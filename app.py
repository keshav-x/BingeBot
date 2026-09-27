"""
BingeBot: Hybrid Content Recommendation Engine
Flask application that generates movie recommendations using collaborative filtering,
content-based genre similarity, and contextual mood matching.
"""

import json
import os
from collections import defaultdict

from flask import Flask, jsonify, render_template, request
from recommender import HybridRecommender

# setup flask app and static folder
app = Flask(__name__, static_folder="static", static_url_path="/static", template_folder=".")

DATA_DIR = os.path.join(os.path.dirname(__file__), "sample_data")


def load_catalogue() -> dict[str, dict]:
    with open(os.path.join(DATA_DIR, "catalogue.json"), "r", encoding="utf-8") as f:
        items = json.load(f)
    return {item["id"]: item for item in items}


def load_interactions() -> list[dict]:
    with open(os.path.join(DATA_DIR, "interactions.json"), "r", encoding="utf-8") as f:
        return json.load(f)


_CATALOGUE = load_catalogue()
_INTERACTIONS = load_interactions()
_ENGINE = HybridRecommender(_CATALOGUE, _INTERACTIONS)


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
    results = _ENGINE.recommend(user_id=user_id, mood=mood, genre=genre, top_n=top_n)

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

    users = [{"user_id": uid, "rating_count": count} for uid, count in sorted(user_counts.items())]
    users.append({"user_id": "NEW_USER", "rating_count": 0})
    return jsonify(users), 200


# start local development server
if __name__ == "__main__":
    print(f"BingeBot loaded: {len(_CATALOGUE)} titles, {len(set(i['user_id'] for i in _INTERACTIONS))} users, {len(_INTERACTIONS)} interactions")
    print("Starting at http://127.0.0.1:5001")
    app.run(debug=True, host="127.0.0.1", port=5001)
