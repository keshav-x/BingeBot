"""
Core Recommendation Engine for BingeBot.
Provides modular components for collaborative filtering,
content-based genre similarity, and contextual mood matching.
"""

from collections import defaultdict
import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity


class CollaborativeEngine:
    """Calculates viewer-to-viewer similarity and predicts ratings."""

    @staticmethod
    def build_matrix(interactions: list[dict]) -> pd.DataFrame:
        # build user rating pivot matrix from interaction history
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
        # pivot into user-item interaction table
        return df.pivot_table(index="user_id", columns="title_id", values="rating").fillna(0.0)

    @staticmethod
    def compute_similarity(pivot_df: pd.DataFrame) -> pd.DataFrame:
        # calculate cosine similarity matrix across user rating vectors
        if pivot_df.empty:
            return pd.DataFrame()
        sim_matrix = cosine_similarity(pivot_df.values)
        return pd.DataFrame(sim_matrix, index=pivot_df.index, columns=pivot_df.index)

    @classmethod
    def score(cls, user_id: str, title_id: str, pivot_df: pd.DataFrame, sim_df: pd.DataFrame) -> float:
        # added collaborative filtering logic: score movie based on similar viewers
        if pivot_df.empty or user_id not in pivot_df.index or title_id not in pivot_df.columns:
            return 0.0

        ratings = pivot_df[title_id]
        user_sims = sim_df.loc[user_id]
        rated_mask = ratings > 0
        other_mask = rated_mask & (ratings.index != user_id)

        if not other_mask.any():
            return 0.0

        # compute weighted average of ratings given by peers
        weights = user_sims[other_mask]
        weight_sum = weights.abs().sum()

        if weight_sum == 0.0:
            return float(ratings[other_mask].mean())

        predicted = float(np.dot(weights, ratings[other_mask]) / weight_sum)
        # clamp rating within valid 1.0 to 5.0 range
        return round(float(np.clip(predicted, 1.0, 5.0)), 2)


class ContentEngine:
    """Computes genre similarity between candidate titles and user history."""

    @staticmethod
    def score(user_id: str, title_id: str, catalogue: dict[str, dict], interactions: list[dict]) -> float:
        # added content trait similarity matching based on user watch history
        candidate = catalogue.get(title_id)
        if not candidate:
            return 0.0

        candidate_genres = set(g.lower() for g in candidate.get("genre", []))
        # collect titles the viewer previously rated 4.0 or above
        liked_ids = [
            item["title_id"] for item in interactions
            if item["user_id"] == user_id and float(item["rating"]) >= 4.0
        ]

        if not liked_ids:
            return round(float(candidate.get("rating", 3.0)), 2)

        liked_genres = set()
        for tid in liked_ids:
            liked_item = catalogue.get(tid)
            if liked_item:
                for g in liked_item.get("genre", []):
                    liked_genres.add(g.lower())

        if not liked_genres:
            return round(float(candidate.get("rating", 3.0)), 2)

        # calculate jaccard overlap between movie genres and liked genres
        overlap = len(candidate_genres & liked_genres)
        total = len(candidate_genres | liked_genres)
        jaccard = overlap / total if total > 0 else 0.0
        # scale similarity to 1.0 to 5.0 rating range
        return round(float(1.0 + jaccard * 4.0), 2)


class MoodMatcher:
    """Matches contextual mood tags to title attributes."""

    @staticmethod
    def score(mood: str, title_id: str, catalogue: dict[str, dict]) -> float:
        # added mood tone boost logic
        if not mood:
            return 0.0
        item = catalogue.get(title_id)
        if not item:
            return 0.0
        title_moods = [m.lower() for m in item.get("mood", [])]
        # return full boost if requested mood matches title tags
        return 1.0 if mood.lower() in title_moods else 0.0


class HybridRecommender:
    """Coordinates collaborative, content, and mood signals."""

    def __init__(self, catalogue: dict[str, dict], interactions: list[dict]):
        self.catalogue = catalogue
        self.interactions = interactions
        # pre-build interaction matrix and viewer similarity cache
        self.pivot_df = CollaborativeEngine.build_matrix(interactions)
        self.sim_df = CollaborativeEngine.compute_similarity(self.pivot_df)

    def cold_start(self, mood: str, top_n: int = 4) -> list[dict]:
        # added cold start fallback for brand-new users with zero viewing history
        scored = []
        for tid, item in self.catalogue.items():
            base_rating = float(item.get("rating", 3.0))
            # add mood boost to catalogue rating
            m_boost = MoodMatcher.score(mood, tid, self.catalogue) * 0.5
            final_score = round(min(5.0, base_rating + m_boost), 2)
            match_pct = round((final_score / 5.0) * 100)

            # human readable explanation for cold start
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
                "scores": {"collaborative": 0.0, "content": base_rating, "mood_boost": round(m_boost, 2)},
                "explanation": explanation,
                "poster": item.get("poster", ""),
            })

        # sort descending by final score
        scored.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return scored[:top_n]

    def recommend(self, user_id: str, mood: str = "", genre: str = "", top_n: int = 4) -> list[dict]:
        # added hybrid recommendation pipeline combining 3 signals
        user_has_history = any(i["user_id"] == user_id for i in self.interactions)
        if not user_has_history:
            return self.cold_start(mood, top_n)

        # skip titles already watched by the user
        watched_ids = set(i["title_id"] for i in self.interactions if i["user_id"] == user_id)
        scored = []

        for tid, item in self.catalogue.items():
            if tid in watched_ids:
                continue

            # apply optional genre filter
            if genre:
                item_genres = [g.lower() for g in item.get("genre", [])]
                if genre.lower() not in item_genres:
                    continue

            # calculate individual scores: collaborative, content, mood
            collab = CollaborativeEngine.score(user_id, tid, self.pivot_df, self.sim_df)
            content = ContentEngine.score(user_id, tid, self.catalogue, self.interactions)
            m_boost = MoodMatcher.score(mood, tid, self.catalogue)

            # added weighted hybrid formula: 50% collaborative + 30% content + 20% mood
            if collab > 0.0:
                raw_score = (0.50 * collab) + (0.30 * content) + (0.20 * m_boost * 5.0)
            else:
                raw_score = (0.60 * content) + (0.20 * float(item.get("rating", 3.0))) + (0.20 * m_boost * 5.0)

            # clamp final score between 1.0 and 5.0
            final_score = round(float(np.clip(raw_score, 1.0, 5.0)), 2)
            match_pct = round((final_score / 5.0) * 100)

            # generate natural, clean explanation text
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
                "scores": {"collaborative": round(collab, 2), "content": round(content, 2), "mood_boost": round(m_boost * 1.0, 2)},
                "explanation": explanation,
                "poster": item.get("poster", ""),
            })

        # sort titles by hybrid score descending
        scored.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return scored[:top_n]
