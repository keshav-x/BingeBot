// Standalone Serverless Embedded Engine
        // Enables 100% full functionality on Vercel or any static host without requiring a running server
        const EMBEDDED_CATALOGUE = [
            {
                id: "T001",
                title: "Inception",
                genre: ["Sci-Fi", "Thriller"],
                year: 2010,
                rating: 4.8,
                sentiment_tone: "cerebral",
                mood_tags: ["cerebral", "tense", "mind-bending"],
                description: "A thief who steals corporate secrets through dream-sharing technology is given the inverse task of planting an idea into the mind of a CEO."
            },
            {
                id: "T002",
                title: "The Dark Knight",
                genre: ["Crime", "Action"],
                year: 2008,
                rating: 4.9,
                sentiment_tone: "dark",
                mood_tags: ["dark", "gritty", "tense"],
                description: "When the menace known as the Joker wreaks havoc on Gotham, Batman must accept one of the greatest psychological and physical tests."
            },
            {
                id: "T003",
                title: "Interstellar",
                genre: ["Sci-Fi", "Drama"],
                year: 2014,
                rating: 4.8,
                sentiment_tone: "reflective",
                mood_tags: ["cerebral", "inspiring", "melancholic"],
                description: "When Earth becomes uninhabitable in the future, a farmer and ex-NASA pilot is tasked to pilot a spacecraft to find a new planet."
            },
            {
                id: "T004",
                title: "The Shawshank Redemption",
                genre: ["Drama"],
                year: 1994,
                rating: 4.9,
                sentiment_tone: "inspiring",
                mood_tags: ["inspiring", "reflective", "uplifting"],
                description: "Over the course of several years, two convicts form a friendship, seeking solace and eventual redemption through basic compassion."
            },
            {
                id: "T005",
                title: "Spirited Away",
                genre: ["Animation", "Fantasy"],
                year: 2001,
                rating: 4.7,
                sentiment_tone: "inspiring",
                mood_tags: ["inspiring", "fun", "magical"],
                description: "During her family's move to the suburbs, a sullen 10-year-old girl wanders into a world ruled by gods, witches, and spirits."
            },
            {
                id: "T006",
                title: "Knives Out",
                genre: ["Comedy", "Mystery"],
                year: 2019,
                rating: 4.5,
                sentiment_tone: "fun",
                mood_tags: ["fun", "witty", "tense"],
                description: "A master detective investigates the death of the patriarch of an eccentric, combative family."
            }
        ];

        const EMBEDDED_RATINGS = {
            "U001": { "T001": 5, "T003": 5, "T002": 4 },
            "U002": { "T002": 5, "T006": 4, "T001": 4 },
            "U003": { "T004": 5, "T005": 5, "T003": 4 }
        };

        let currentMood = "";

        function applyPreset(userId, genre, mood) {
            document.getElementById('userSelect').value = userId;
            document.getElementById('genreSelect').value = genre;
            currentMood = mood;
            document.querySelectorAll('.mood-chip').forEach(chip => {
                if (chip.getAttribute('data-mood') === mood) chip.classList.add('active');
                else chip.classList.remove('active');
            });
            fetchRecommendations();
        }

        document.querySelectorAll('.mood-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                document.querySelectorAll('.mood-chip').forEach(p => p.classList.remove('active'));
                chip.classList.add('active');
                currentMood = chip.getAttribute('data-mood');
                fetchRecommendations();
            });
        });

        // Client-Side Zero-Server Recommendation Engine
        function computeClientSideRecommendations(userId, genre, mood, topN) {
            const isColdStart = (userId === "NEW_USER" || !EMBEDDED_RATINGS[userId]);
            let candidates = EMBEDDED_CATALOGUE.slice();

            // Filter by genre if selected
            if (genre) {
                candidates = candidates.filter(t => t.genre.includes(genre));
            }

            if (isColdStart) {
                // Cold-Start Popularity Fallback + Mood Match
                const results = candidates.map(t => {
                    const moodMatch = mood && (t.mood_tags.includes(mood) || t.sentiment_tone === mood);
                    const boost = moodMatch ? 0.2 : 0.0;
                    const finalScore = Math.min(5.0, t.rating * (1.0 + boost * 0.1));
                    return {
                        title: t.title,
                        year: t.year,
                        genre: t.genre,
                        catalogue_rating: t.rating,
                        hybrid_score: finalScore,
                        description: t.description,
                        scores: { collaborative: null, content: null, mood_boost: boost },
                        explanation: moodMatch
                            ? `Top catalogue title matching your requested ${mood} tone.`
                            : `Top-rated title in global catalogue.`
                    };
                });

                results.sort((a, b) => b.hybrid_score - a.hybrid_score);
                return { is_cold_start: true, recommendations: results.slice(0, topN) };
            }

            // Personalized Collaborative + Content Hybrid
            const userHistory = EMBEDDED_RATINGS[userId] || {};
            const unrated = candidates.filter(t => userHistory[t.id] === undefined);

            const scored = (unrated.length > 0 ? unrated : candidates).map(t => {
                // 1. Collaborative rating estimation
                let peerSum = 0;
                let peerCount = 0;
                for (const [peerId, ratings] of Object.entries(EMBEDDED_RATINGS)) {
                    if (peerId !== userId && ratings[t.id] !== undefined) {
                        peerSum += ratings[t.id];
                        peerCount++;
                    }
                }
                const collabScore = peerCount > 0 ? (peerSum / peerCount) : t.rating;

                // 2. Content similarity with user's top-rated items
                let contentScore = 3.5;
                for (const [watchedId, rating] of Object.entries(userHistory)) {
                    if (rating >= 4) {
                        const watched = EMBEDDED_CATALOGUE.find(m => m.id === watchedId);
                        if (watched) {
                            const sharedGenre = t.genre.some(g => watched.genre.includes(g));
                            if (sharedGenre) contentScore = Math.max(contentScore, 4.6);
                        }
                    }
                }

                // 3. Mood tone boost
                const moodMatch = mood && (t.mood_tags.includes(mood) || t.sentiment_tone === mood);
                const moodBoost = moodMatch ? 0.2 : 0.0;

                // Hybrid combination formula (scale 0-5.0):
                // 50% Collab + 30% Content + 20% Mood
                const hybrid = (0.50 * collabScore) + (0.30 * contentScore) + (0.20 * moodBoost * 5.0);

                let explanation = "Recommended based on viewer tastes";
                if (peerCount > 0 && moodMatch) {
                    explanation = `Similar viewers rated this ${collabScore.toFixed(1)}/5.0; matches your requested ${mood} tone.`;
                } else if (peerCount > 0) {
                    explanation = `Viewers with similar taste rated this ${collabScore.toFixed(1)}/5.0; shares genre traits.`;
                } else if (moodMatch) {
                    explanation = `Matches your requested ${mood} tone and content style.`;
                }

                return {
                    title: t.title,
                    year: t.year,
                    genre: t.genre,
                    catalogue_rating: t.rating,
                    hybrid_score: hybrid,
                    description: t.description,
                    scores: { collaborative: collabScore, content: contentScore, mood_boost: moodBoost },
                    explanation: explanation
                };
            });

            scored.sort((a, b) => b.hybrid_score - a.hybrid_score);
            return { is_cold_start: false, recommendations: scored.slice(0, topN) };
        }

        async function fetchRecommendations() {
            const container = document.getElementById('resultsContainer');
            const userId = document.getElementById('userSelect').value;
            const genre = document.getElementById('genreSelect').value;
            const topN = parseInt(document.getElementById('topNSelect').value);
            const indicator = document.getElementById('modeIndicator');

            container.innerHTML = '<div style="padding: 24px; text-align: center; color: var(--text-muted);">Computing hybrid recommendations...</div>';

            let data = null;

            // Try backend API first (when running Flask locally)
            try {
                const response = await fetch('/api/recommend', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: userId, mood: currentMood, genre: genre, top_n: topN })
                });
                if (response.ok) {
                    data = await response.json();
                }
            } catch (err) {
                // Backend server not available (e.g. static Vercel deployment)
            }

            // Seamless Serverless Fallback
            if (!data) {
                data = computeClientSideRecommendations(userId, genre, currentMood, topN);
            }

            if (data.is_cold_start) {
                indicator.textContent = 'Cold Start Fallback (Top Popular Titles + Mood Match)';
            } else {
                indicator.textContent = 'Personalized Hybrid Mode (Collaborative + Content + Mood)';
            }

            if (!data.recommendations || data.recommendations.length === 0) {
                container.innerHTML = '<div style="padding: 24px; text-align: center; color: var(--text-muted);">No catalogue titles match the requested combination of genre and mood.</div>';
                return;
            }

            container.innerHTML = data.recommendations.map(item => {
                const genres = (item.genre || []).map(g => `<span class="meta-tag">${g}</span>`).join('');
                const rawScore = item.hybrid_score !== undefined ? item.hybrid_score : (item.catalogue_rating || 4.0);
                const matchPercent = Math.min(100, Math.max(10, Math.round((rawScore / 5.0) * 100)));
                const predRating = Math.min(5.0, Math.max(1.0, rawScore)).toFixed(1);

                const collabScore = item.scores && item.scores.collaborative ? item.scores.collaborative.toFixed(1) : null;
                const contentScore = item.scores && item.scores.content ? item.scores.content.toFixed(1) : null;
                const moodMatch = item.scores && item.scores.mood_boost > 0 ? "Tone Matched (+0.2)" : null;

                const breakdownParts = [];
                if (collabScore) breakdownParts.push(`Similar Viewers: ${collabScore} / 5.0`);
                if (contentScore) breakdownParts.push(`Content Trait Match: ${contentScore} / 5.0`);
                if (moodMatch) breakdownParts.push(moodMatch);

                return `
                    <article class="recommendation-card">
                        <div class="card-top">
                            <div>
                                <div class="card-title-group">
                                    <h3 class="movie-title">${escapeHtml(item.title)}</h3>
                                    <span class="movie-year">${item.year || ''}</span>
                                </div>
                                <div class="meta-tags" style="margin-top: 6px;">
                                    ${genres}
                                    <span class="meta-tag">Catalogue Rating: ${item.catalogue_rating || '4.5'} / 5.0</span>
                                </div>
                            </div>
                            <div class="score-box">
                                <div class="match-score">${matchPercent}% Match</div>
                                <div class="pred-rating">Predicted Rating: ${predRating} / 5.0</div>
                            </div>
                        </div>

                        <p class="synopsis">${escapeHtml(item.description)}</p>

                        <div class="explanation-footer">
                            <div class="why-box">Why: ${escapeHtml(item.explanation)}</div>
                            ${breakdownParts.length > 0 ? `<div class="sub-scores">${breakdownParts.join(' &bull; ')}</div>` : ''}
                        </div>
                    </article>
                `;
            }).join('');
        }

        function escapeHtml(s) {
            if (!s) return '';
            const d = document.createElement('div');
            d.textContent = s;
            return d.innerHTML;
        }

        window.addEventListener('DOMContentLoaded', () => {
            fetchRecommendations();
        });
