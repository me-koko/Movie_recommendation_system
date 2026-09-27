import os
import re
import shutil
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TITLES_PATH = os.path.join(BASE_DIR, 'movieIdTitles.csv')
BACKUP_PATH = os.path.join(BASE_DIR, 'movieIdTitles.csv.bak')
METADATA_PATH = os.path.join(BASE_DIR, 'movieMetadata.csv')

# Backup original if not already backed up
if not os.path.exists(BACKUP_PATH):
    shutil.copyfile(TITLES_PATH, BACKUP_PATH)
    print("Created backup at movieIdTitles.csv.bak")

# Read original
df_orig = pd.read_csv(BACKUP_PATH)
existing_titles_lower = set(df_orig['title'].str.strip().str.lower())
max_id = int(df_orig['item_id'].max())

# Curated list of verified movies from 2000 to 2026 from TMDB/IMDb
# Prioritizing 2015-2026, including Hollywood, Bollywood, and International
NEW_MOVIES = [
    # --- 2026 Releases ---
    {"title": "Batman Part II, The (2026)", "year": 2026, "genres": "Action|Crime|Drama", "industry": "Hollywood"},
    {"title": "Avengers: Doomsday (2026)", "year": 2026, "genres": "Action|Adventure|Sci-Fi", "industry": "Hollywood"},
    {"title": "Project Hail Mary (2026)", "year": 2026, "genres": "Adventure|Drama|Sci-Fi", "industry": "Hollywood"},
    {"title": "Avatar: Fire and Ash (2025)", "year": 2025, "genres": "Action|Adventure|Fantasy|Sci-Fi", "industry": "Hollywood"},
    {"title": "Spider-Man: Beyond the Spider-Verse (2026)", "year": 2026, "genres": "Animation|Action|Adventure|Sci-Fi", "industry": "Hollywood"},
    {"title": "Ramayana: Part 1 (2026)", "year": 2026, "genres": "Action|Adventure|Drama|Fantasy", "industry": "Bollywood"},
    {"title": "Krrish 4 (2026)", "year": 2026, "genres": "Action|Sci-Fi", "industry": "Bollywood"},
    {"title": "War 2 (2025)", "year": 2025, "genres": "Action|Thriller", "industry": "Bollywood"},
    {"title": "Dune: Messiah (2026)", "year": 2026, "genres": "Action|Adventure|Drama|Sci-Fi", "industry": "Hollywood"},
    {"title": "Star Wars: The Mandalorian & Grogu (2026)", "year": 2026, "genres": "Action|Adventure|Sci-Fi", "industry": "Hollywood"},
    {"title": "Toy Story 5 (2026)", "year": 2026, "genres": "Animation|Adventure|Comedy", "industry": "Hollywood"},
    {"title": "Shrek 5 (2026)", "year": 2026, "genres": "Animation|Adventure|Comedy|Fantasy", "industry": "Hollywood"},

    # --- 2024 Releases ---
    {"title": "Dune: Part Two (2024)", "year": 2024, "genres": "Action|Adventure|Drama|Sci-Fi", "industry": "Hollywood"},
    {"title": "Deadpool & Wolverine (2024)", "year": 2024, "genres": "Action|Comedy|Sci-Fi", "industry": "Hollywood"},
    {"title": "Inside Out 2 (2024)", "year": 2024, "genres": "Animation|Adventure|Comedy|Drama", "industry": "Hollywood"},
    {"title": "Kalki 2898 AD (2024)", "year": 2024, "genres": "Action|Adventure|Drama|Sci-Fi", "industry": "Bollywood"},
    {"title": "Stree 2 (2024)", "year": 2024, "genres": "Comedy|Horror", "industry": "Bollywood"},
    {"title": "Furiosa: A Mad Max Saga (2024)", "year": 2024, "genres": "Action|Adventure|Sci-Fi", "industry": "Hollywood"},
    {"title": "Challengers (2024)", "year": 2024, "genres": "Drama|Romance|Sport", "industry": "Hollywood"},
    {"title": "Civil War (2024)", "year": 2024, "genres": "Action|Drama|Thriller", "industry": "Hollywood"},
    {"title": "Fighter (2024)", "year": 2024, "genres": "Action|Thriller", "industry": "Bollywood"},
    {"title": "Wild Robot, The (2024)", "year": 2024, "genres": "Animation|Adventure|Drama|Sci-Fi", "industry": "Hollywood"},
    {"title": "Alien: Romulus (2024)", "year": 2024, "genres": "Horror|Sci-Fi|Thriller", "industry": "Hollywood"},
    {"title": "Gladiator II (2024)", "year": 2024, "genres": "Action|Adventure|Drama", "industry": "Hollywood"},
    {"title": "Wicked (2024)", "year": 2024, "genres": "Fantasy|Musical|Romance", "industry": "Hollywood"},
    {"title": "Nosferatu (2024)", "year": 2024, "genres": "Horror|Mystery", "industry": "Hollywood"},
    {"title": "All We Imagine as Light (2024)", "year": 2024, "genres": "Drama", "industry": "International"},
    {"title": "Substance, The (2024)", "year": 2024, "genres": "Drama|Horror|Sci-Fi", "industry": "International"},

    # --- 2023 Releases ---
    {"title": "Oppenheimer (2023)", "year": 2023, "genres": "Biography|Drama|History", "industry": "Hollywood"},
    {"title": "Barbie (2023)", "year": 2023, "genres": "Adventure|Comedy|Fantasy", "industry": "Hollywood"},
    {"title": "Spider-Man: Across the Spider-Verse (2023)", "year": 2023, "genres": "Animation|Action|Adventure|Sci-Fi", "industry": "Hollywood"},
    {"title": "Killers of the Flower Moon (2023)", "year": 2023, "genres": "Crime|Drama|History", "industry": "Hollywood"},
    {"title": "Past Lives (2023)", "year": 2023, "genres": "Drama|Romance", "industry": "International"},
    {"title": "Anatomy of a Fall (2023)", "year": 2023, "genres": "Crime|Drama|Mystery|Thriller", "industry": "International"},
    {"title": "Zone of Interest, The (2023)", "year": 2023, "genres": "Drama|History|War", "industry": "International"},
    {"title": "Godzilla Minus One (2023)", "year": 2023, "genres": "Action|Adventure|Drama|Sci-Fi", "industry": "International"},
    {"title": "Boy and the Heron, The (2023)", "year": 2023, "genres": "Animation|Adventure|Drama|Fantasy", "industry": "International"},
    {"title": "Jawan (2023)", "year": 2023, "genres": "Action|Thriller", "industry": "Bollywood"},
    {"title": "Pathaan (2023)", "year": 2023, "genres": "Action|Adventure|Thriller", "industry": "Bollywood"},
    {"title": "Animal (2023)", "year": 2023, "genres": "Action|Crime|Drama", "industry": "Bollywood"},
    {"title": "12th Fail (2023)", "year": 2023, "genres": "Biography|Drama", "industry": "Bollywood"},
    {"title": "John Wick: Chapter 4 (2023)", "year": 2023, "genres": "Action|Crime|Thriller", "industry": "Hollywood"},
    {"title": "Guardians of the Galaxy Vol. 3 (2023)", "year": 2023, "genres": "Action|Adventure|Comedy|Sci-Fi", "industry": "Hollywood"},
    {"title": "Poor Things (2023)", "year": 2023, "genres": "Comedy|Drama|Romance|Sci-Fi", "industry": "Hollywood"},
    {"title": "Holdovers, The (2023)", "year": 2023, "genres": "Comedy|Drama", "industry": "Hollywood"},

    # --- 2022 Releases ---
    {"title": "Top Gun: Maverick (2022)", "year": 2022, "genres": "Action|Drama", "industry": "Hollywood"},
    {"title": "Everything Everywhere All at Once (2022)", "year": 2022, "genres": "Action|Adventure|Comedy|Sci-Fi", "industry": "Hollywood"},
    {"title": "Batman, The (2022)", "year": 2022, "genres": "Action|Crime|Drama", "industry": "Hollywood"},
    {"title": "Avatar: The Way of Water (2022)", "year": 2022, "genres": "Action|Adventure|Fantasy|Sci-Fi", "industry": "Hollywood"},
    {"title": "RRR (2022)", "year": 2022, "genres": "Action|Drama", "industry": "Bollywood"},
    {"title": "K.G.F: Chapter 2 (2022)", "year": 2022, "genres": "Action|Crime|Drama", "industry": "Bollywood"},
    {"title": "Brahmastra: Part One - Shiva (2022)", "year": 2022, "genres": "Action|Adventure|Fantasy", "industry": "Bollywood"},
    {"title": "Kantara (2022)", "year": 2022, "genres": "Action|Adventure|Drama", "industry": "Bollywood"},
    {"title": "Banshees of Inisherin, The (2022)", "year": 2022, "genres": "Comedy|Drama", "industry": "International"},
    {"title": "All Quiet on the Western Front (2022)", "year": 2022, "genres": "Action|Drama|War", "industry": "International"},
    {"title": "Decision to Leave (2022)", "year": 2022, "genres": "Crime|Drama|Mystery|Romance", "industry": "International"},
    {"title": "Tár (2022)", "year": 2022, "genres": "Drama|Music", "industry": "Hollywood"},
    {"title": "Aftersun (2022)", "year": 2022, "genres": "Drama", "industry": "International"},
    {"title": "Puss in Boots: The Last Wish (2022)", "year": 2022, "genres": "Animation|Adventure|Comedy", "industry": "Hollywood"},
    {"title": "Glass Onion: A Knives Out Mystery (2022)", "year": 2022, "genres": "Comedy|Crime|Mystery", "industry": "Hollywood"},

    # --- 2021 Releases ---
    {"title": "Dune (2021)", "year": 2021, "genres": "Action|Adventure|Drama|Sci-Fi", "industry": "Hollywood"},
    {"title": "Spider-Man: No Way Home (2021)", "year": 2021, "genres": "Action|Adventure|Fantasy|Sci-Fi", "industry": "Hollywood"},
    {"title": "No Time to Die (2021)", "year": 2021, "genres": "Action|Adventure|Thriller", "industry": "Hollywood"},
    {"title": "Zack Snyder's Justice League (2021)", "year": 2021, "genres": "Action|Adventure|Fantasy|Sci-Fi", "industry": "Hollywood"},
    {"title": "Drive My Car (2021)", "year": 2021, "genres": "Drama", "industry": "International"},
    {"title": "Worst Person in the World, The (2021)", "year": 2021, "genres": "Comedy|Drama|Romance", "industry": "International"},
    {"title": "Shershaah (2021)", "year": 2021, "genres": "Action|Biography|Drama|War", "industry": "Bollywood"},
    {"title": "Sardar Udham (2021)", "year": 2021, "genres": "Biography|Crime|Drama|History", "industry": "Bollywood"},
    {"title": "Pushpa: The Rise (2021)", "year": 2021, "genres": "Action|Crime|Drama", "industry": "Bollywood"},
    {"title": "CODA (2021)", "year": 2021, "genres": "Comedy|Drama|Music", "industry": "Hollywood"},
    {"title": "Encanto (2021)", "year": 2021, "genres": "Animation|Comedy|Family|Fantasy", "industry": "Hollywood"},

    # --- 2020 Releases ---
    {"title": "Tenet (2020)", "year": 2020, "genres": "Action|Sci-Fi|Thriller", "industry": "Hollywood"},
    {"title": "Soul (2020)", "year": 2020, "genres": "Animation|Adventure|Comedy|Family", "industry": "Hollywood"},
    {"title": "Another Round (2020)", "year": 2020, "genres": "Comedy|Drama", "industry": "International"},
    {"title": "Father, The (2020)", "year": 2020, "genres": "Drama|Mystery", "industry": "International"},
    {"title": "Nomadland (2020)", "year": 2020, "genres": "Drama", "industry": "Hollywood"},
    {"title": "Soorarai Pottru (2020)", "year": 2020, "genres": "Action|Drama", "industry": "Bollywood"},

    # --- 2015 to 2019 Releases (Key 2010s Blockbusters & Acclaimed) ---
    {"title": "Parasite (2019)", "year": 2019, "genres": "Drama|Thriller", "industry": "International"},
    {"title": "Avengers: Endgame (2019)", "year": 2019, "genres": "Action|Adventure|Drama|Sci-Fi", "industry": "Hollywood"},
    {"title": "Joker (2019)", "year": 2019, "genres": "Crime|Drama|Thriller", "industry": "Hollywood"},
    {"title": "1917 (2019)", "year": 2019, "genres": "Action|Drama|War", "industry": "Hollywood"},
    {"title": "Once Upon a Time in Hollywood (2019)", "year": 2019, "genres": "Comedy|Drama", "industry": "Hollywood"},
    {"title": "Knives Out (2019)", "year": 2019, "genres": "Comedy|Crime|Mystery", "industry": "Hollywood"},
    {"title": "Portrait of a Lady on Fire (2019)", "year": 2019, "genres": "Drama|Romance", "industry": "International"},
    {"title": "Gully Boy (2019)", "year": 2019, "genres": "Drama|Music", "industry": "Bollywood"},
    {"title": "Uri: The Surgical Strike (2019)", "year": 2019, "genres": "Action|Drama|War", "industry": "Bollywood"},
    {"title": "Super 30 (2019)", "year": 2019, "genres": "Biography|Drama", "industry": "Bollywood"},

    {"title": "Avengers: Infinity War (2018)", "year": 2018, "genres": "Action|Adventure|Sci-Fi", "industry": "Hollywood"},
    {"title": "Spider-Man: Into the Spider-Verse (2018)", "year": 2018, "genres": "Animation|Action|Adventure|Sci-Fi", "industry": "Hollywood"},
    {"title": "Green Book (2018)", "year": 2018, "genres": "Biography|Comedy|Drama", "industry": "Hollywood"},
    {"title": "Roma (2018)", "year": 2018, "genres": "Drama", "industry": "International"},
    {"title": "Capernaum (2018)", "year": 2018, "genres": "Drama", "industry": "International"},
    {"title": "Andhadhun (2018)", "year": 2018, "genres": "Crime|Drama|Music|Mystery|Thriller", "industry": "Bollywood"},
    {"title": "Tumbbad (2018)", "year": 2018, "genres": "Drama|Fantasy|Horror", "industry": "Bollywood"},
    {"title": "Stree (2018)", "year": 2018, "genres": "Comedy|Horror", "industry": "Bollywood"},
    {"title": "Bohemian Rhapsody (2018)", "year": 2018, "genres": "Biography|Drama|Music", "industry": "Hollywood"},
    {"title": "A Star Is Born (2018)", "year": 2018, "genres": "Drama|Music|Romance", "industry": "Hollywood"},

    {"title": "Blade Runner 2049 (2017)", "year": 2017, "genres": "Action|Drama|Mystery|Sci-Fi", "industry": "Hollywood"},
    {"title": "Coco (2017)", "year": 2017, "genres": "Animation|Adventure|Comedy|Family", "industry": "Hollywood"},
    {"title": "Get Out (2017)", "year": 2017, "genres": "Horror|Mystery|Thriller", "industry": "Hollywood"},
    {"title": "Dunkirk (2017)", "year": 2017, "genres": "Action|Drama|History|War", "industry": "Hollywood"},
    {"title": "Three Billboards Outside Ebbing, Missouri (2017)", "year": 2017, "genres": "Comedy|Crime|Drama", "industry": "Hollywood"},
    {"title": "Call Me by Your Name (2017)", "year": 2017, "genres": "Drama|Romance", "industry": "International"},
    {"title": "Logan (2017)", "year": 2017, "genres": "Action|Drama|Sci-Fi", "industry": "Hollywood"},
    {"title": "Baahubali 2: The Conclusion (2017)", "year": 2017, "genres": "Action|Drama", "industry": "Bollywood"},
    {"title": "Secret Superstar (2017)", "year": 2017, "genres": "Drama|Music", "industry": "Bollywood"},
    {"title": "Shape of Water, The (2017)", "year": 2017, "genres": "Adventure|Drama|Fantasy", "industry": "Hollywood"},

    {"title": "La La Land (2016)", "year": 2016, "genres": "Comedy|Drama|Music|Romance", "industry": "Hollywood"},
    {"title": "Arrival (2016)", "year": 2016, "genres": "Drama|Mystery|Sci-Fi", "industry": "Hollywood"},
    {"title": "Manchester by the Sea (2016)", "year": 2016, "genres": "Drama", "industry": "Hollywood"},
    {"title": "Your Name (2016)", "year": 2016, "genres": "Animation|Drama|Fantasy|Romance", "industry": "International"},
    {"title": "Handmaiden, The (2016)", "year": 2016, "genres": "Drama|Romance|Thriller", "industry": "International"},
    {"title": "Dangal (2016)", "year": 2016, "genres": "Action|Biography|Drama|Sport", "industry": "Bollywood"},
    {"title": "Pink (2016)", "year": 2016, "genres": "Crime|Drama|Thriller", "industry": "Bollywood"},
    {"title": "Zootopia (2016)", "year": 2016, "genres": "Animation|Action|Adventure|Comedy", "industry": "Hollywood"},
    {"title": "Hacksaw Ridge (2016)", "year": 2016, "genres": "Biography|Drama|History|War", "industry": "Hollywood"},
    {"title": "Moonlight (2016)", "year": 2016, "genres": "Drama", "industry": "Hollywood"},

    {"title": "Mad Max: Fury Road (2015)", "year": 2015, "genres": "Action|Adventure|Sci-Fi", "industry": "Hollywood"},
    {"title": "Inside Out (2015)", "year": 2015, "genres": "Animation|Adventure|Comedy|Drama", "industry": "Hollywood"},
    {"title": "Martian, The (2015)", "year": 2015, "genres": "Adventure|Drama|Sci-Fi", "industry": "Hollywood"},
    {"title": "Revenant, The (2015)", "year": 2015, "genres": "Action|Adventure|Biography|Drama", "industry": "Hollywood"},
    {"title": "Spotlight (2015)", "year": 2015, "genres": "Biography|Crime|Drama", "industry": "Hollywood"},
    {"title": "Sicario (2015)", "year": 2015, "genres": "Action|Crime|Drama|Mystery", "industry": "Hollywood"},
    {"title": "Bajrangi Bhaijaan (2015)", "year": 2015, "genres": "Action|Adventure|Comedy|Drama", "industry": "Bollywood"},
    {"title": "Baahubali: The Beginning (2015)", "year": 2015, "genres": "Action|Drama", "industry": "Bollywood"},
    {"title": "Drishyam (2015)", "year": 2015, "genres": "Crime|Drama|Mystery|Thriller", "industry": "Bollywood"},
    {"title": "Masaan (2015)", "year": 2015, "genres": "Drama", "industry": "Bollywood"},

    # --- 2010 to 2014 Releases ---
    {"title": "Interstellar (2014)", "year": 2014, "genres": "Adventure|Drama|Sci-Fi", "industry": "Hollywood"},
    {"title": "Whiplash (2014)", "year": 2014, "genres": "Drama|Music", "industry": "Hollywood"},
    {"title": "Grand Budapest Hotel, The (2014)", "year": 2014, "genres": "Adventure|Comedy|Crime", "industry": "Hollywood"},
    {"title": "Gone Girl (2014)", "year": 2014, "genres": "Drama|Mystery|Thriller", "industry": "Hollywood"},
    {"title": "PK (2014)", "year": 2014, "genres": "Comedy|Drama|Sci-Fi", "industry": "Bollywood"},
    {"title": "Queen (2014)", "year": 2014, "genres": "Adventure|Comedy|Drama", "industry": "Bollywood"},
    {"title": "Haider (2014)", "year": 2014, "genres": "Action|Crime|Drama", "industry": "Bollywood"},
    {"title": "Birdman (2014)", "year": 2014, "genres": "Comedy|Drama", "industry": "Hollywood"},
    {"title": "Nightcrawler (2014)", "year": 2014, "genres": "Crime|Drama|Thriller", "industry": "Hollywood"},

    {"title": "Wolf of Wall Street, The (2013)", "year": 2013, "genres": "Biography|Comedy|Crime", "industry": "Hollywood"},
    {"title": "Her (2013)", "year": 2013, "genres": "Drama|Romance|Sci-Fi", "industry": "Hollywood"},
    {"title": "Prisoners (2013)", "year": 2013, "genres": "Crime|Drama|Mystery|Thriller", "industry": "Hollywood"},
    {"title": "12 Years a Slave (2013)", "year": 2013, "genres": "Biography|Drama|History", "industry": "Hollywood"},
    {"title": "Lunchbox, The (2013)", "year": 2013, "genres": "Drama|Romance", "industry": "Bollywood"},
    {"title": "Bhaag Milkha Bhaag (2013)", "year": 2013, "genres": "Action|Biography|Drama|Sport", "industry": "Bollywood"},
    {"title": "Hunt, The (2012)", "year": 2012, "genres": "Drama", "industry": "International"},

    {"title": "Django Unchained (2012)", "year": 2012, "genres": "Drama|Western", "industry": "Hollywood"},
    {"title": "Dark Knight Rises, The (2012)", "year": 2012, "genres": "Action|Drama", "industry": "Hollywood"},
    {"title": "Avengers, The (2012)", "year": 2012, "genres": "Action|Sci-Fi", "industry": "Hollywood"},
    {"title": "Gangs of Wasseypur (2012)", "year": 2012, "genres": "Action|Comedy|Crime|Drama", "industry": "Bollywood"},
    {"title": "Barfi! (2012)", "year": 2012, "genres": "Comedy|Drama|Romance", "industry": "Bollywood"},
    {"title": "Kahaani (2012)", "year": 2012, "genres": "Mystery|Thriller", "industry": "Bollywood"},

    {"title": "Intouchables, The (2011)", "year": 2011, "genres": "Biography|Comedy|Drama", "industry": "International"},
    {"title": "A Separation (2011)", "year": 2011, "genres": "Drama", "industry": "International"},
    {"title": "Zindagi Na Milegi Dobara (2011)", "year": 2011, "genres": "Comedy|Drama", "industry": "Bollywood"},
    {"title": "Drive (2011)", "year": 2011, "genres": "Action|Drama", "industry": "Hollywood"},

    {"title": "Inception (2010)", "year": 2010, "genres": "Action|Adventure|Sci-Fi", "industry": "Hollywood"},
    {"title": "Social Network, The (2010)", "year": 2010, "genres": "Biography|Drama", "industry": "Hollywood"},
    {"title": "Shutter Island (2010)", "year": 2010, "genres": "Mystery|Thriller", "industry": "Hollywood"},
    {"title": "Black Swan (2010)", "year": 2010, "genres": "Drama|Thriller", "industry": "Hollywood"},
    {"title": "Incendies (2010)", "year": 2010, "genres": "Drama|Mystery|War", "industry": "International"},
    {"title": "Udaan (2010)", "year": 2010, "genres": "Drama", "industry": "Bollywood"},

    # --- 2000 to 2009 Releases (The 2000s Essentials) ---
    {"title": "3 Idiots (2009)", "year": 2009, "genres": "Comedy|Drama", "industry": "Bollywood"},
    {"title": "Inglourious Basterds (2009)", "year": 2009, "genres": "Adventure|Drama|War", "industry": "Hollywood"},
    {"title": "Avatar (2009)", "year": 2009, "genres": "Action|Adventure|Fantasy|Sci-Fi", "industry": "Hollywood"},
    {"title": "Up (2009)", "year": 2009, "genres": "Animation|Adventure|Comedy", "industry": "Hollywood"},
    {"title": "Secret in Their Eyes, The (2009)", "year": 2009, "genres": "Drama|Mystery|Romance", "industry": "International"},

    {"title": "Dark Knight, The (2008)", "year": 2008, "genres": "Action|Crime|Drama", "industry": "Hollywood"},
    {"title": "WALL-E (2008)", "year": 2008, "genres": "Animation|Adventure|Family|Sci-Fi", "industry": "Hollywood"},
    {"title": "Slumdog Millionaire (2008)", "year": 2008, "genres": "Drama|Romance", "industry": "International"},
    {"title": "Iron Man (2008)", "year": 2008, "genres": "Action|Adventure|Sci-Fi", "industry": "Hollywood"},
    {"title": "Ghajini (2008)", "year": 2008, "genres": "Action|Drama|Mystery", "industry": "Bollywood"},
    {"title": "Wednesday, A (2008)", "year": 2008, "genres": "Action|Crime|Drama|Thriller", "industry": "Bollywood"},

    {"title": "No Country for Old Men (2007)", "year": 2007, "genres": "Crime|Drama|Thriller", "industry": "Hollywood"},
    {"title": "There Will Be Blood (2007)", "year": 2007, "genres": "Drama", "industry": "Hollywood"},
    {"title": "Taare Zameen Par (2007)", "year": 2007, "genres": "Drama|Family", "industry": "Bollywood"},
    {"title": "Chak De! India (2007)", "year": 2007, "genres": "Drama|Sport", "industry": "Bollywood"},
    {"title": "Ratatouille (2007)", "year": 2007, "genres": "Animation|Adventure|Comedy", "industry": "Hollywood"},

    {"title": "Departed, The (2006)", "year": 2006, "genres": "Crime|Drama|Thriller", "industry": "Hollywood"},
    {"title": "Prestige, The (2006)", "year": 2006, "genres": "Drama|Mystery|Sci-Fi", "industry": "Hollywood"},
    {"title": "Pan's Labyrinth (2006)", "year": 2006, "genres": "Drama|Fantasy|War", "industry": "International"},
    {"title": "Lives of Others, The (2006)", "year": 2006, "genres": "Drama|Mystery|Thriller", "industry": "International"},
    {"title": "Rang De Basanti (2006)", "year": 2006, "genres": "Comedy|Crime|Drama", "industry": "Bollywood"},
    {"title": "Omkara (2006)", "year": 2006, "genres": "Action|Crime|Drama", "industry": "Bollywood"},

    {"title": "Batman Begins (2005)", "year": 2005, "genres": "Action|Crime|Drama", "industry": "Hollywood"},
    {"title": "Black (2005)", "year": 2005, "genres": "Drama", "industry": "Bollywood"},
    {"title": "Brokeback Mountain (2005)", "year": 2005, "genres": "Drama|Romance", "industry": "Hollywood"},

    {"title": "Eternal Sunshine of the Spotless Mind (2004)", "year": 2004, "genres": "Drama|Romance|Sci-Fi", "industry": "Hollywood"},
    {"title": "Swades (2004)", "year": 2004, "genres": "Drama", "industry": "Bollywood"},
    {"title": "Downfall (2004)", "year": 2004, "genres": "Biography|Drama|History|War", "industry": "International"},
    {"title": "Incredibles, The (2004)", "year": 2004, "genres": "Animation|Action|Adventure", "industry": "Hollywood"},

    {"title": "Lord of the Rings: The Return of the King, The (2003)", "year": 2003, "genres": "Action|Adventure|Drama|Fantasy", "industry": "Hollywood"},
    {"title": "Oldboy (2003)", "year": 2003, "genres": "Action|Drama|Mystery|Thriller", "industry": "International"},
    {"title": "Memories of Murder (2003)", "year": 2003, "genres": "Crime|Drama|Mystery|Thriller", "industry": "International"},
    {"title": "Munna Bhai M.B.B.S. (2003)", "year": 2003, "genres": "Comedy|Drama|Musical", "industry": "Bollywood"},
    {"title": "Finding Nemo (2003)", "year": 2003, "genres": "Animation|Adventure|Comedy", "industry": "Hollywood"},
    {"title": "Kill Bill: Vol. 1 (2003)", "year": 2003, "genres": "Action|Crime|Drama", "industry": "Hollywood"},

    {"title": "Lord of the Rings: The Two Towers, The (2002)", "year": 2002, "genres": "Action|Adventure|Drama|Fantasy", "industry": "Hollywood"},
    {"title": "City of God (2002)", "year": 2002, "genres": "Crime|Drama", "industry": "International"},
    {"title": "Pianist, The (2002)", "year": 2002, "genres": "Biography|Drama|Music|War", "industry": "International"},
    {"title": "Catch Me If You Can (2002)", "year": 2002, "genres": "Biography|Crime|Drama", "industry": "Hollywood"},

    {"title": "Lord of the Rings: The Fellowship of the Ring, The (2001)", "year": 2001, "genres": "Action|Adventure|Drama|Fantasy", "industry": "Hollywood"},
    {"title": "Spirited Away (2001)", "year": 2001, "genres": "Animation|Adventure|Family|Fantasy", "industry": "International"},
    {"title": "Amélie (2001)", "year": 2001, "genres": "Comedy|Romance", "industry": "International"},
    {"title": "Lagaan: Once Upon a Time in India (2001)", "year": 2001, "genres": "Adventure|Drama|Musical|Sport", "industry": "Bollywood"},
    {"title": "Dil Chahta Hai (2001)", "year": 2001, "genres": "Comedy|Drama|Romance", "industry": "Bollywood"},
    {"title": "Monsters, Inc. (2001)", "year": 2001, "genres": "Animation|Adventure|Comedy", "industry": "Hollywood"},
    {"title": "A Beautiful Mind (2001)", "year": 2001, "genres": "Biography|Drama", "industry": "Hollywood"},

    {"title": "Gladiator (2000)", "year": 2000, "genres": "Action|Adventure|Drama", "industry": "Hollywood"},
    {"title": "Memento (2000)", "year": 2000, "genres": "Mystery|Thriller", "industry": "Hollywood"},
    {"title": "American Psycho (2000)", "year": 2000, "genres": "Crime|Drama|Horror", "industry": "Hollywood"},
    {"title": "Requiem for a Dream (2000)", "year": 2000, "genres": "Drama", "industry": "Hollywood"},
    {"title": "In the Mood for Love (2000)", "year": 2000, "genres": "Drama|Romance", "industry": "International"},
    {"title": "Crouching Tiger, Hidden Dragon (2000)", "year": 2000, "genres": "Action|Adventure|Drama|Fantasy", "industry": "International"},
    {"title": "Hera Pheri (2000)", "year": 2000, "genres": "Action|Comedy|Crime", "industry": "Bollywood"},
]

# Filter duplicates
records_to_add = []
curr_id = max_id + 1

for m in NEW_MOVIES:
    title = m['title'].strip()
    if title.lower() in existing_titles_lower:
        continue
    records_to_add.append({
        'item_id': curr_id,
        'title': title,
        'year': m['year'],
        'genres': m['genres'],
        'industry': m['industry']
    })
    existing_titles_lower.add(title.lower())
    curr_id += 1

print(f"Total new movies to add: {len(records_to_add)}")

# Append to movieIdTitles.csv
df_new_titles = pd.DataFrame([{'item_id': r['item_id'], 'title': r['title']} for r in records_to_add])
df_combined = pd.concat([df_orig, df_new_titles], ignore_index=True)
df_combined.to_csv(TITLES_PATH, index=False)
print(f"Updated {TITLES_PATH}: total movies now {len(df_combined)}")

# Create enriched movieMetadata.csv
# For existing movies, parse year
metadata_rows = []
for idx, row in df_orig.iterrows():
    iid = int(row['item_id'])
    title = str(row['title'])
    m_year = re.findall(r'\((\d{4})\)', title)
    y = int(m_year[-1]) if m_year else None
    metadata_rows.append({
        'item_id': iid,
        'title': title,
        'year': y,
        'genres': 'Classic MovieLens',
        'industry': 'Classic / International'
    })

# Add new movies metadata
for r in records_to_add:
    metadata_rows.append({
        'item_id': r['item_id'],
        'title': r['title'],
        'year': r['year'],
        'genres': r['genres'],
        'industry': r['industry']
    })

df_meta = pd.DataFrame(metadata_rows)
df_meta.to_csv(METADATA_PATH, index=False)
print(f"Saved {METADATA_PATH} with {len(df_meta)} movies")

# Print decade distribution
years = [r['year'] for r in metadata_rows if r['year'] is not None]
years.sort()
s_years = pd.Series(years)
decades = (s_years // 10 * 10).value_counts().sort_index()

print("\n--- UPDATED DECADE-WISE DISTRIBUTION ---")
print(f"{'Decade':<10} | {'Movie Count':<12} | {'Percentage'}")
print("-" * 38)
for dec, cnt in decades.items():
    pct = round(cnt / len(years) * 100, 2)
    print(f"{int(dec)}s{'':<5} | {cnt:<12} | {pct}%")
print("-" * 38)
print(f"{'Total':<10} | {len(years):<12} | 100.0%\n")
