# Movie Recommendation System (1922–2026)

An interactive, full-stack Movie Recommendation System built with **Python**, **Pandas**, **MovieLens**, and **Flask**. It leverages **Item-Based Collaborative Filtering (Pearson Correlation)** to uncover statistically correlated titles, enhanced with dynamic movie posters and a curated catalog spanning from **1922 to 2026** across Hollywood, Bollywood, and International cinema.

---

## ✨ Features

- **Item-Based Collaborative Filtering**: Computes Pearson correlation coefficients over the user-item interaction matrix.
- **Modern, Responsive Dark-Themed UI**: Built with modern typography, centered layout, and subtle glow & hover effects.
- **Dynamic Theatrical Movie Posters**: Asynchronously fetches official movie posters from Wikipedia/Wikimedia with fallback support.
- **Smart Search & Autocomplete**: Search by movie title or release year with real-time suggestion thumbnails and keyboard navigation.
- **Expanded Dataset (1922–2026)**:
  - 1,894 movies across 11 decades (1920s to 2026).
  - Includes iconic releases from Christopher Nolan, Denis Villeneuve, Marvel/DC, Bollywood blockbusters (*RRR*, *Dangal*, *KGF*, *Stree 2*, *Jawan*), and international cinema (*Parasite*, *Spirited Away*, *Anatomy of a Fall*).
  - Preserves 100% data integrity without fabricated user rating matrices.
- **Interactive Traversal**: Click any recommendation card to pivot and explore recommendations based on that movie.
- **"Refresh Recommendations" Button**: Cycle to the next tier of correlated titles.
- **Decade Distribution Modal**: Inspect live catalog breakdowns and statistics right inside the web app.
- **Terminal CLI Runner**: Interactive command-line script for quick lookups without opening a browser.

---

## 🚀 Quick Start

### 1. Requirements
Ensure Python 3.9+ is installed:
```bash
pip install pandas flask matplotlib seaborn
```

### 2. Run Web Application (Recommended)
```bash
python app.py
```
Open your web browser and navigate to:
👉 **http://127.0.0.1:5000**

### 3. Run Command-Line Interface (CLI)
```bash
python recommend.py
```

---

## 📁 Project Structure

```text
Movie_recommendation_system/
├── app.py                      # Flask web server & dual recommendation engine
├── recommend.py                # Terminal interactive recommendation CLI
├── dataset.csv                 # MovieLens 100k user-item rating logs
├── movieIdTitles.csv           # Complete movie title catalog (1,894 titles)
├── movieMetadata.csv           # Enriched metadata (genres, industries, years)
├── MovieRecommendations.csv    # Precomputed correlation matrices
├── expand_dataset.py           # Dataset expansion & decade validation script
├── Movie Recommender System.ipynb # Original research Jupyter Notebook
├── README.md                   # Project documentation
└── .gitignore                  # Git ignored files
```

---

## 📊 Dataset Distribution

| Decade | Movie Count | Catalog Share |
| :--- | :--- | :--- |
| **1920s** | 2 | 0.11% |
| **1930s** | 29 | 1.53% |
| **1940s** | 45 | 2.38% |
| **1950s** | 57 | 3.01% |
| **1960s** | 46 | 2.43% |
| **1970s** | 55 | 2.91% |
| **1980s** | 110 | 5.81% |
| **1990s** | 1,336 | 70.61% |
| **2000s** | 53 | 2.80% |
| **2010s** | 82 | 4.33% |
| **2020s & 2026** | 77 | 4.07% |
| **Total** | **1,894** | **100.0%** |
