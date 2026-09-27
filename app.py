"""
BingeBot: Hybrid Content Recommendation Engine
Flask application that generates movie recommendations using collaborative filtering,
content-based genre similarity, and contextual mood matching.
"""

import json
import os
from collections import defaultdict

import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request
from sklearn.metrics.pairwise import cosine_similarity

# setup flask app and static folder
app = Flask(__name__, static_folder="static", static_url_path="/static", template_folder=".")

DATA_DIR = os.path.join(os.path.dirname(__file__), "sample_data")


# load movie catalogue from json file
def load_catalogue() -> dict[str, dict]:
    with open(os.path.join(DATA_DIR, "catalogue.json"), "r", encoding="utf-8") as f:
        items = json.load(f)
    return {item["id"]: item for item in items}


# load user interaction ratings history
def load_interactions() -> list[dict]:
    with open(os.path.join(DATA_DIR, "interactions.json"), "r", encoding="utf-8") as f:
        return json.load(f)


_CATALOGUE = load_catalogue()
_INTERACTIONS = load_interactions()


# build user-item matrix of ratings
def build_user_item_matrix(interactions: list[dict]) -> pd.DataFrame:
    records = []
    for item in interactions:
        records.append({
            "user_id": item["user_id"],
            "title_id": item["title_id"],
            "rating": float(item["rating"]),
        })
    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame()
    return df.pivot_table(index="user_id", columns="title_id", values="rating").fillna(0.0)


# calculate user similarity using cosine distance
def compute_user_similarity(pivot_df: pd.DataFrame) -> pd.DataFrame:
    if pivot_df.empty:
        return pd.DataFrame()
    sim_matrix = cosine_similarity(pivot_df.values)
    return pd.DataFrame(sim_matrix, index=pivot_df.index, columns=pivot_df.index)


# collaborative filtering: score movie based on similar viewers
def collaborative_score(user_id: str, title_id: str,
                        pivot_df: pd.DataFrame,
                        sim_df: pd.DataFrame) -> float:
    if pivot_df.empty or user_id not in pivot_df.index:
        return 0.0

    if title_id not in pivot_df.columns:
        return 0.0

    ratings = pivot_df[title_id]
    user_sims = sim_df.loc[user_id]

    # only consider other users who rated this movie
    rated_mask = ratings > 0
    other_mask = rated_mask & (ratings.index != user_id)

    if not other_mask.any():
        return 0.0

    weights = user_sims[other_mask]
    weight_sum = weights.abs().sum()

    if weight_sum == 0.0:
        return float(ratings[other_mask].mean())

    predicted = float(np.dot(weights, ratings[other_mask]) / weight_sum)
    return round(float(np.clip(predicted, 1.0, 5.0)), 2)


# content similarity based on genres of previously liked movies
def content_score(user_id: str, title_id: str,
                  catalogue: dict[str, dict],
                  interactions: list[dict]) -> float:
    candidate = catalogue.get(title_id)
    if not candidate:
        return 0.0

    candidate_genres = set(g.lower() for g in candidate.get("genre", []))

    # find titles this user rated 4 stars or higher
    liked_ids = [
        item["title_id"] for item in interactions
        if item["user_id"] == user_id and float(item["rating"]) >= 4.0
    ]

    if not liked_ids:
        # fallback to average catalogue rating scaled to 5
        return round(float(candidate.get("rating", 3.0)), 2)

    liked_genres = set()
    for tid in liked_ids:
        liked_item = catalogue.get(tid)
        if liked_item:
            for g in liked_item.get("genre", []):
                liked_genres.add(g.lower())

    if not liked_genres:
        return round(float(candidate.get("rating", 3.0)), 2)

    # compute jaccard genre overlap
    overlap = len(candidate_genres & liked_genres)
    total = len(candidate_genres | liked_genres)
    jaccard = overlap / total if total > 0 else 0.0

    return round(float(1.0 + jaccard * 4.0), 2)


# mood match boost logic
def mood_score(mood: str, title_id: str, catalogue: dict[str, dict]) -> float:
    if not mood:
        return 0.0
    item = catalogue.get(title_id)
    if not item:
        return 0.0
    title_moods = [m.lower() for m in item.get("mood", [])]
    return 1.0 if mood.lower() in title_moods else 0.0


# cold start fallback for brand new users
def cold_start_recommendations(mood: str, catalogue: dict[str, dict],
                               top_n: int = 4) -> list[dict]:
    scored = []
    for tid, item in catalogue.items():
        base_rating = float(item.get("rating", 3.0))
        m_boost = mood_score(mood, tid, catalogue) * 0.5
        final_score = round(min(5.0, base_rating + m_boost), 2)
        match_pct = round((final_score / 5.0) * 100)

        explanation = f"Popular title (rating {base_rating}/5.0)"
        if m_boost > 0:
            explanation += f", matches your selected mood: {mood}"

        scored.append({
            "title_id": tid,
            "title": item.get("title", tid),
            "year": item.get("year", 2020),
            "genre": item.get("genre", []),
            "catalogue_rating": base_rating,
            "hybrid_score": final_score,
            "match_pct": match_pct,
            "scores": {
                "collaborative": 0.0,
                "content": base_rating,
                "mood_boost": round(m_boost, 2),
            },
            "explanation": explanation,
            "poster": item.get("poster", ""),
        })

    scored.sort(key=lambda x: x["hybrid_score"], reverse=True)
    return scored[:top_n]


# hybrid recommendation calculation combining collaborative, content, and mood
def hybrid_recommend(user_id: str, mood: str = "", genre: str = "",
                     top_n: int = 4) -> list[dict]:
    catalogue = _CATALOGUE
    interactions = _INTERACTIONS

    user_has_history = any(i["user_id"] == user_id for i in interactions)

    # new user with no ratings gets cold start suggestions
    if not user_has_history:
        return cold_start_recommendations(mood, catalogue, top_n)

    pivot_df = build_user_item_matrix(interactions)
    sim_df = compute_user_similarity(pivot_df)

    # find titles the user has already watched
    watched_ids = set(
        i["title_id"] for i in interactions if i["user_id"] == user_id
    )

    scored = []
    for tid, item in catalogue.items():
        if tid in watched_ids:
            continue

        # filter by preferred genre if provided
        if genre:
            item_genres = [g.lower() for g in item.get("genre", [])]
            if genre.lower() not in item_genres:
                continue

        collab = collaborative_score(user_id, tid, pivot_df, sim_df)
        content = content_score(user_id, tid, catalogue, interactions)
        m_boost = mood_score(mood, tid, catalogue)

        # weighted hybrid formula: 50% collaborative + 30% content + 20% mood
        if collab > 0.0:
            raw_score = (0.50 * collab) + (0.30 * content) + (0.20 * m_boost * 5.0)
        else:
            raw_score = (0.60 * content) + (0.20 * float(item.get("rating", 3.0))) + (0.20 * m_boost * 5.0)

        final_score = round(float(np.clip(raw_score, 1.0, 5.0)), 2)
        match_pct = round((final_score / 5.0) * 100)

        # build clear explanation for recommendation
        reasons = []
        if collab >= 3.8:
            reasons.append("similar viewers loved this")
        if content >= 3.5:
            reasons.append("matches genres you watch")
        if m_boost > 0:
            reasons.append(f"fits your {mood} mood")
        if not reasons:
            reasons.append(f"rated {item.get('rating', 4.0)}/5 in catalogue")

        explanation = ", ".join(reasons).capitalize() + "."

        scored.append({
            "title_id": tid,
            "title": item.get("title", tid),
            "year": item.get("year", 2020),
            "genre": item.get("genre", []),
            "catalogue_rating": float(item.get("rating", 3.0)),
            "hybrid_score": final_score,
            "match_pct": match_pct,
            "scores": {
                "collaborative": round(collab, 2),
                "content": round(content, 2),
                "mood_boost": round(m_boost * 1.0, 2),
            },
            "explanation": explanation,
            "poster": item.get("poster", ""),
        })

    scored.sort(key=lambda x: x["hybrid_score"], reverse=True)
    return scored[:top_n]


# web dashboard route
@app.route("/")
def index():
    return render_template("index.html")


# api endpoint: get hybrid recommendations
@app.route("/api/recommend", methods=["POST"])
def api_recommend():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "U001")
    mood = data.get("mood", "")
    genre = data.get("genre", "")
    top_n = int(data.get("top_n", 4))

    is_cold_start = not any(i["user_id"] == user_id for i in _INTERACTIONS)
    results = hybrid_recommend(user_id=user_id, mood=mood, genre=genre, top_n=top_n)

    return jsonify({
        "user_id": user_id,
        "is_cold_start": is_cold_start,
        "total_results": len(results),
        "recommendations": results,
    }), 200


# api endpoint: get catalogue titles
@app.route("/api/catalogue", methods=["GET"])
def api_catalogue():
    return jsonify(list(_CATALOGUE.values())), 200


# api endpoint: get user personas list
@app.route("/api/users", methods=["GET"])
def api_users():
    user_counts: dict[str, int] = defaultdict(int)
    for item in _INTERACTIONS:
        user_counts[item["user_id"]] += 1

    users = [{"user_id": uid, "rating_count": count}
             for uid, count in sorted(user_counts.items())]
    users.append({"user_id": "NEW_USER", "rating_count": 0})
    return jsonify(users), 200


# start local development server
if __name__ == "__main__":
    print(f"BingeBot loaded: {len(_CATALOGUE)} titles, {len(set(i['user_id'] for i in _INTERACTIONS))} users, {len(_INTERACTIONS)} interactions")
    print("Starting at http://127.0.0.1:5001")
    app.run(debug=True, host="127.0.0.1", port=5001)
