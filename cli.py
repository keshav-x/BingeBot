"""
Command-Line Interface (CLI) for BingeBot.
Allows running movie recommendations directly from terminal.
"""

import argparse
import json
import os
import sys
from recommender import HybridRecommender

DATA_DIR = os.path.join(os.path.dirname(__file__), "sample_data")


def load_data():
    # load catalogue and interaction datasets
    with open(os.path.join(DATA_DIR, "catalogue.json"), "r", encoding="utf-8") as f:
        items = json.load(f)
    catalogue = {item["id"]: item for item in items}

    with open(os.path.join(DATA_DIR, "interactions.json"), "r", encoding="utf-8") as f:
        interactions = json.load(f)

    return catalogue, interactions


def main():
    # parse command line arguments
    parser = argparse.ArgumentParser(description="BingeBot: OTT Movie Recommendations Engine.")
    parser.add_argument("--user", default="U001", help="Viewer User ID (e.g. U001, U002, NEW_USER).")
    parser.add_argument("--mood", default="", help="Current mood (e.g. cerebral, adrenaline, dark, uplifting).")
    parser.add_argument("--genre", default="", help="Preferred genre filter (e.g. Sci-Fi, Crime, Drama).")
    parser.add_argument("--top", type=int, default=3, help="Number of recommendations to return.")
    parser.add_argument("--catalogue", action="store_true", help="Display all catalogue titles.")
    args = parser.parse_args()

    catalogue, interactions = load_data()

    # display movie catalogue if requested
    if args.catalogue:
        print("\n=== BingeBot Movie Catalogue ===")
        for tid, m in catalogue.items():
            print(f"- {m['title']} ({m['year']}) | Genres: {', '.join(m['genre'])} | Moods: {', '.join(m['mood'])} | Rating: {m['rating']}/5.0")
        print()
        return

    # initialize recommender and execute query
    rec = HybridRecommender(catalogue, interactions)
    results = rec.recommend(user_id=args.user, mood=args.mood, genre=args.genre, top_n=args.top)

    # display formatted recommendations in terminal
    print(f"\n=== Recommendations for {args.user} (Mood: '{args.mood or 'Any'}', Genre: '{args.genre or 'Any'}') ===")
    for idx, r in enumerate(results, 1):
        print(f"\n{idx}. {r['title']} ({r['year']}) - Match: {r['match_pct']}% (Score: {r['hybrid_score']}/5.0)")
        print(f"   Genres : {', '.join(r['genre'])}")
        print(f"   Reason : {r['explanation']}")
    print()


if __name__ == "__main__":
    main()
