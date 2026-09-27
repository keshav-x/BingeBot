# BingeBot

Hybrid content recommendation engine and web dashboard that suggests movies based on viewer history, genre similarity, and current mood context.

Built to run 100% self-contained with zero server dependencies on Vercel and zero paid subscriptions.

---

## Key Features

- Tri-Hybrid Ranking: Combines collaborative viewer signals (50%), content genre similarity (30%), and mood boost (20%).
- Cold-Start Fallback: Instantly provides top-rated, mood-filtered recommendations for new viewers with zero rating history.
- Plain-English Attribution: Every suggestion explains why it was selected (similar viewer ratings, shared genres, or mood fit).
- Dual-Mode Architecture: Runs locally on a Python Flask backend (http://127.0.0.1:5001), or as a zero-server Edge app on Vercel using client-side JavaScript.
- Clean Earth Palette: Styled in a high-contrast executive theme (rust, amber, forest green, charcoal on warm ivory).

---

## System Architecture

```
+---------------------------------------------------------+
|             Viewer ID + Mood + Genre Choice             |
+---------------------------------------------------------+
                             |
                             v
                   Is this a new user?
                             |
            +----------------+----------------+
            |                                 |
         (Yes)                               (No)
            |                                 |
            v                                 v
+-----------------------+     +-------------------------------+
| Cold Start Fallback   |     | Calculate 3 Hybrid Signals    |
| Highest rated titles  |     | 1. Collaborative (50% weight) |
| + Mood filter match   |     | 2. Content Genre (30% weight) |
+-----------------------+     | 3. Mood Boost    (20% weight) |
            |                 +-------------------------------+
            |                                 |
            +----------------+----------------+
                             |
                             v
+---------------------------------------------------------+
|                 Combine into Final Score                |
| Final Score = (0.50 * Collab) + (0.30 * Content) + Mood |
| Clamped to 1.0 - 5.0 stars (0% - 100% match)            |
+---------------------------------------------------------+
                             |
                             v
+---------------------------------------------------------+
|                Ranked Movie Recommendations             |
| With plain-text explanation of why each was picked      |
+---------------------------------------------------------+
```

### How the Pipeline Works

1. Viewer Context:
   Accepts user persona ID, situational mood (such as cerebral, dark, adrenaline, uplifting), and preferred genre.

2. Signal 1 - Collaborative Filtering (50% weight):
   Uses cosine similarity over the user-item rating matrix to identify viewers with matching taste. Predicts rating based on what similar viewers enjoyed.

3. Signal 2 - Content Similarity (30% weight):
   Calculates genre overlap between candidate movies and titles previously rated 4 stars or higher by this user.

4. Signal 3 - Mood Context Boost (20% weight):
   Adds a bonus score when candidate movie tags directly match the viewer's requested mood.

5. Cold Start Fallback:
   When a new viewer has zero rating history, the engine falls back to highest-rated titles filtered by the selected mood.

6. Final Scoring Calculation:
   Score = (0.50 * Collaborative) + (0.30 * Content) + (0.20 * Mood Boost * 5.0)
   - Clamped between 1.0 and 5.0 stars.
   - Normalized match percentage = (Score / 5.0) * 100.

7. Dual-Mode Execution:
   - Local Mode: Uses app.py with Flask, NumPy, and Scikit-Learn.
   - Vercel Serverless Mode: Runs recommendation math in client-side JavaScript inside static/engine.js. Executes in under 1ms with zero backend server.

---

## Local Setup & Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/keshav-x/BingeBot.git
cd BingeBot
```

### 2. (Optional) Create Virtual Environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Local Server
```bash
python app.py
```
Open http://127.0.0.1:5001 in your browser.

---

## How to Deploy on Vercel (Zero Server Needed)

BingeBot runs on Vercel without needing any backend server, subscription, or container:

1. Push or fork this repository to your GitHub account.
2. Log in to Vercel (https://vercel.com) and click "Add New Project".
3. Import the BingeBot repository.
4. Leave build settings as default (Framework Preset: Other, Build Command: empty, Output Directory: ./).
5. Click "Deploy".

Vercel serves index.html and static files directly from its global Edge network.

---

## REST API Specification (When Running Locally)

### Compute Recommendations
- Endpoint: POST /api/recommend
- Payload:
  ```json
  {
    "user_id": "U001",
    "mood": "cerebral",
    "genre": "Sci-Fi",
    "top_n": 3
  }
  ```
- Response:
  ```json
  {
    "user_id": "U001",
    "is_cold_start": false,
    "recommendations": [
      {
        "title": "Inception",
        "year": 2010,
        "genre": ["Sci-Fi", "Thriller"],
        "catalogue_rating": 4.8,
        "hybrid_score": 4.8,
        "scores": {
          "collaborative": 4.8,
          "content": 4.2,
          "mood_boost": 0.2
        },
        "explanation": "Similar viewers loved this, matches genres you watch, fits your cerebral mood."
      }
    ]
  }
  ```

---

## Project Structure

```
BingeBot/
├── index.html                  # Standalone Vercel Edge frontend
├── vercel.json                 # Vercel deployment configuration
├── app.py                      # Flask REST API and recommendation engine
├── requirements.txt            # Minimal dependencies (Flask, scikit-learn, numpy, pandas)
├── README.md                   # Project documentation
├── static/
│   ├── style.css               # Executive Earth design system (CSS)
│   └── engine.js               # Client-side recommendation engine (JS)
└── sample_data/
    ├── catalogue.json          # Benchmark movie catalogue
    └── interactions.json       # Viewer rating history
```

---

## Author

Developed by Keshav Chaudhary (https://github.com/keshav-x).
