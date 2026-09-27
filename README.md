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

Here is the simple flow of how recommendations are calculated:

```
User Selection (User Profile, Current Mood, Optional Genre)
      |
      v
Is this a brand new user with no history?
      |-- Yes -> Show highest-rated movies matching their mood (Cold Start)
      |-- No  -> Calculate 3 signals:
      |            1. Collaborative (50%): What similar viewers liked
      |            2. Content (30%): Movies sharing genres with past 4+ star ratings
      |            3. Mood Boost (20%): Extra points if movie matches current mood
      v
Combine into final score (1.0 to 5.0 stars and match percentage)
      v
Show ranked movie recommendations with reasons why each was picked
```

### Breakdown of the Pipeline

1. Taste Similarity (50%): Uses cosine similarity across user rating history to find other people who like the same kinds of movies. We use their ratings to predict what you will enjoy.
2. Genre Matching (30%): Looks at the movies you rated 4 or 5 stars and compares their genres to other titles in the catalogue.
3. Mood Boost (20%): If you select a mood like "cerebral", "dark", or "adrenaline", movies tagged with that mood get a boost in ranking.
4. New User Fallback (Cold Start): When a new user with zero ratings opens the app, instead of showing an empty screen, we show the highest-rated movies that fit their chosen mood.
5. Dual-Mode Setup:
   - Local: Runs via app.py using Flask, NumPy, and Scikit-Learn at http://127.0.0.1:5001.
   - Vercel: Runs all matrix math directly in the browser with JavaScript (static/engine.js). Requires zero backend server or hosting fees.

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
├── app.py                      # Flask backend and recommendation logic
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
