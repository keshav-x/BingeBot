// client-side recommendation engine for Vercel
const CATALOGUE = [
    { id: "T001", title: "Inception", year: 2010, genre: ["Sci-Fi", "Action"], mood: ["cerebral", "intense"], rating: 4.8 },
    { id: "T002", title: "The Dark Knight", year: 2008, genre: ["Action", "Crime"], mood: ["dark", "adrenaline"], rating: 4.9 },
    { id: "T003", title: "Interstellar", year: 2014, genre: ["Sci-Fi", "Drama"], mood: ["cerebral", "emotional"], rating: 4.7 },
    { id: "T004", title: "The Shawshank Redemption", year: 1994, genre: ["Drama", "Crime"], mood: ["inspiring", "emotional"], rating: 4.9 },
    { id: "T005", title: "Spirited Away", year: 2001, genre: ["Animation", "Fantasy"], mood: ["whimsical", "inspiring"], rating: 4.6 },
    { id: "T006", title: "Knives Out", year: 2019, genre: ["Mystery", "Comedy"], mood: ["cerebral", "fun"], rating: 4.4 }
];

const RATINGS = {
    U001: { T001: 5.0, T003: 4.8 },
    U002: { T002: 5.0, T006: 4.5 },
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

function clientSideRecommend(userId, mood, genre, topN = 3) {
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

        const rawScore = hasHistory && collab > 0 ? (0.50 * collab) + (0.30 * content) + (0.20 * mBoost * 5.0) : (0.75 * item.rating) + (0.25 * mBoost * 5.0);
        const finalScore = parseFloat(Math.min(5.0, Math.max(1.0, rawScore)).toFixed(1));
        const matchPct = Math.round((finalScore / 5.0) * 100);

        const reasons = [];
        if (collab >= 3.8) reasons.push("similar viewers loved this");
        if (mBoost > 0) reasons.push(`matches your ${mood} mood`);
        if (!reasons.length) reasons.push(`rated ${item.rating}/5.0 in catalogue`);

        return {
            title: item.title,
            year: item.year,
            genre: item.genre,
            mood: item.mood,
            catalogue_rating: item.rating,
            hybrid_score: finalScore,
            match_pct: matchPct,
            explanation: reasons.join(", ").replace(/^./, c => c.toUpperCase()) + ".",
            scores: {
                collaborative: collab ? parseFloat(collab.toFixed(1)) : 0.0,
                content: parseFloat(content.toFixed(1)),
                mood_boost: mBoost
            }
        };
    });

    scored.sort((a, b) => b.hybrid_score - a.hybrid_score);
    return scored.slice(0, topN);
}

// apply quick test presets
window.applyPreset = function(userId, genre, mood) {
    const userSelect = document.getElementById("userSelect");
    const genreSelect = document.getElementById("genreSelect");
    if (userSelect) userSelect.value = userId;
    if (genreSelect) genreSelect.value = genre;

    // update active mood chip
    document.querySelectorAll(".mood-chip").forEach(chip => {
        if (chip.dataset.mood === mood || (!mood && chip.dataset.mood === "")) {
            chip.classList.add("active");
        } else {
            chip.classList.remove("active");
        }
    });

    window.fetchRecommendations();
};

// fetch and render recommendations
window.fetchRecommendations = async function() {
    const userSelect = document.getElementById("userSelect");
    const genreSelect = document.getElementById("genreSelect");
    const topNSelect = document.getElementById("topNSelect");
    const container = document.getElementById("resultsContainer");
    const modeIndicator = document.getElementById("modeIndicator");

    if (!container) return;

    const userId = userSelect ? userSelect.value : "U001";
    const genre = genreSelect ? genreSelect.value : "";
    const topN = topNSelect ? parseInt(topNSelect.value, 10) : 3;

    const activeChip = document.querySelector(".mood-chip.active");
    const mood = activeChip ? activeChip.dataset.mood || "" : "";

    const isColdStart = (userId === "NEW_USER");
    if (modeIndicator) {
        modeIndicator.textContent = isColdStart
            ? "Cold-Start Popularity + Mood Mode"
            : "Collaborative + Content Hybrid Mode";
    }

    container.innerHTML = '<div style="text-align:center;padding:32px 0;color:var(--text-muted);">Finding best titles...</div>';

    let recommendations = [];
    try {
        const res = await fetch("/api/recommend", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: userId, mood, genre, top_n: topN })
        });
        if (res.ok) {
            const data = await res.json();
            recommendations = data.recommendations || [];
        }
    } catch (_) {}

    if (!recommendations.length) {
        recommendations = clientSideRecommend(userId, mood, genre, topN);
    }

    if (!recommendations.length) {
        container.innerHTML = '<div style="text-align:center;padding:36px 0;color:var(--text-muted);background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);">No titles match the chosen genre and mood. Try selecting "All Genres" or "Any Tone".</div>';
        return;
    }

    container.innerHTML = recommendations.map(r => {
        const genres = (r.genre || []).map(g => `<span class="meta-tag">${escapeHtml(g)}</span>`).join("");
        const moods = (r.mood || []).map(m => `<span class="meta-tag" style="background:#FAF8F5;">${escapeHtml(m)}</span>`).join("");
        const collabScore = r.scores?.collaborative ? `Collab: ${r.scores.collaborative}` : "Cold-Start Prior";

        return `
            <div class="recommendation-card">
                <div class="card-top">
                    <div class="card-title-group">
                        <span class="movie-title">${escapeHtml(r.title)}</span>
                        <span class="movie-year">(${r.year})</span>
                    </div>
                    <div class="score-box">
                        <div class="match-score">${r.match_pct}% Match</div>
                        <div class="pred-rating">Score: ${Number(r.hybrid_score).toFixed(1)} / 5.0</div>
                    </div>
                </div>

                <div class="meta-tags">
                    ${genres}
                    ${moods}
                </div>

                <div class="explanation-footer">
                    <span class="why-box">Why: ${escapeHtml(r.explanation)}</span>
                    <span class="sub-scores">${collabScore}</span>
                </div>
            </div>`;
    }).join("");
};

function escapeHtml(s) {
    const d = document.createElement("div");
    d.textContent = s || "";
    return d.innerHTML;
}

// setup event listeners on page load
document.addEventListener("DOMContentLoaded", () => {
    // bind mood chip click events
    document.querySelectorAll(".mood-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            document.querySelectorAll(".mood-chip").forEach(c => c.classList.remove("active"));
            chip.classList.add("active");
            window.fetchRecommendations();
        });
    });

    // bind change listeners to dropdowns for instant interactive update
    const userSelect = document.getElementById("userSelect");
    const genreSelect = document.getElementById("genreSelect");
    const topNSelect = document.getElementById("topNSelect");
    if (userSelect) userSelect.addEventListener("change", window.fetchRecommendations);
    if (genreSelect) genreSelect.addEventListener("change", window.fetchRecommendations);
    if (topNSelect) topNSelect.addEventListener("change", window.fetchRecommendations);

    // initial fetch on page load
    window.fetchRecommendations();
});
