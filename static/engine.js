// client-side recommendation engine for Vercel
const CATALOGUE = [
    { id: "T001", title: "Inception", year: 2010, genre: ["Sci-Fi", "Action"], mood: ["cerebral", "intense"], rating: 4.8, poster: "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=400&q=80" },
    { id: "T002", title: "The Dark Knight", year: 2008, genre: ["Action", "Crime"], mood: ["dark", "adrenaline"], rating: 4.9, poster: "https://images.unsplash.com/photo-1509347528160-9a9e33742cdb?w=400&q=80" },
    { id: "T003", title: "Interstellar", year: 2014, genre: ["Sci-Fi", "Drama"], mood: ["cerebral", "emotional"], rating: 4.7, poster: "https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=400&q=80" },
    { id: "T004", title: "The Shawshank Redemption", year: 1994, genre: ["Drama", "Crime"], mood: ["uplifting", "emotional"], rating: 4.9, poster: "https://images.unsplash.com/photo-1518676590629-3dcbd9c5a5c9?w=400&q=80" },
    { id: "T005", title: "Spirited Away", year: 2001, genre: ["Animation", "Fantasy"], mood: ["whimsical", "uplifting"], rating: 4.6, poster: "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=400&q=80" },
    { id: "T006", title: "Knives Out", year: 2019, genre: ["Mystery", "Comedy"], mood: ["cerebral", "fun"], rating: 4.4, poster: "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=400&q=80" }
];

const RATINGS = {
    U001: { T001: 5.0, T003: 4.8 },
    U002: { T002: 5.0, T004: 4.5 },
    U003: { T004: 5.0, T005: 4.8 }
};

function cosineSim(vecA, vecB) {
    let dot = 0, mA = 0, mB = 0;
    for (const k of Object.keys(vecA)) {
        if (vecB[k] !== undefined) dot += vecA[k] * vecB[k];
        mA += vecA[k] * vecA[k];
    }
    for (const k of Object.keys(vecB)) mB += vecB[k] * vecB[k];
    if (mA === 0 || mB === 0) return 0;
    return dot / (Math.sqrt(mA) * Math.sqrt(mB));
}

function clientSideRecommend(userId, mood, genre, topN = 4) {
    const userRatings = RATINGS[userId] || {};
    const hasHistory = Object.keys(userRatings).length > 0;

    let scored = CATALOGUE.filter(item => {
        if (userRatings[item.id]) return false;
        if (genre && !item.genre.some(g => g.toLowerCase() === genre.toLowerCase())) return false;
        return true;
    }).map(item => {
        const mBoost = mood && item.mood.some(m => m.toLowerCase() === mood.toLowerCase()) ? 1.0 : 0.0;
        let collab = 0.0, content = item.rating;

        if (hasHistory) {
            let simSum = 0, weightSum = 0;
            for (const [otherId, ratings] of Object.entries(RATINGS)) {
                if (otherId === userId || !ratings[item.id]) continue;
                const sim = cosineSim(userRatings, ratings);
                if (sim > 0) { simSum += sim * ratings[item.id]; weightSum += sim; }
            }
            if (weightSum > 0) collab = simSum / weightSum;
        }

        const rawScore = hasHistory && collab > 0 ? (0.50 * collab) + (0.30 * content) + (0.20 * mBoost * 5.0) : (0.70 * item.rating) + (0.30 * mBoost * 5.0);
        const finalScore = parseFloat(Math.min(5.0, Math.max(1.0, rawScore)).toFixed(1));
        const matchPct = Math.round((finalScore / 5.0) * 100);

        const reasons = [];
        if (collab >= 3.8) reasons.push("similar viewers loved this");
        if (mBoost > 0) reasons.push(`fits your ${mood} mood`);
        if (!reasons.length) reasons.push(`rated ${item.rating}/5 in catalogue`);

        return {
            title: item.title, year: item.year, genre: item.genre, catalogue_rating: item.rating,
            hybrid_score: finalScore, match_pct: matchPct,
            explanation: reasons.join(", ").replace(/^./, c => c.toUpperCase()) + ".",
            poster: item.poster
        };
    });

    scored.sort((a, b) => b.hybrid_score - a.hybrid_score);
    return scored.slice(0, topN);
}

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("recommendForm");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const userId = document.getElementById("userSelect").value;
        const mood = document.getElementById("moodSelect").value;
        const genre = document.getElementById("genreSelect").value;
        const grid = document.getElementById("resultsGrid");
        const status = document.getElementById("statusMsg");

        grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;color:#78716C;">Calculating recommendations...</div>';

        let results = [];
        try {
            const res = await fetch("/api/recommend", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: userId, mood, genre, top_n: 4 })
            });
            if (res.ok) {
                const data = await res.json();
                results = data.recommendations || [];
            }
        } catch (_) {}

        if (!results.length) results = clientSideRecommend(userId, mood, genre, 4);

        if (status) status.textContent = `Found ${results.length} recommendations for ${userId}`;

        if (!results.length) {
            grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px;color:#78716C;">No movies match your selected filters. Try choosing "Any Mood" or "Any Genre".</div>';
            return;
        }

        grid.innerHTML = results.map(r => `
            <div class="movie-card">
                <img src="${r.poster}" alt="${r.title}" class="movie-poster" onerror="this.src='https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=400&q=80'">
                <div class="movie-body">
                    <div class="movie-header">
                        <span class="movie-title">${r.title}</span>
                        <span class="movie-year">${r.year}</span>
                    </div>
                    <div class="movie-genres">${(r.genre || []).map(g => `<span class="genre-pill">${g}</span>`).join("")}</div>
                    <div class="score-row">
                        <span class="star-rating">★ ${Number(r.hybrid_score).toFixed(1)}</span>
                        <span class="match-badge">${r.match_pct}% Match</span>
                    </div>
                    <div class="movie-reason">${r.explanation}</div>
                </div>
            </div>`).join("");
    });
});
