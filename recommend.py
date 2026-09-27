import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
METADATA_PATH = os.path.join(BASE_DIR, 'movieMetadata.csv')

def load_data():
    if not os.path.exists(METADATA_PATH):
        raise FileNotFoundError(f"Could not find {METADATA_PATH}")
    return pd.read_csv(METADATA_PATH)

def get_genre_recommendations(query, df, limit=5):
    # Try exact match first
    match = df[df['title'].str.strip().str.lower() == query.strip().lower()]
    
    # If no exact match, search partial matches
    if match.empty:
        matches = df[df['title'].str.contains(query.strip(), case=False, na=False)]
        if matches.empty:
            return None, []
        if len(matches) > 1:
            return None, matches['title'].tolist()
        match = matches

    target = match.iloc[0]
    target_title = target['title']
    target_genres = set(str(target['genres']).split('|'))
    target_ind = target['industry']

    candidates = []
    for idx, row in df.iterrows():
        title = row['title']
        if title == target_title:
            continue
        c_genres = set(str(row['genres']).split('|'))
        intersection = target_genres.intersection(c_genres)
        if not intersection:
            continue
        
        dice = 2.0 * len(intersection) / (len(target_genres) + len(c_genres))
        match_pct = int(round(dice * 100))
        
        score = dice
        if row['industry'] == target_ind:
            score += 0.05
            
        candidates.append({
            'title': title,
            'year': row['year'],
            'genres': row['genres'],
            'industry': row['industry'],
            'match_pct': match_pct,
            'matched_genres': list(intersection),
            'score': score
        })

    candidates.sort(key=lambda x: x['score'], reverse=True)
    return target, candidates[:limit]

def main():
    print("=" * 65)
    print("   Movie Recommendation System - Content-Based Genre Engine")
    print("=" * 65)
    
    df = load_data()
    print(f"Loaded {len(df)} movies (1922–2026) with full genre fingerprints.\n")
    print("Tip: Type any movie (e.g., 'Star Wars', 'Toy Story', 'Oppenheimer')")
    print("Type 'exit' or 'quit' to close.\n")

    while True:
        try:
            query = input("Enter movie name: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting. Goodbye!")
            break

        if not query:
            continue
        if query.lower() in ('exit', 'quit', 'q'):
            print("Goodbye!")
            break

        target, results = get_genre_recommendations(query, df)

        if target is None and not results:
            print(f"No movies found matching '{query}'. Please try another search.\n")
        elif target is None and results:
            print(f"Multiple movies matched '{query}':")
            for idx, candidate in enumerate(results[:10], start=1):
                print(f"  {idx}. {candidate}")
            if len(results) > 10:
                print(f"  ... and {len(results) - 10} more. Please refine your query.")
            print("\nPlease type the exact name from the list above.\n")
        else:
            print(f"\nTarget Movie: {target['title']} ({target['year']})")
            print(f"Genres: {target['genres'].replace('|', ' · ')} | Industry: {target['industry']}")
            print(f"\nTop Genre-Based Recommendations:")
            print("-" * 65)
            for idx, r in enumerate(results, start=1):
                genres_fmt = r['genres'].replace('|', ' · ')
                matched_fmt = ', '.join(r['matched_genres'])
                print(f"  {idx}. {r['title']} [{r['match_pct']}% Match]")
                print(f"     Genres: {genres_fmt} (Shared: {matched_fmt})")
            print("-" * 65 + "\n")

if __name__ == '__main__':
    main()
