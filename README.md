# BingeBot: Hybrid OTT Content Recommendation Engine

An explainable, multi-signal recommendation engine and interactive web console combining Collaborative Filtering (user taste similarity), Content-Based Filtering (genre and thematic trait vectors), and Mood Tone matching for OTT streaming discovery.

Developed as a Summer Industrial Training project in **Python & Artificial Intelligence** at **Grziti Interactive** (5 June - 19 July 2026), affiliated with **Rayat Bahra Institute of Engineering & Nanotechnology, Hoshiarpur**.

---

## 1. Project Overview & Core Purpose

Modern streaming media platforms face two fundamental challenges:
1. **The Cold-Start Dilemma**: New viewers have zero watch history, causing collaborative filtering algorithms to break down or return unranked noise.
2. **Recommendation Opacity**: Black-box recommendation systems provide no justification for their suggestions, eroding user trust.

**BingeBot** addresses these issues with a transparent **tri-hybrid recommendation pipeline**. It mathematically fuses:
- What people like you enjoyed (**Collaborative Filtering, 50%**)
- Titles sharing visual, structural, and genre traits (**Content-Based Filtering, 30%**)
- What tone you are in the mood for tonight (**Mood Context Boost, 20%**)

When a new visitor with zero viewing history arrives, the engine seamlessly activates an automatic **Cold-Start Popularity Fallback**, ensuring an instant, high-quality viewing list.

---

## 2. Zero-Subscription Architecture (100% Free & Self-Contained)

> **Important**: BingeBot does NOT require any external paid APIs (no OpenAI, no Anthropic, no HuggingFace Inference API) and does NOT require cloud vector databases (no Pinecone, no Weaviate, no Milvus).

### How BingeBot Handles Everything Locally
- **Local Linear Algebra**: Uses `scikit-learn`'s `cosine_similarity` and `NumPy` matrices running directly in RAM on standard CPU hardware.
- **Local Feature Vectors**: Titles are encoded into binary feature vectors across genres, directors, and mood tags without external embedding APIs.
- **Deterministic Attribution**: Explanations are derived mathematically from the exact weights that produced the recommendation (e.g. *"Viewers with similar taste rated this 4.8 / 5.0"*), rather than hallucinated by an LLM.
- **Local Flask Server**: Runs self-contained on `http://127.0.0.1:5001`.
- **Operational Cost**: **$0.00**. Completely functional offline without an internet connection.

---

## 3. Recommendation Mathematics & Scoring Formulation

### Hybrid Score Formulation
For a given viewer $u$ and candidate catalogue title $i$, the engine predicts an affinity rating on a **0.0 to 5.0 star scale**:

$$\text{Score}(u, i) = (W_{\text{collab}} \times S_{\text{collab}}) + (W_{\text{content}} \times S_{\text{content}}) + (W_{\text{mood}} \times S_{\text{mood}} \times 5.0)$$

### Configured Signal Weights
| Signal | Weight | Method | Purpose |
|---|---|---|---|
| **Collaborative Filtering** | **50%** ($W = 0.50$) | User-Item Cosine Similarity | Predicts rating from peer viewers who share consumption patterns |
| **Content Trait Similarity** | **30%** ($W = 0.30$) | Binary Feature Vector Cosine Similarity | Evaluates similarity with titles the user previously rated 5/5 |
| **Mood Tone Context** | **20%** ($W = 0.20$) | Categorical Attribute Match | Boosts titles matching the viewer's current emotional request |

### Normalisation & Display Range
- **Predicted Rating**: Clamped between `1.0` and `5.0` stars.
- **Match Score**: Normalized to a clean `0%` to `100%` scale via:
  $$\text{Match Percentage} = \min\left(100, \max\left(0, \text{round}\left(\frac{\text{Score}}{5.0} \times 100\right)\right)\right)$$
  *(Eliminates distorted percentage metrics above 100%).*

---

## 4. Cold-Start Handling Strategy

When `user_id` is unrecognized or has zero ratings in `interactions.json`:
1. The engine intercepts the request before collaborative matrix computation.
2. It transitions into **Cold-Start Popularity Mode**.
3. Titles are ranked by their catalogue baseline rating, boosted by requested mood or genre filters.
4. The web dashboard displays a clear tag: `Cold Start Fallback (Top Popular Titles + Mood Match)`.

---

## 5. Quick Start: Local Installation & Execution

### Prerequisites
- Python 3.10, 3.11, 3.12, or 3.14 installed.
- Git installed.

### Setup Instructions

```bash
# 1. Navigate to the project directory
cd A:\projects\internship\BingeBot

# 2. (Optional) Create and activate a virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the recommendation server
python app.py
```

Open your browser to: **`http://127.0.0.1:5001`**

---

## 6. Curated Catalogue & Examiner 1-Click Demo Scenarios

The sample catalogue is intentionally curated with **6 universally recognized films** and **3 distinct viewer personas** to ensure demonstration clarity:

### Curated Catalogue
1. **Inception (2010)**: Sci-Fi, Thriller &bull; Tone: Cerebral &bull; Rating: 4.8 / 5.0
2. **The Dark Knight (2008)**: Crime, Action &bull; Tone: Dark & Gritty &bull; Rating: 4.9 / 5.0
3. **Interstellar (2014)**: Sci-Fi, Drama &bull; Tone: Reflective &bull; Rating: 4.8 / 5.0
4. **The Shawshank Redemption (1994)**: Drama &bull; Tone: Inspiring &bull; Rating: 4.9 / 5.0
5. **Spirited Away (2001)**: Animation, Fantasy &bull; Tone: Inspiring &bull; Rating: 4.7 / 5.0
6. **Knives Out (2019)**: Comedy, Mystery &bull; Tone: Fun & Witty &bull; Rating: 4.5 / 5.0

### 1-Click Examiner Demo Scenarios

| Scenario | Button | Target Profile | Expected Recommendation | Attribution Reasoning |
|---|---|---|---|---|
| **Scenario 1** | `[Test 1: Sci-Fi Enthusiast]` | User 1 (Rated Inception, Interstellar) | **Inception** (96% Match, 4.8 / 5.0) | Peer rating 4.8/5.0 + Sci-Fi genre trait match + Cerebral mood boost |
| **Scenario 2** | `[Test 2: Crime Fan]` | User 2 (Rated Dark Knight, Knives Out) | **The Dark Knight** (98% Match, 4.9 / 5.0) | Crime enthusiast peer marks + Dark/Gritty tone match |
| **Scenario 3** | `[Test 3: First-Time User]` | New User (Cold Start) | **The Shawshank Redemption** (98% Match, 4.9 / 5.0) | Popularity fallback active; top catalogue title matching inspiring tone |

---

## 7. REST API Specification

### 1. Compute Recommendations
- **Endpoint**: `POST /api/recommend`
- **Headers**: `Content-Type: application/json`

**Sample Request**:
```bash
curl -X POST http://127.0.0.1:5001/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id": "U001", "mood": "cerebral", "top_n": 3}'
```

**Sample Response**:
```json
{
  "user_id": "U001",
  "is_cold_start": false,
  "recommendations": [
    {
      "title_id": "T001",
      "title": "Inception",
      "year": 2010,
      "genre": ["Sci-Fi", "Thriller"],
      "catalogue_rating": 4.8,
      "hybrid_score": 4.80,
      "scores": {
        "collaborative": 4.8,
        "content": 4.2,
        "mood_boost": 0.2
      },
      "explanation": "Users with similar taste rated this highly; shares genre traits with your top-rated titles; matches your requested cerebral mood."
    }
  ]
}
```

### 2. Catalogue & User Endpoints
- **GET /api/catalogue**: List all 6 catalogue titles with metadata.
- **GET /api/users**: View interaction history and ratings across user profiles.

---

## 8. Project Structure

```
BingeBot/
├── app.py                      # Recommendation engine, similarity matrices, Flask routes
├── requirements.txt            # Minimal dependencies (Flask, scikit-learn, numpy, pandas)
├── README.md                   # Complete architectural documentation
├── sample_data/
│   ├── catalogue.json          # 6 curated benchmark films
│   └── interactions.json       # 9 verified rating interactions
└── templates/
    └── dashboard.html          # Prismatic Polygons console with examiner presets
```
