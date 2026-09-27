"""
BingeBot — OTT Content Discovery Engine
=========================================
A local Flask API that provides hybrid content recommendations by combining
collaborative filtering with content-based signals and mood/sentiment matching.

Technical approach
------------------
1. **Collaborative filtering**: Builds a user-item rating matrix from the
   sample interaction data. Computes user-user cosine similarity using
   scikit-learn. For a given user, predicts ratings for unseen titles based on
   the weighted average of similar users' ratings.

2. **Content-based signals**: Computes similarity between titles using genre,
   mood tags, and sentiment tone. Titles that share genres and mood attributes
   with a user's highly-rated titles score higher.

3. **Mood/sentiment matching**: Each catalogue title has a sentiment_tone and
   mood_tags field. When a user specifies a current mood, titles matching that
   mood are boosted in the ranking.

4. **Hybrid ranking**: The final score is a weighted combination of the
   collaborative score and content score. Weights are configurable.

5. **Cold-start fallback**: For unknown users (no interaction history), the
   system returns top-rated titles filtered by any mood/genre preferences,
   with a clear indication that this is a popularity-based fallback.

6. **Explanations**: Each recommendation includes a plain-text explanation
   grounded in the actual ranking signals (not an LLM).

Limitations
-----------
* The sample catalogue has 12 titles and 5 users — this is a demonstration.
* Collaborative filtering quality depends on having sufficient overlapping
  ratings. With 5 users, similarity estimates are rough.
* Content signals use exact keyword matching, not embeddings.
* No LLM is used. Explanations are template-based from ranking signals.
"""

import json
import os
from collections import defaultdict

import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request
from sklearn.metrics.pairwise import cosine_similarity

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__, static_folder="static", static_url_path="/static", template_folder=".")

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), "sample_data")


def load_catalogue() -> dict[str, dict]:
    """Load title catalogue keyed by title ID."""
    with open(os.path.join(DATA_DIR, "catalogue.json"), "r", encoding="utf-8") as f:
        items = json.load(f)
    return {item["id"]: item for item in items}


def load_interactions() -> list[dict]:
    """Load user-item interaction records."""
    with open(os.path.join(DATA_DIR, "interactions.json"), "r", encoding="utf-8") as f:
        return json.load(f)


CATALOGUE = load_catalogue()
INTERACTIONS = load_interactions()

# ---------------------------------------------------------------------------
# Recommendation engine
# ---------------------------------------------------------------------------

class RecommendationEngine:
    """Hybrid recommendation engine combining collaborative and content signals."""

    def __init__(self, catalogue: dict[str, dict], interactions: list[dict]):
        self.catalogue = catalogue
        self.interactions = interactions
        self.title_ids = sorted(catalogue.keys())
        self.title_idx = {tid: i for i, tid in enumerate(self.title_ids)}

        # Build user-item matrix
        self.users: set[str] = set()
        self.user_ratings: dict[str, dict[str, float]] = defaultdict(dict)
        for inter in interactions:
            uid = inter["user_id"]
            tid = inter["title_id"]
            self.users.add(uid)
            self.user_ratings[uid][tid] = inter["rating"]

        self.user_ids = sorted(self.users)
        self.user_idx = {uid: i for i, uid in enumerate(self.user_ids)}

        # Build rating matrix (users × titles)
        n_users = len(self.user_ids)
        n_titles = len(self.title_ids)
        self.rating_matrix = np.zeros((n_users, n_titles))
        for uid, ratings in self.user_ratings.items():
            for tid, rating in ratings.items():
                if uid in self.user_idx and tid in self.title_idx:
                    self.rating_matrix[self.user_idx[uid], self.title_idx[tid]] = rating

        # User-user similarity
        # Replace 0s with NaN for similarity calculation, then back to 0
        mask = self.rating_matrix > 0
        normed = self.rating_matrix.copy()
        # Mean-centre per user
        for i in range(n_users):
            rated = mask[i]
            if rated.any():
                mean = normed[i, rated].mean()
                normed[i, rated] -= mean
                normed[i, ~rated] = 0
        self.user_similarity = cosine_similarity(normed)

        # Content feature vectors for titles
        self._build_content_features()

    def _build_content_features(self):
        """Build simple content feature vectors from genre, mood, and tone."""
        # Collect all unique genre and mood values
        all_genres: set[str] = set()
        all_moods: set[str] = set()
        all_tones: set[str] = set()
        for t in self.catalogue.values():
            all_genres.update(t.get("genre", []))
            all_moods.update(t.get("mood_tags", []))
            all_tones.add(t.get("sentiment_tone", ""))

        self.genre_list = sorted(all_genres)
        self.mood_list = sorted(all_moods)
        self.tone_list = sorted(all_tones - {""})

        n_features = len(self.genre_list) + len(self.mood_list) + len(self.tone_list)
        self.content_vectors = np.zeros((len(self.title_ids), n_features))

        for tid, t in self.catalogue.items():
            idx = self.title_idx[tid]
            offset = 0
            for g in t.get("genre", []):
                if g in self.genre_list:
                    self.content_vectors[idx, self.genre_list.index(g)] = 1
            offset = len(self.genre_list)
            for m in t.get("mood_tags", []):
                if m in self.mood_list:
                    self.content_vectors[idx, offset + self.mood_list.index(m)] = 1
            offset += len(self.mood_list)
            tone = t.get("sentiment_tone", "")
            if tone in self.tone_list:
                self.content_vectors[idx, offset + self.tone_list.index(tone)] = 1

        self.content_similarity = cosine_similarity(self.content_vectors)

    def _collaborative_scores(self, user_id: str) -> dict[str, float]:
        """Predict ratings for unseen titles using user-user collaborative filtering."""
        if user_id not in self.user_idx:
            return {}

        u_idx = self.user_idx[user_id]
        seen = set(self.user_ratings[user_id].keys())
        predictions = {}

        for tid in self.title_ids:
            if tid in seen:
                continue
            t_idx = self.title_idx[tid]

            # Weighted average of other users' ratings
            numerator = 0.0
            denominator = 0.0
            for other_uid in self.user_ids:
                if other_uid == user_id:
                    continue
                o_idx = self.user_idx[other_uid]
                other_rating = self.rating_matrix[o_idx, t_idx]
                if other_rating == 0:
                    continue
                sim = self.user_similarity[u_idx, o_idx]
                if sim <= 0:
                    continue
                numerator += sim * other_rating
                denominator += sim

            if denominator > 0:
                predictions[tid] = numerator / denominator
            else:
                predictions[tid] = 0.0

        return predictions

    def _content_scores(self, user_id: str) -> dict[str, float]:
        """Score unseen titles by content similarity to the user's top-rated titles."""
        if user_id not in self.user_ratings or not self.user_ratings[user_id]:
            return {}

        seen = self.user_ratings[user_id]
        # Weight by rating: titles rated higher contribute more
        unseen_scores = {}

        for tid in self.title_ids:
            if tid in seen:
                continue
            t_idx = self.title_idx[tid]
            score = 0.0
            weight_sum = 0.0
            for rated_tid, rating in seen.items():
                if rated_tid not in self.title_idx:
                    continue
                r_idx = self.title_idx[rated_tid]
                sim = self.content_similarity[t_idx, r_idx]
                score += sim * rating
                weight_sum += rating
            if weight_sum > 0:
                unseen_scores[tid] = score / weight_sum * 5  # Scale to 0-5
            else:
                unseen_scores[tid] = 0.0

        return unseen_scores

    def _mood_boost(self, mood: str) -> dict[str, float]:
        """Return a boost score for titles matching the requested mood."""
        mood_lower = mood.lower().strip()
        boosts = {}
        for tid, t in self.catalogue.items():
            tags = [m.lower() for m in t.get("mood_tags", [])]
            tone = t.get("sentiment_tone", "").lower()
            if mood_lower in tags or mood_lower == tone:
                boosts[tid] = 1.0
            elif any(mood_lower in tag for tag in tags):
                boosts[tid] = 0.5
            else:
                boosts[tid] = 0.0
        return boosts

    def recommend(self, user_id: str, mood: str = "",
                  genre_filter: str = "", top_n: int = 5,
                  collab_weight: float = 0.5,
                  content_weight: float = 0.3,
                  mood_weight: float = 0.2) -> list[dict]:
        """Generate hybrid recommendations with explanations.

        For known users: combines collaborative + content + mood signals.
        For unknown users: returns popularity-based fallback.
        """
        is_cold_start = user_id not in self.user_idx

        if is_cold_start:
            return self._cold_start_recommend(mood, genre_filter, top_n)

        # Get component scores
        collab = self._collaborative_scores(user_id)
        content = self._content_scores(user_id)
        mood_boosts = self._mood_boost(mood) if mood else {}

        seen = set(self.user_ratings[user_id].keys())
        candidates = [tid for tid in self.title_ids if tid not in seen]

        # Apply genre filter
        if genre_filter:
            gf = genre_filter.lower()
            candidates = [
                tid for tid in candidates
                if any(gf == g.lower() for g in self.catalogue[tid].get("genre", []))
            ]

        # Compute hybrid scores
        scored = []
        for tid in candidates:
            c_score = collab.get(tid, 0.0)
            ct_score = content.get(tid, 0.0)
            m_score = mood_boosts.get(tid, 0.0)

            hybrid = (collab_weight * c_score +
                      content_weight * ct_score +
                      mood_weight * m_score * 5)  # Scale mood to match

            # Build explanation
            explanation_parts = []
            if c_score > 0:
                explanation_parts.append(
                    f"Users with similar taste rated this {c_score:.1f}/5"
                )
            if ct_score > 0:
                explanation_parts.append(
                    f"shares genre/mood traits with your top-rated titles (content score: {ct_score:.1f})"
                )
            if m_score > 0 and mood:
                explanation_parts.append(
                    f"matches your '{mood}' mood preference"
                )

            title_info = self.catalogue[tid]
            scored.append({
                "title_id": tid,
                "title": title_info["title"],
                "genre": title_info.get("genre", []),
                "type": title_info.get("type", ""),
                "year": title_info.get("year", ""),
                "description": title_info.get("description", ""),
                "mood_tags": title_info.get("mood_tags", []),
                "sentiment_tone": title_info.get("sentiment_tone", ""),
                "catalogue_rating": title_info.get("rating", 0),
                "hybrid_score": round(hybrid, 3),
                "scores": {
                    "collaborative": round(c_score, 3),
                    "content": round(ct_score, 3),
                    "mood_boost": round(m_score, 3),
                },
                "explanation": "; ".join(explanation_parts) if explanation_parts else "Recommended based on available signals.",
                "recommendation_method": "hybrid (collaborative + content + mood)",
            })

        scored.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return scored[:top_n]

    def _cold_start_recommend(self, mood: str, genre_filter: str,
                              top_n: int) -> list[dict]:
        """Fallback for unknown users: popularity-based with mood/genre filter."""
        candidates = list(self.catalogue.values())

        if genre_filter:
            gf = genre_filter.lower()
            candidates = [
                t for t in candidates
                if any(gf == g.lower() for g in t.get("genre", []))
            ]

        if mood:
            mood_lower = mood.lower()
            # Boost mood-matching titles
            for t in candidates:
                tags = [m.lower() for m in t.get("mood_tags", [])]
                t["_mood_match"] = 1 if mood_lower in tags or mood_lower == t.get("sentiment_tone", "").lower() else 0
            candidates.sort(key=lambda t: (t.get("_mood_match", 0), t.get("rating", 0)), reverse=True)
        else:
            candidates.sort(key=lambda t: t.get("rating", 0), reverse=True)

        results = []
        for t in candidates[:top_n]:
            explanation = "Recommended based on popularity (top-rated in catalogue)"
            if mood and t.get("_mood_match"):
                explanation += f"; matches your '{mood}' mood preference"

            results.append({
                "title_id": t["id"],
                "title": t["title"],
                "genre": t.get("genre", []),
                "type": t.get("type", ""),
                "year": t.get("year", ""),
                "description": t.get("description", ""),
                "mood_tags": t.get("mood_tags", []),
                "sentiment_tone": t.get("sentiment_tone", ""),
                "catalogue_rating": t.get("rating", 0),
                "hybrid_score": t.get("rating", 0),
                "scores": {
                    "collaborative": 0,
                    "content": 0,
                    "mood_boost": t.get("_mood_match", 0),
                },
                "explanation": explanation,
                "recommendation_method": "cold-start fallback (popularity-based)",
            })

        # Clean up temp field
        for t in self.catalogue.values():
            t.pop("_mood_match", None)

        return results


# Initialize engine
engine = RecommendationEngine(CATALOGUE, INTERACTIONS)

# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Web dashboard for presentation, or JSON API info if requested."""
    if request.args.get("format") == "json" or (
        request.accept_mimetypes.best == "application/json"
        and not request.accept_mimetypes.accept_html
    ):
        return jsonify({
            "name": "BingeBot — OTT Content Discovery Engine",
            "version": "1.0.0",
            "endpoints": {
                "GET /": "Web dashboard (or JSON if format=json)",
                "GET /api/health": "Health check",
                "GET /api/catalogue": "List all titles",
                "GET /api/catalogue/<title_id>": "Get a specific title",
                "GET /api/users": "List known users",
                "POST /api/recommend": "Get recommendations",
            },
            "sample_request": {
                "url": "POST /api/recommend",
                "body": {
                    "user_id": "U001",
                    "mood": "tense",
                    "genre": "",
                    "top_n": 5,
                },
            },
        })
    return render_template("index.html")


@app.route("/api/health")
def health():
    """Health check."""
    return jsonify({
        "status": "ok",
        "catalogue_size": len(CATALOGUE),
        "known_users": len(engine.user_ids),
        "total_interactions": len(INTERACTIONS),
    })


@app.route("/api/catalogue")
def list_catalogue():
    """List all titles in the catalogue."""
    genre_filter = request.args.get("genre", "").lower()
    tone_filter = request.args.get("tone", "").lower()

    titles = list(CATALOGUE.values())
    if genre_filter:
        titles = [t for t in titles if any(genre_filter == g.lower() for g in t.get("genre", []))]
    if tone_filter:
        titles = [t for t in titles if t.get("sentiment_tone", "").lower() == tone_filter]

    return jsonify({"titles": titles, "count": len(titles)})


@app.route("/api/catalogue/<title_id>")
def get_title(title_id):
    """Get details for a specific title."""
    title = CATALOGUE.get(title_id)
    if not title:
        return jsonify({"error": f"Title '{title_id}' not found."}), 404
    return jsonify(title)


@app.route("/api/users")
def list_users():
    """List known users and their watch history."""
    users = {}
    for uid in engine.user_ids:
        ratings = engine.user_ratings[uid]
        watched = []
        for tid, rating in ratings.items():
            t = CATALOGUE.get(tid, {})
            watched.append({
                "title_id": tid,
                "title": t.get("title", "Unknown"),
                "rating": rating,
            })
        users[uid] = {"watched": watched, "count": len(watched)}
    return jsonify({"users": users})


@app.route("/api/recommend", methods=["POST"])
def recommend():
    """Get personalised recommendations.

    Request body (JSON):
        {
            "user_id": "U001",           # Required. Use unknown ID for cold-start.
            "mood": "tense",             # Optional. Current mood preference.
            "genre": "Sci-Fi",           # Optional. Genre filter.
            "top_n": 5,                  # Optional. Number of results (default 5).
            "collab_weight": 0.5,        # Optional. Weight for collaborative signal.
            "content_weight": 0.3,       # Optional. Weight for content signal.
            "mood_weight": 0.2           # Optional. Weight for mood signal.
        }
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be valid JSON."}), 400

    user_id = data.get("user_id", "").strip()
    if not user_id:
        return jsonify({"error": "'user_id' is required. Use any string for cold-start."}), 400

    mood = data.get("mood", "")
    genre = data.get("genre", "")
    top_n = min(data.get("top_n", 5), len(CATALOGUE))
    collab_weight = data.get("collab_weight", 0.5)
    content_weight = data.get("content_weight", 0.3)
    mood_weight = data.get("mood_weight", 0.2)

    # Validate weights
    if not all(isinstance(w, (int, float)) and w >= 0 for w in [collab_weight, content_weight, mood_weight]):
        return jsonify({"error": "Weights must be non-negative numbers."}), 400

    results = engine.recommend(
        user_id=user_id,
        mood=mood,
        genre_filter=genre,
        top_n=top_n,
        collab_weight=collab_weight,
        content_weight=content_weight,
        mood_weight=mood_weight,
    )

    is_cold = user_id not in engine.user_idx
    return jsonify({
        "user_id": user_id,
        "is_cold_start": is_cold,
        "mood_requested": mood,
        "genre_filter": genre,
        "recommendation_count": len(results),
        "recommendations": results,
        "note": (
            "This user has no interaction history. Recommendations are based on "
            "catalogue popularity and any mood/genre preferences provided."
            if is_cold
            else f"Hybrid recommendations for {user_id} using collaborative filtering, "
                 "content similarity, and mood signals."
        ),
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"BingeBot loaded: {len(CATALOGUE)} titles, {len(engine.user_ids)} users, {len(INTERACTIONS)} interactions")
    print("Starting at http://127.0.0.1:5001")
    app.run(debug=True, port=5001)
