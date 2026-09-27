import os
import pandas as pd

CSV_PATH = os.path.join(os.path.dirname(__file__), 'MovieRecommendations.csv')

def load_data():
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Could not find {CSV_PATH}")
    return pd.read_csv(CSV_PATH)

def get_recommendations(movie_name, df):
    # Try exact match first
    match = df[df['title'].str.strip().str.lower() == movie_name.strip().lower()]
    
    # If no exact match, search partial matches
    if match.empty:
        matches = df[df['title'].str.contains(movie_name.strip(), case=False, na=False)]
        if matches.empty:
            return None, []
        if len(matches) > 1:
            return None, matches['title'].tolist()
        match = matches

    row = match.iloc[0]
    matched_title = row['title']
    recommendations = [
        row['FirstMovieRecommendation'],
        row['SecondMovieRecommendation'],
        row['ThirdMovieRecommendation'],
        row['FourthMovieRecommendation']
    ]
    # Filter out empty or '-' recommendations
    recommendations = [rec for rec in recommendations if pd.notna(rec) and rec != '-']
    return matched_title, recommendations

def main():
    print("=" * 60)
    print("       Movie Recommendation System (Python & Pandas)")
    print("=" * 60)
    
    df = load_data()
    print(f"Loaded {len(df)} movies from dataset.\n")
    print("Tip: Type a movie name (e.g., 'Star Wars', 'Toy Story', 'Godfather')")
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

        matched_title, results = get_recommendations(query, df)

        if matched_title is None and not results:
            print(f"No movies found matching '{query}'. Please try another search.\n")
        elif matched_title is None and results:
            print(f"Multiple movies matched '{query}':")
            for idx, candidate in enumerate(results[:10], start=1):
                print(f"  {idx}. {candidate}")
            if len(results) > 10:
                print(f"  ... and {len(results) - 10} more. Please refine your query.")
            print("\nPlease type the exact name from the list above.\n")
        else:
            print(f"\nTop Recommendations for '{matched_title}':")
            print("-" * 50)
            if not results:
                print("No strong recommendations found for this movie (insufficient ratings).")
            else:
                for idx, movie in enumerate(results, start=1):
                    print(f"  {idx}. {movie}")
            print("-" * 50 + "\n")

if __name__ == '__main__':
    main()
