import os
import re
import json
import warnings
import threading
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
from flask import Flask, request, jsonify, render_template_string

warnings.filterwarnings('ignore')

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(BASE_DIR, 'dataset.csv')
TITLES_PATH = os.path.join(BASE_DIR, 'movieIdTitles.csv')
METADATA_PATH = os.path.join(BASE_DIR, 'movieMetadata.csv')

# In-memory poster cache
POSTER_CACHE = {}

def parse_title_and_year(raw_title):
    """Parses raw MovieLens titles into clean display title and release year."""
    if not isinstance(raw_title, str):
        return str(raw_title), ""
    raw = raw_title.strip()
    m = re.match(r'^(.*?)(?:\s*\((\d{4})\))?$', raw)
    title = m.group(1).strip() if m else raw
    year = m.group(2) if (m and m.group(2)) else ""
    
    # Fix MovieLens article syntax e.g., "Empire Strikes Back, The" -> "The Empire Strikes Back"
    if ', The' in title:
        title = 'The ' + title.replace(', The', '')
    elif ', A' in title:
        title = 'A ' + title.replace(', A', '')
    elif ', An' in title:
        title = 'An ' + title.replace(', An', '')
    
    return title, year

# Load ratings summary for quality/popularity metrics
print("Loading MovieLens dataset and metadata catalog...")
column_names = ['user_id', 'item_id', 'rating', 'timestamp']
df_data = pd.read_csv(DATASET_PATH, sep='\t', names=column_names)
movie_titles = pd.read_csv(TITLES_PATH)
df_metadata = pd.read_csv(METADATA_PATH)

df_merged = pd.merge(df_data, movie_titles, on='item_id')
ratings_summary = pd.DataFrame(df_merged.groupby('title')['rating'].mean())
ratings_summary['numOfRatings'] = pd.DataFrame(df_merged.groupby('title')['rating'].count())

# Prebuild comprehensive movie catalog (all 1894 movies across 1922-2026)
all_movies = []
meta_by_title = {}
for _, row in df_metadata.iterrows():
    meta_by_title[str(row['title']).strip()] = {
        'genres': str(row.get('genres', 'Drama')),
        'industry': str(row.get('industry', 'International'))
    }

for _, row in movie_titles.iterrows():
    raw = str(row['title']).strip()
    t, y = parse_title_and_year(raw)
    meta = meta_by_title.get(raw, {'genres': 'Drama', 'industry': 'International'})
    
    has_ratings = raw in ratings_summary.index
    avg_r = round(float(ratings_summary.loc[raw, 'rating']), 2) if has_ratings else None
    cnt_r = int(ratings_summary.loc[raw, 'numOfRatings']) if has_ratings else 0
    is_modern = not has_ratings or (y and int(y) >= 2000)

    all_movies.append({
        'item_id': int(row['item_id']),
        'raw': raw,
        'title': t,
        'year': y,
        'genres': meta['genres'],
        'industry': meta['industry'],
        'avg_rating': avg_r,
        'rating_count': cnt_r,
        'is_modern': is_modern
    })

print(f"Ready with {len(all_movies)} movies spanning 1922 to 2026!")

def fetch_wikipedia_poster(title, year=''):
    """Fetches high-quality theatrical movie poster from Wikipedia API."""
    cache_key = f"{title}_{year}"
    if cache_key in POSTER_CACHE:
        return POSTER_CACHE[cache_key]

    queries = []
    if year:
        queries.append(f"{title} ({year} film)")
        queries.append(f"{title} ({year})")
    queries.append(f"{title} (film)")
    queries.append(title)

    headers = {'User-Agent': 'MovieLensRecommender/2.0 (student@edu.org)'}
    poster_url = None

    for q in queries:
        try:
            slug = urllib.parse.quote(q.replace(' ', '_'))
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=1.8) as resp:
                data = json.loads(resp.read().decode())
                thumb = data.get('thumbnail', {}).get('source')
                if thumb:
                    poster_url = thumb
                    break
        except Exception:
            continue

    POSTER_CACHE[cache_key] = poster_url
    return poster_url

def warmup_posters():
    """Background thread to pre-warm popular posters so starter movies appear instantly."""
    starter_movies = [
        ('Star Wars', '1977'),
        ('Toy Story', '1995'),
        ('Oppenheimer', '2023'),
        ('RRR', '2022'),
        ('Dune: Part Two', '2024'),
        ('Inception', '2010'),
        ('The Dark Knight', '2008'),
        ('Fargo', '1996'),
        ('The Godfather', '1972'),
        ('Parasite', '2019')
    ]
    with ThreadPoolExecutor(max_workers=5) as executor:
        for t, y in starter_movies:
            executor.submit(fetch_wikipedia_poster, t, y)

threading.Thread(target=warmup_posters, daemon=True).start()

def compute_genre_recommendations(movie_raw, offset=0, limit=4):
    """Computes pure Content-Based recommendations using multi-genre similarity."""
    target = next((m for m in all_movies if m['raw'] == movie_raw), None)
    if not target:
        return [], 0

    target_genres = set(target['genres'].split('|'))
    target_ind = target['industry']

    candidates = []
    for m in all_movies:
        if m['raw'] == movie_raw:
            continue
        c_genres = set(m['genres'].split('|'))
        intersection = target_genres.intersection(c_genres)
        if not intersection:
            continue
        
        # Dice similarity coefficient on genres
        dice = 2.0 * len(intersection) / (len(target_genres) + len(c_genres))
        match_pct = int(round(dice * 100))
        
        # Tie-breaker score: Dice similarity + subtle quality/industry weighting
        score = dice
        if m['industry'] == target_ind:
            score += 0.05
        if m['avg_rating']:
            score += (m['avg_rating'] / 5.0) * 0.03
            
        candidates.append({
            'movie': m,
            'score': score,
            'match_pct': match_pct,
            'matched_genres': list(intersection)
        })

    # Sort primarily by genre similarity score
    candidates.sort(key=lambda x: x['score'], reverse=True)
    total = len(candidates)
    if total == 0:
        return [], 0

    start = (offset * limit) % total
    picked = candidates[start:start + limit]
    if len(picked) < limit and total > len(picked):
        picked += candidates[:limit - len(picked)]
        
    return picked, total


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Movie Recommendation System (Genre-Based)</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-body: #080c16;
            --bg-card: #0f172a;
            --bg-card-hover: #141f38;
            --bg-input: #10182b;
            --border-color: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(99, 102, 241, 0.45);
            --accent-cyan: #38bdf8;
            --accent-purple: #818cf8;
            --accent-indigo: #6366f1;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --text-dim: #64748b;
            --shadow-subtle: 0 4px 20px -2px rgba(0, 0, 0, 0.45);
            --shadow-hover: 0 10px 28px -4px rgba(0, 0, 0, 0.6), 0 0 16px rgba(99, 102, 241, 0.18);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-body);
            background-image: 
                radial-gradient(ellipse 80% 50% at 50% -20%, rgba(99, 102, 241, 0.15), transparent 70%),
                radial-gradient(circle at 100% 100%, rgba(56, 189, 248, 0.05), transparent 50%);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 44px 20px 80px;
            -webkit-font-smoothing: antialiased;
        }

        .container {
            width: 100%;
            max-width: 680px;
        }

        /* Header */
        header {
            text-align: center;
            margin-bottom: 32px;
        }

        header h1 {
            font-size: 2.15rem;
            font-weight: 700;
            letter-spacing: -0.025em;
            background: linear-gradient(135deg, #ffffff 40%, #c7d2fe 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }

        header p {
            color: var(--text-muted);
            font-size: 0.95rem;
            line-height: 1.5;
            font-weight: 400;
            margin-bottom: 14px;
        }

        .stats-trigger-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.25);
            color: var(--accent-purple);
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .stats-trigger-btn:hover {
            background: rgba(99, 102, 241, 0.2);
            color: #ffffff;
            transform: translateY(-1px);
        }

        /* Search Section */
        .search-wrapper {
            position: relative;
            margin-bottom: 28px;
        }

        .search-box {
            position: relative;
            display: flex;
            align-items: center;
            background: var(--bg-input);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            box-shadow: var(--shadow-subtle);
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .search-box:focus-within {
            border-color: var(--accent-indigo);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.22), var(--shadow-subtle);
        }

        .search-icon {
            position: absolute;
            left: 18px;
            width: 19px;
            height: 19px;
            color: var(--text-dim);
            pointer-events: none;
            transition: color 0.2s ease;
        }

        .search-box:focus-within .search-icon {
            color: var(--accent-cyan);
        }

        .search-input {
            width: 100%;
            padding: 16px 48px 16px 50px;
            font-size: 1.02rem;
            font-family: inherit;
            background: transparent;
            border: none;
            color: #ffffff;
            outline: none;
        }

        .search-input::placeholder {
            color: var(--text-dim);
        }

        .clear-btn {
            position: absolute;
            right: 14px;
            background: rgba(255, 255, 255, 0.08);
            border: none;
            border-radius: 50%;
            width: 26px;
            height: 26px;
            display: none;
            align-items: center;
            justify-content: center;
            color: var(--text-muted);
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .clear-btn:hover {
            background: rgba(255, 255, 255, 0.16);
            color: #ffffff;
        }

        /* Autocomplete Dropdown */
        .suggestions-dropdown {
            position: absolute;
            top: calc(100% + 8px);
            left: 0;
            right: 0;
            background: #0f172a;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            max-height: 320px;
            overflow-y: auto;
            z-index: 100;
            display: none;
            box-shadow: 0 16px 36px rgba(0, 0, 0, 0.65);
            backdrop-filter: blur(12px);
        }

        .suggestion-item {
            padding: 8px 14px;
            display: flex;
            align-items: center;
            gap: 12px;
            cursor: pointer;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            transition: background 0.12s ease;
        }

        .suggestion-item:last-child { border-bottom: none; }
        .suggestion-item:hover, .suggestion-item.active { background: #1e293b; }

        .suggestion-poster-wrap {
            width: 32px;
            height: 46px;
            background: #141d33;
            border-radius: 5px;
            overflow: hidden;
            flex-shrink: 0;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1px solid rgba(255, 255, 255, 0.06);
        }

        .suggestion-poster-wrap img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: 4px;
            opacity: 0;
            transition: opacity 0.25s ease;
        }

        .suggestion-poster-wrap img.loaded { opacity: 1; }

        .suggestion-info { flex-grow: 1; min-width: 0; }

        .suggestion-title {
            font-size: 0.94rem;
            color: var(--text-main);
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .suggestion-item:hover .suggestion-title,
        .suggestion-item.active .suggestion-title {
            color: var(--accent-cyan);
        }

        .suggestion-sub {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 2px;
            font-size: 0.78rem;
            color: var(--text-dim);
        }

        .suggestion-year {
            background: rgba(255, 255, 255, 0.06);
            padding: 1px 6px;
            border-radius: 4px;
            color: var(--text-muted);
            font-weight: 500;
        }

        .genre-pill {
            background: rgba(99, 102, 241, 0.12);
            color: var(--accent-purple);
            padding: 1px 6px;
            border-radius: 4px;
            font-size: 0.74rem;
            font-weight: 500;
        }

        /* Selected Movie Hero Card */
        .selected-movie-card {
            background: linear-gradient(135deg, #111a2f 0%, #16203c 100%);
            border: 1px solid rgba(99, 102, 241, 0.28);
            border-radius: 14px;
            padding: 16px;
            display: flex;
            gap: 18px;
            align-items: center;
            margin-bottom: 24px;
            box-shadow: 0 8px 24px -4px rgba(0, 0, 0, 0.4);
        }

        .selected-poster-wrap {
            width: 74px;
            height: 108px;
            background: #141d33;
            border-radius: 10px;
            overflow: hidden;
            flex-shrink: 0;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.5);
        }

        .selected-poster-img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: 9px;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .selected-poster-img.loaded { opacity: 1; }

        .selected-details { flex-grow: 1; min-width: 0; }

        .selected-tag {
            display: inline-block;
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--accent-cyan);
            background: rgba(56, 189, 248, 0.12);
            padding: 2px 8px;
            border-radius: 4px;
            margin-bottom: 6px;
        }

        .selected-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 6px;
            line-height: 1.3;
        }

        .selected-meta {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 10px;
            font-size: 0.84rem;
            color: var(--text-muted);
        }

        .genre-badge-list {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-top: 6px;
        }

        .genre-badge {
            background: rgba(99, 102, 241, 0.18);
            border: 1px solid rgba(99, 102, 241, 0.3);
            color: #c7d2fe;
            padding: 2px 8px;
            border-radius: 5px;
            font-size: 0.76rem;
            font-weight: 600;
        }

        /* Recommendations Section Header */
        .recommendations-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
            padding: 0 4px;
        }

        .rec-info-title {
            font-size: 0.96rem;
            color: var(--text-muted);
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .rec-info-title span.accent-label {
            color: var(--accent-purple);
        }

        .refresh-btn {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            padding: 7px 14px;
            font-size: 0.84rem;
            font-weight: 500;
            font-family: inherit;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .refresh-btn:hover {
            background: rgba(99, 102, 241, 0.12);
            border-color: var(--accent-indigo);
            color: #ffffff;
            transform: translateY(-1px);
        }

        .refresh-btn svg { width: 14px; height: 14px; transition: transform 0.4s ease; }
        .refresh-btn.spinning svg { transform: rotate(360deg); }

        /* Cards List */
        .cards-list { display: flex; flex-direction: column; gap: 12px; }

        .rec-card {
            display: flex;
            align-items: center;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 12px 16px;
            gap: 16px;
            cursor: pointer;
            text-decoration: none;
            transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1), 
                        border-color 0.2s ease, 
                        box-shadow 0.2s ease, 
                        background 0.2s ease;
            position: relative;
        }

        .rec-card:hover {
            transform: translateY(-2px);
            border-color: var(--border-hover);
            background: var(--bg-card-hover);
            box-shadow: var(--shadow-hover);
        }

        .card-rank {
            font-size: 0.8rem;
            font-weight: 700;
            color: var(--accent-purple);
            background: rgba(99, 102, 241, 0.12);
            width: 24px;
            height: 24px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        .poster-container {
            width: 54px;
            height: 78px;
            background: #141d33;
            border-radius: 8px;
            overflow: hidden;
            flex-shrink: 0;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1px solid rgba(255, 255, 255, 0.05);
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.35);
        }

        .poster-img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: 7px;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .poster-img.loaded { opacity: 1; }

        .card-content { flex-grow: 1; min-width: 0; }

        .card-title {
            font-size: 1.05rem;
            font-weight: 600;
            color: var(--text-main);
            margin-bottom: 5px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            transition: color 0.15s ease;
        }

        .rec-card:hover .card-title { color: var(--accent-cyan); }

        .card-meta {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.82rem;
            color: var(--text-muted);
            margin-bottom: 4px;
        }

        .year-pill {
            background: rgba(255, 255, 255, 0.06);
            padding: 2px 7px;
            border-radius: 5px;
            font-weight: 500;
            font-size: 0.78rem;
        }

        .match-badge {
            color: #38bdf8;
            background: rgba(56, 189, 248, 0.1);
            border: 1px solid rgba(56, 189, 248, 0.25);
            padding: 2px 7px;
            border-radius: 5px;
            font-weight: 700;
            font-size: 0.76rem;
        }

        .card-genres {
            font-size: 0.78rem;
            color: var(--text-dim);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .card-action-cue {
            font-size: 0.78rem;
            color: var(--text-dim);
            opacity: 0;
            transform: translateX(-4px);
            transition: all 0.2s ease;
            margin-left: auto;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .rec-card:hover .card-action-cue {
            opacity: 1;
            transform: translateX(0);
            color: var(--accent-purple);
        }

        /* Empty & Error States */
        .empty-state, .error-state {
            background: var(--bg-card);
            border: 1px dashed var(--border-color);
            border-radius: 14px;
            padding: 40px 24px;
            text-align: center;
        }

        .state-icon {
            width: 44px;
            height: 44px;
            margin: 0 auto 16px;
            color: var(--text-dim);
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 50%;
        }

        .empty-state h3, .error-state h3 {
            font-size: 1.05rem;
            font-weight: 600;
            margin-bottom: 8px;
            color: #e2e8f0;
        }

        .empty-state p, .error-state p {
            font-size: 0.88rem;
            color: var(--text-muted);
            max-width: 460px;
            margin: 0 auto 24px;
            line-height: 1.5;
        }

        /* Starter Grid */
        .starter-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            text-align: left;
        }

        .starter-card {
            background: #111a2e;
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 10px 12px;
            display: flex;
            align-items: center;
            gap: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        .starter-card:hover {
            background: #16223e;
            border-color: var(--accent-indigo);
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
        }

        .starter-poster {
            width: 38px;
            height: 56px;
            background: #1b2640;
            border-radius: 6px;
            overflow: hidden;
            flex-shrink: 0;
            position: relative;
        }

        .starter-poster img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .starter-poster img.loaded { opacity: 1; }

        .starter-info { flex-grow: 1; min-width: 0; }

        .starter-title {
            font-size: 0.88rem;
            font-weight: 600;
            color: var(--text-main);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .starter-meta { font-size: 0.74rem; color: var(--text-dim); margin-top: 2px; }

        /* Modal for Decade Distribution */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(8, 12, 22, 0.85);
            backdrop-filter: blur(8px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            padding: 20px;
        }

        .modal-content {
            background: #0f172a;
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 16px;
            max-width: 540px;
            width: 100%;
            padding: 24px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.7);
        }

        .modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 18px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 12px;
        }

        .modal-header h2 {
            font-size: 1.18rem;
            font-weight: 700;
            color: #ffffff;
        }

        .close-modal-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            padding: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .close-modal-btn:hover { color: #ffffff; }

        .stats-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.88rem;
        }

        .stats-table th, .stats-table td {
            padding: 9px 12px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }

        .stats-table th {
            color: var(--text-dim);
            font-weight: 600;
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .stats-table td.count { text-align: right; font-weight: 600; color: #ffffff; }
        .stats-table td.pct { text-align: right; color: var(--accent-cyan); font-weight: 600; }
        .stats-table tr:hover { background: rgba(255, 255, 255, 0.02); }

        /* Loading Skeleton */
        .skeleton-card {
            display: flex;
            align-items: center;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 12px 16px;
            gap: 16px;
        }

        .skeleton-pulse {
            background: linear-gradient(90deg, #131c31 0%, #1f2a47 50%, #131c31 100%);
            background-size: 200% 100%;
            animation: pulseShimmer 1.5s infinite;
            border-radius: 6px;
        }

        @keyframes pulseShimmer {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }

        .skeleton-rank { width: 24px; height: 24px; border-radius: 6px; flex-shrink: 0; }
        .skeleton-poster { width: 54px; height: 78px; border-radius: 8px; flex-shrink: 0; }
        .skeleton-lines { flex-grow: 1; display: flex; flex-direction: column; gap: 8px; }
        .skeleton-title { width: 65%; height: 18px; }
        .skeleton-subtitle { width: 30%; height: 13px; }

        @media (max-width: 640px) {
            body { padding: 32px 16px 60px; }
            header h1 { font-size: 1.7rem; }
            .starter-grid { grid-template-columns: 1fr; }
            .selected-movie-card { padding: 12px; gap: 14px; }
            .selected-poster-wrap { width: 62px; height: 90px; }
            .selected-title { font-size: 1.1rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Movie Recommendation System</h1>
            <p>Content-Based Genre Recommender built with Python, Pandas & MovieLens (1922–2026)</p>
            <button type="button" class="stats-trigger-btn" onclick="openStatsModal()">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="20" x2="18" y2="10"></line>
                    <line x1="12" y1="20" x2="12" y2="4"></line>
                    <line x1="6" y1="20" x2="6" y2="14"></line>
                </svg>
                1,894 Movies (1922–2026) · View Decades
            </button>
        </header>

        <!-- Search Selection Input -->
        <div class="search-wrapper">
            <div class="search-box">
                <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
                <input 
                    type="text" 
                    id="movieInput" 
                    class="search-input" 
                    placeholder="Search movie title or release year (e.g. Star Wars, Toy Story, Oppenheimer)..." 
                    autocomplete="off"
                    spellcheck="false"
                >
                <button type="button" id="clearBtn" class="clear-btn" aria-label="Clear input">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
            <div id="suggestionsDropdown" class="suggestions-dropdown"></div>
        </div>

        <!-- Main Content -->
        <div id="mainContent">
            <!-- Empty State with Featured Poster Cards -->
            <div id="emptyState" class="empty-state">
                <div class="state-icon">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                        <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect>
                        <line x1="7" y1="2" x2="7" y2="22"></line>
                        <line x1="17" y1="2" x2="17" y2="22"></line>
                        <line x1="2" y1="12" x2="22" y2="12"></line>
                        <line x1="2" y1="7" x2="7" y2="7"></line>
                        <line x1="2" y1="17" x2="7" y2="17"></line>
                        <line x1="17" y1="17" x2="22" y2="17"></line>
                        <line x1="17" y1="7" x2="22" y2="7"></line>
                    </svg>
                </div>
                <h3>Explore 1,894 Movies by Genre</h3>
                <p>Select any title from Hollywood, Bollywood, or International cinema to discover recommendations sharing its core genres.</p>
                
                <div class="starter-grid">
                    <div class="starter-card" onclick="selectMovie('Star Wars (1977)')">
                        <div class="starter-poster">
                            <img id="starter-img-0" alt="Star Wars">
                        </div>
                        <div class="starter-info">
                            <div class="starter-title">Star Wars</div>
                            <div class="starter-meta">1977 · Sci-Fi · Action · Adventure</div>
                        </div>
                    </div>
                    <div class="starter-card" onclick="selectMovie('Toy Story (1995)')">
                        <div class="starter-poster">
                            <img id="starter-img-1" alt="Toy Story">
                        </div>
                        <div class="starter-info">
                            <div class="starter-title">Toy Story</div>
                            <div class="starter-meta">1995 · Animation · Comedy · Family</div>
                        </div>
                    </div>
                    <div class="starter-card" onclick="selectMovie('Oppenheimer (2023)')">
                        <div class="starter-poster">
                            <img id="starter-img-2" alt="Oppenheimer">
                        </div>
                        <div class="starter-info">
                            <div class="starter-title">Oppenheimer</div>
                            <div class="starter-meta">2023 · Biography · Drama · History</div>
                        </div>
                    </div>
                    <div class="starter-card" onclick="selectMovie('Dark Knight, The (2008)')">
                        <div class="starter-poster">
                            <img id="starter-img-3" alt="The Dark Knight">
                        </div>
                        <div class="starter-info">
                            <div class="starter-title">The Dark Knight</div>
                            <div class="starter-meta">2008 · Action · Crime · Drama</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Loading State -->
            <div id="loadingState" style="display: none;">
                <div class="recommendations-header">
                    <div class="rec-info-title">Matching genre fingerprints...</div>
                </div>
                <div class="cards-list">
                    <div class="skeleton-card">
                        <div class="skeleton-pulse skeleton-rank"></div>
                        <div class="skeleton-pulse skeleton-poster"></div>
                        <div class="skeleton-lines">
                            <div class="skeleton-pulse skeleton-title"></div>
                            <div class="skeleton-pulse skeleton-subtitle"></div>
                        </div>
                    </div>
                    <div class="skeleton-card">
                        <div class="skeleton-pulse skeleton-rank"></div>
                        <div class="skeleton-pulse skeleton-poster"></div>
                        <div class="skeleton-lines">
                            <div class="skeleton-pulse skeleton-title"></div>
                            <div class="skeleton-pulse skeleton-subtitle"></div>
                        </div>
                    </div>
                    <div class="skeleton-card">
                        <div class="skeleton-pulse skeleton-rank"></div>
                        <div class="skeleton-pulse skeleton-poster"></div>
                        <div class="skeleton-lines">
                            <div class="skeleton-pulse skeleton-title"></div>
                            <div class="skeleton-pulse skeleton-subtitle"></div>
                        </div>
                    </div>
                    <div class="skeleton-card">
                        <div class="skeleton-pulse skeleton-rank"></div>
                        <div class="skeleton-pulse skeleton-poster"></div>
                        <div class="skeleton-lines">
                            <div class="skeleton-pulse skeleton-title"></div>
                            <div class="skeleton-pulse skeleton-subtitle"></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Error State -->
            <div id="errorState" class="error-state" style="display: none;">
                <div class="state-icon" style="color: #f87171;">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="12"></line>
                        <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                </div>
                <h3 id="errorHeading">Unable to Load Recommendations</h3>
                <p id="errorMessage">Please choose another movie or try again.</p>
                <div style="margin-top: 18px;">
                    <button class="refresh-btn" onclick="selectMovie('Star Wars (1977)')">Try Star Wars</button>
                    <button class="refresh-btn" onclick="selectMovie('Toy Story (1995)')">Try Toy Story</button>
                </div>
            </div>

            <!-- Recommendations View -->
            <div id="recommendationsView" style="display: none;">
                <!-- Hero Selected Movie Card -->
                <div id="selectedMovieCard" class="selected-movie-card">
                    <div class="selected-poster-wrap">
                        <img id="selectedMoviePoster" class="selected-poster-img" alt="Selected movie poster">
                    </div>
                    <div class="selected-details">
                        <span id="selectedTag" class="selected-tag">Selected Movie</span>
                        <div id="selectedMovieTitleText" class="selected-title"></div>
                        <div class="selected-meta">
                            <span id="selectedMovieYear" class="year-pill"></span>
                            <span id="selectedMovieMeta"></span>
                        </div>
                        <div id="selectedMovieGenres" class="genre-badge-list"></div>
                    </div>
                </div>

                <!-- Recommendations Section Header -->
                <div class="recommendations-header">
                    <div class="rec-info-title">
                        Recommended For You <span id="recEngineLabel" class="accent-label">Top Genre Matches</span>
                    </div>
                    <button type="button" id="refreshBtn" class="refresh-btn" title="Get next set of recommendations">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path>
                        </svg>
                        Refresh
                    </button>
                </div>

                <!-- Recommendation Cards List -->
                <div id="cardsList" class="cards-list"></div>
            </div>
        </div>
    </div>

    <!-- Modal for Decade Distribution -->
    <div id="statsModal" class="modal-overlay" onclick="closeStatsModalOnBg(event)">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Decade-Wise Distribution (1922–2026)</h2>
                <button type="button" class="close-modal-btn" onclick="closeStatsModal()" aria-label="Close">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>
            <table class="stats-table">
                <thead>
                    <tr>
                        <th>Decade</th>
                        <th style="text-align: right;">Movie Count</th>
                        <th style="text-align: right;">Share</th>
                    </tr>
                </thead>
                <tbody id="statsTableBody">
                    <tr><td colspan="3" style="text-align: center; color: var(--text-dim);">Loading distribution...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        const movieInput = document.getElementById('movieInput');
        const clearBtn = document.getElementById('clearBtn');
        const dropdown = document.getElementById('suggestionsDropdown');
        const emptyState = document.getElementById('emptyState');
        const loadingState = document.getElementById('loadingState');
        const errorState = document.getElementById('errorState');
        const recommendationsView = document.getElementById('recommendationsView');
        const cardsList = document.getElementById('cardsList');
        const refreshBtn = document.getElementById('refreshBtn');

        const selectedTag = document.getElementById('selectedTag');
        const selectedMovieTitleText = document.getElementById('selectedMovieTitleText');
        const selectedMovieYear = document.getElementById('selectedMovieYear');
        const selectedMovieMeta = document.getElementById('selectedMovieMeta');
        const selectedMovieGenres = document.getElementById('selectedMovieGenres');
        const selectedMoviePoster = document.getElementById('selectedMoviePoster');
        const recEngineLabel = document.getElementById('recEngineLabel');

        let currentSelectedMovie = null;
        let currentOffset = 0;
        let searchDebounceTimer = null;
        let activeSuggestionIndex = -1;
        let suggestionsData = [];

        // Load starter posters
        loadPosterAsync('Star Wars', '1977', 'starter-img-0');
        loadPosterAsync('Toy Story', '1995', 'starter-img-1');
        loadPosterAsync('Oppenheimer', '2023', 'starter-img-2');
        loadPosterAsync('The Dark Knight', '2008', 'starter-img-3');

        // Input listener with debounce
        movieInput.addEventListener('input', () => {
            const query = movieInput.value.trim();
            clearBtn.style.display = query.length > 0 ? 'flex' : 'none';

            clearTimeout(searchDebounceTimer);
            if (query.length < 2) {
                hideDropdown();
                return;
            }

            searchDebounceTimer = setTimeout(() => {
                fetchSuggestions(query);
            }, 160);
        });

        clearBtn.addEventListener('click', () => {
            movieInput.value = '';
            clearBtn.style.display = 'none';
            hideDropdown();
            movieInput.focus();
        });

        // Keyboard navigation
        movieInput.addEventListener('keydown', (e) => {
            const items = dropdown.querySelectorAll('.suggestion-item');
            if (!items.length) return;

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                activeSuggestionIndex = (activeSuggestionIndex + 1) % items.length;
                updateActiveSuggestion(items);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                activeSuggestionIndex = (activeSuggestionIndex - 1 + items.length) % items.length;
                updateActiveSuggestion(items);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                if (activeSuggestionIndex >= 0 && activeSuggestionIndex < suggestionsData.length) {
                    selectMovie(suggestionsData[activeSuggestionIndex].raw);
                } else if (suggestionsData.length > 0) {
                    selectMovie(suggestionsData[0].raw);
                }
            } else if (e.key === 'Escape') {
                hideDropdown();
            }
        });

        function updateActiveSuggestion(items) {
            items.forEach((item, index) => {
                item.classList.toggle('active', index === activeSuggestionIndex);
                if (index === activeSuggestionIndex) {
                    item.scrollIntoView({ block: 'nearest' });
                }
            });
        }

        document.addEventListener('click', (e) => {
            if (!movieInput.contains(e.target) && !dropdown.contains(e.target)) {
                hideDropdown();
            }
        });

        function hideDropdown() {
            dropdown.style.display = 'none';
            dropdown.innerHTML = '';
            activeSuggestionIndex = -1;
            suggestionsData = [];
        }

        function fetchSuggestions(query) {
            fetch(`/search?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(results => {
                    suggestionsData = results;
                    activeSuggestionIndex = -1;
                    dropdown.innerHTML = '';

                    if (!results || results.length === 0) {
                        hideDropdown();
                        return;
                    }

                    results.forEach((item, index) => {
                        const div = document.createElement('div');
                        div.className = 'suggestion-item';
                        const posterId = `sug-poster-${index}`;
                        
                        let displayGenres = item.genres.split('|').slice(0, 2).join(' · ');

                        div.innerHTML = `
                            <div class="suggestion-poster-wrap">
                                <img id="${posterId}" alt="${item.title}">
                            </div>
                            <div class="suggestion-info">
                                <div class="suggestion-title">${item.title}</div>
                                <div class="suggestion-sub">
                                    ${item.year ? `<span class="suggestion-year">${item.year}</span>` : ''}
                                    <span class="genre-pill">${displayGenres}</span>
                                    <span>${item.industry}</span>
                                </div>
                            </div>
                        `;
                        div.addEventListener('click', () => {
                            selectMovie(item.raw);
                        });
                        dropdown.appendChild(div);

                        loadPosterAsync(item.title, item.year, posterId);
                    });

                    dropdown.style.display = 'block';
                })
                .catch(() => hideDropdown());
        }

        function selectMovie(rawMovieName) {
            currentSelectedMovie = rawMovieName;
            currentOffset = 0;
            movieInput.value = rawMovieName;
            clearBtn.style.display = 'flex';
            hideDropdown();
            fetchRecommendations(rawMovieName, currentOffset);
        }

        refreshBtn.addEventListener('click', () => {
            if (!currentSelectedMovie) return;
            currentOffset += 1;
            refreshBtn.classList.add('spinning');
            fetchRecommendations(currentSelectedMovie, currentOffset);
            setTimeout(() => refreshBtn.classList.remove('spinning'), 500);
        });

        function fetchRecommendations(movieRaw, offset) {
            showLoading();

            fetch(`/recommend?movie=${encodeURIComponent(movieRaw)}&offset=${offset}`)
                .then(res => {
                    if (!res.ok) throw new Error('Network response error');
                    return res.json();
                })
                .then(data => {
                    if (!data.recommendations || data.recommendations.length === 0) {
                        showError("No Matching Genre Titles", `No movies sharing genres could be found for "${data.movie.title}". Try selecting another title.`);
                        return;
                    }
                    renderRecommendations(data);
                })
                .catch(err => {
                    showError("Error Loading Recommendations", "Could not connect to the recommendation engine. Please check your connection and try again.");
                });
        }

        function renderRecommendations(data) {
            emptyState.style.display = 'none';
            loadingState.style.display = 'none';
            errorState.style.display = 'none';
            recommendationsView.style.display = 'block';

            // Selected Movie Card details
            selectedMovieTitleText.textContent = data.movie.title;
            selectedMovieYear.textContent = data.movie.year || 'Catalog';
            selectedTag.textContent = data.movie.year >= 2025 ? 'Upcoming Release' : 'Selected Movie';
            selectedMovieMeta.textContent = `${data.movie.industry} cinema`;
            recEngineLabel.textContent = 'Genre Similarity Matches';

            // Render selected movie genre badges
            selectedMovieGenres.innerHTML = '';
            data.movie.genres.split('|').forEach(g => {
                const badge = document.createElement('span');
                badge.className = 'genre-badge';
                badge.textContent = g;
                selectedMovieGenres.appendChild(badge);
            });

            selectedMoviePoster.classList.remove('loaded');
            loadPosterAsync(data.movie.title, data.movie.year, 'selectedMoviePoster');

            // Render Recommendation Cards
            cardsList.innerHTML = '';

            data.recommendations.forEach((rec, idx) => {
                const card = document.createElement('div');
                card.className = 'rec-card';
                card.setAttribute('role', 'button');
                card.setAttribute('tabindex', '0');
                card.title = `Click to get recommendations for ${rec.title}`;

                const cardId = `poster-${idx}`;
                const genresFormatted = rec.genres ? rec.genres.replace(/\\|/g, ' · ') : 'General';

                card.innerHTML = `
                    <div class="card-rank">#${idx + 1}</div>
                    <div class="poster-container">
                        <img id="${cardId}" class="poster-img" alt="${rec.title}">
                    </div>
                    <div class="card-content">
                        <div class="card-title">${rec.title}</div>
                        <div class="card-meta">
                            ${rec.year ? `<span class="year-pill">${rec.year}</span>` : ''}
                            <span class="match-badge">${rec.match_pct}% Match</span>
                            <span>${rec.industry || 'Cinema'}</span>
                        </div>
                        <div class="card-genres">${genresFormatted}</div>
                    </div>
                    <div class="card-action-cue">
                        <span>Explore</span>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                            <polyline points="9 18 15 12 9 6"></polyline>
                        </svg>
                    </div>
                `;

                card.addEventListener('click', () => { selectMovie(rec.raw); });
                card.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        selectMovie(rec.raw);
                    }
                });

                cardsList.appendChild(card);
                loadPosterAsync(rec.title, rec.year, cardId);
            });
        }

        function loadPosterAsync(title, year, elementId) {
            fetch(`/poster?title=${encodeURIComponent(title)}&year=${encodeURIComponent(year || '')}`)
                .then(res => res.json())
                .then(data => {
                    if (data.poster) {
                        const img = document.getElementById(elementId);
                        if (img) {
                            img.src = data.poster;
                            img.onload = () => img.classList.add('loaded');
                        }
                    }
                })
                .catch(() => {});
        }

        function showLoading() {
            emptyState.style.display = 'none';
            errorState.style.display = 'none';
            recommendationsView.style.display = 'none';
            loadingState.style.display = 'block';
        }

        function showError(heading, message) {
            emptyState.style.display = 'none';
            loadingState.style.display = 'none';
            recommendationsView.style.display = 'none';
            errorState.style.display = 'block';

            document.getElementById('errorHeading').textContent = heading;
            document.getElementById('errorMessage').textContent = message;
        }

        // Stats Modal
        function openStatsModal() {
            const modal = document.getElementById('statsModal');
            modal.style.display = 'flex';
            fetch('/dataset-stats')
                .then(res => res.json())
                .then(data => {
                    const tbody = document.getElementById('statsTableBody');
                    tbody.innerHTML = '';
                    data.decades.forEach(row => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td>${row.decade}</td>
                            <td class="count">${row.count.toLocaleString()}</td>
                            <td class="pct">${row.percentage.toFixed(2)}%</td>
                        `;
                        tbody.appendChild(tr);
                    });
                    const totalTr = document.createElement('tr');
                    totalTr.style.borderTop = '2px solid rgba(255,255,255,0.15)';
                    totalTr.style.fontWeight = '700';
                    totalTr.innerHTML = `
                        <td><strong>Total Catalog</strong></td>
                        <td class="count"><strong>${data.total_movies.toLocaleString()}</strong></td>
                        <td class="pct"><strong>100.0%</strong></td>
                    `;
                    tbody.appendChild(totalTr);
                });
        }

        function closeStatsModal() {
            document.getElementById('statsModal').style.display = 'none';
        }

        function closeStatsModalOnBg(e) {
            if (e.target.id === 'statsModal') {
                closeStatsModal();
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/search')
def search():
    query = request.args.get('q', '').strip().lower()
    if not query:
        return jsonify([])
    
    matches = []
    for item in all_movies:
        raw_l = item['raw'].lower()
        title_l = item['title'].lower()
        if query in raw_l or query in title_l:
            matches.append(item)

    # Sort by relevance: title start > word start > substring
    def relevance_key(item):
        t = item['title'].lower()
        if t.startswith(query):
            return (0, len(t))
        words = t.split()
        if any(w.startswith(query) for w in words):
            return (1, len(t))
        return (2, len(t))

    matches.sort(key=relevance_key)
    return jsonify(matches[:10])

@app.route('/recommend')
def recommend():
    movie_query = request.args.get('movie', '').strip()
    offset = int(request.args.get('offset', 0))
    limit = 4

    if not movie_query:
        return jsonify({'error': 'No movie specified'}), 400

    target = None
    for item in all_movies:
        if item['raw'].lower() == movie_query.lower() or item['title'].lower() == movie_query.lower():
            target = item
            break
    if not target:
        for item in all_movies:
            if movie_query.lower() in item['raw'].lower():
                target = item
                break

    if not target:
        return jsonify({'error': 'Movie not found in dataset', 'recommendations': []}), 404

    # Pure Content-Based Genre Recommendations
    rec_results, total_count = compute_genre_recommendations(target['raw'], offset=offset, limit=limit)
    
    formatted_recs = []
    for r in rec_results:
        m = r['movie'].copy()
        m['match_pct'] = r['match_pct']
        m['matched_genres'] = r['matched_genres']
        formatted_recs.append(m)

    return jsonify({
        'movie': target,
        'recommendations': formatted_recs,
        'offset': offset,
        'total_available': total_count
    })

@app.route('/poster')
def poster():
    title = request.args.get('title', '').strip()
    year = request.args.get('year', '').strip()
    poster_url = fetch_wikipedia_poster(title, year)
    return jsonify({'poster': poster_url})

@app.route('/dataset-stats')
def dataset_stats():
    years = [int(m['year']) for m in all_movies if m['year'] and str(m['year']).isdigit()]
    years.sort()
    s_years = pd.Series(years)
    decades = (s_years // 10 * 10).value_counts().sort_index()

    decade_list = []
    total_with_years = len(years)
    for dec, count in decades.items():
        decade_list.append({
            'decade': f"{int(dec)}s",
            'count': int(count),
            'percentage': round((count / total_with_years) * 100, 2)
        })

    return jsonify({
        'total_movies': len(all_movies),
        'movies_with_years': total_with_years,
        'decades': decade_list
    })

if __name__ == '__main__':
    port = 5000
    print("=" * 65)
    print(" Movie Recommendation System (Genre-Based)")
    print(f" Web app running at: http://127.0.0.1:{port}")
    print("=" * 65)
    app.run(host='127.0.0.1', port=port, debug=False)
