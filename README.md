# BingeBot: Hybrid OTT Content Recommendation Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Vercel Ready](https://img.shields.io/badge/Vercel-Deployed-black.svg)](https://vercel.com)

A mathematical, multi-signal recommendation engine and interactive web console that combines **Collaborative Filtering** (viewer taste similarity), **Content Trait Similarity** (genres and themes), and **Mood Tone Context** for streaming discovery.

Built to run **100% self-contained** with **zero server dependencies on Vercel** and **zero paid subscriptions**.

---

## Key Features

- **Tri-Hybrid Ranking Formula**: Mathematically balances collaborative user signals (50%), content similarity (30%), and viewer mood boost (20%).
- **Automated Cold-Start Fallback**: Instantly provides top-rated, mood-filtered recommendations for new viewers with zero interaction history.
- **Explainable Attribution**: Every suggestion breaks down *why* it was selected (similar viewer ratings + content overlap + mood boost).
- **Dual-Mode Architecture**: Runs as a full Python Flask backend locally (`http://127.0.0.1:5001`), or as a zero-server Edge application when deployed to Vercel.
- **Executive Earth Design**: Styled in a refined, high-contrast masculine palette (Terracotta Rust, Burnished Amber, Forest Green, Deep Charcoal on warm ivory).

---

## Recommendation Formulation

For a viewer $u$ and candidate title $i$, the engine computes an affinity rating on a **0.0 to 5.0 star scale**:

$$\text{Score}(u, i) = (0.50 \times S_{\text{collab}}) + (0.30 \times S_{\text{content}}) + (0.20 \times S_{\text{mood}} \times 5.0)$$

- **Predicted Rating**: Clamped between `1.0` and `5.0` stars.
- **Match Percentage**: Strictly normalized from `0%` to `100%`:
  $$\text{Match \%} = \min\left(100, \max\left(0, \text{round}\left(\frac{\text{Score}}{5.0} \times 100\right)\right)\right)$$

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
Open **`http://127.0.0.1:5001`** in your browser.

---

## How to Deploy on Vercel (Zero Server Needed)

BingeBot is architected to run on Vercel **without needing any backend server, subscription, or container**:

1. Fork or push this repository to your GitHub account (`keshav-x/BingeBot`).
2. Log in to [Vercel](https://vercel.com) and click **"Add New Project"**.
3. Import the `BingeBot` repository.
4. Leave all build settings as default (Framework Preset: **Other**, Build Command: empty, Output Directory: `./`).
5. Click **"Deploy"**.

Vercel will serve `index.html` directly from its global Edge network. The recommendation engine executes in the browser in `<1ms` with full functionality.

---

## REST API Specification (When Running Locally)

### Compute Recommendations
- **Endpoint**: `POST /api/recommend`
- **Payload**:
  ```json
  {
    "user_id": "U001",
    "mood": "cerebral",
    "genre": "Sci-Fi",
    "top_n": 3
  }
  ```
- **Response**:
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
        "explanation": "Users with similar taste rated this highly; shares genre traits; matches requested cerebral mood."
      }
    ]
  }
  ```

---

## Project Structure

```
BingeBot/
├── index.html                  # Standalone Vercel Edge frontend (embedded engine)
├── vercel.json                 # Vercel deployment configuration
├── app.py                      # Flask REST API & recommendation engine
├── requirements.txt            # Minimal dependencies (Flask, scikit-learn, numpy, pandas)
├── README.md                   # Project documentation
├── sample_data/
│   ├── catalogue.json          # 6 curated benchmark films
│   └── interactions.json       # Verified viewer ratings
└── templates/
    └── dashboard.html          # Server-rendered Flask template
```

---

## Author

Developed by **Keshav Chaudhary** ([@keshav-x](https://github.com/keshav-x)).
