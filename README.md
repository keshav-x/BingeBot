# BingeBot

A movie recommendation engine and web dashboard that suggests titles using viewer history, genre similarity, and current mood.

Runs locally with Python and Flask, or directly on Vercel as a zero-server static site.

---

## Features

- 3-signal recommendation model: Combines user taste similarity (50%), genre matching (30%), and mood boost (20%).
- Cold start support: Shows top-rated movies matching the selected mood when a brand-new user has no ratings yet.
- Clear explanations: Tells you why each movie was suggested (e.g. "similar viewers loved this, fits your cerebral mood").
- Works without a backend on Vercel using client-side JavaScript.
- Clean, minimal earth tone interface.

---

## Architecture & How It Works

Here is the simple flow of how BingeBot computes recommendations:

```
User Selects Profile (or New User) + Mood Preference
      |
      v
Check User History in Rating Matrix
      |
      +---> Has Prior Ratings? (Normal Hybrid Flow)
      |       |
      |       |-- 1. Collaborative Filtering (50% weight)
      |       |      Calculates cosine similarity with viewers sharing your taste
      |       |
      |       |-- 2. Content Trait Similarity (30% weight)
      |       |      Matches genres against titles you previously enjoyed
      |       |
      |       \-- 3. Mood Tone Alignment (20% weight)
      |              Applies score boost for matching emotional tone
      |
      +---> Zero Prior Ratings? (Cold Start Mode)
              |
              \-- Automatic Cold-Start Fallback:
                  Ranks titles by catalogue rating + selected mood affinity
      |
      v
Combine Weighted Scores (clamped to 1.0 to 5.0 scale)
      v
Generate Plain-English Attribution & Match Percentage
      v
Display Ranked Movie Cards on Dashboard / Return API JSON
```

### How BingeBot Generates Recommendations

BingeBot recommends films using a mathematical hybrid ranking pipeline:

1. **Collaborative Filtering (50% weight)**: Predicts what you would rate a title (0.0 to 5.0 scale) based on cosine similarity with viewers who share your taste.
2. **Content Trait Similarity (30% weight)**: Computes feature vector similarity with genres and themes you previously watched.
3. **Mood Tone Alignment (20% weight)**: Boosts titles aligned with your requested emotional tone. For new visitors with zero viewing history, it uses an automatic **Cold-Start Popularity Fallback**.

### Breakdown of the Pipeline

1. Input Intake: The user selects a viewer profile, optional genre filter, and situational mood tone via the web dashboard, CLI, or REST API (`/api/recommend`).
2. Dual-Path Execution:
   - Experienced Viewer: Retrieves the user's historical rating vector. Finds similar viewers via cosine distance, extracts preferred genres, and calculates the tri-hybrid recommendation score.
   - Brand-New Viewer (Cold Start): When no ratings exist, it activates the fallback path to rank titles using catalogue popularity and selected mood affinity.
3. Scoring & Normalization: Individual signal weights (50% collaborative, 30% content, 20% mood) are combined, scaled to a 5-star rating, and converted into a match percentage (0 to 100%).
4. Explainable Output: Every suggestion includes a plain-English explanation of why it was chosen (e.g. "Similar viewers loved this, matches genres you watch, fits your cerebral mood.").
5. Dual-Mode Deployment:
   - Local: Runs using Python and Flask via `app.py` at `http://127.0.0.1:5001`.
   - Vercel: Runs entirely client-side using JavaScript in `static/engine.js` without requiring an active server.

---

## Running Locally

### 1. Clone the repo
```bash
git clone https://github.com/keshav-x/BingeBot.git
cd BingeBot
```

### 2. Set up virtual environment (optional)
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 3. Install requirements
```bash
pip install -r requirements.txt
```

### 4. Start the app
```bash
python app.py
```
Open http://127.0.0.1:5001 in your browser.

---

## API Endpoints (Local Flask)

### Get Recommendations
- POST /api/recommend
- Body:
  ```json
  {
    "user_id": "U001",
    "mood": "cerebral",
    "genre": "Sci-Fi",
    "top_n": 3
  }
  ```
- Returns ranked movies with hybrid scores, match percentages, and explanations.

### Get Catalogue & Users
- GET /api/catalogue: Returns full list of movies in the catalogue.
- GET /api/users: Returns available user personas and rating counts.

---

## Project Structure

```
BingeBot/
├── index.html                  # Main dashboard page
├── vercel.json                 # Vercel static hosting config
├── app.py                      # Flask web application and API
├── recommender.py              # Hybrid recommendation algorithms
├── cli.py                      # Command-line interface for terminal usage
├── requirements.txt            # Python dependencies
├── README.md                   # Documentation
├── static/
│   ├── style.css               # Dashboard styling
│   └── engine.js               # Client-side recommendation engine for Vercel
└── sample_data/
    ├── catalogue.json          # Movie dataset
    └── interactions.json       # User rating history
```

---

## Author

Keshav Chaudhary (https://github.com/keshav-x)
