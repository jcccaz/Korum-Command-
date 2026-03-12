/* KORUM-OS Logic - Fully Integrated (Telemetry, Interrogation, Charts) */

// ============================================================
// AUTH MODULE
// ============================================================
const KorumAuth = {
    authenticated: false,
    authEnabled: true,
    user: null,

    async checkStatus() {
        try {
            const res = await fetch('/api/auth/status', { credentials: 'include' });
            const data = await res.json();
            this.authenticated = data.authenticated;
            this.authEnabled = data.auth_enabled;
            this.user = data.user || null;

            if (this.authEnabled && !this.authenticated) {
                this.showModal();
            } else {
                this.hideModal();
                this.updateNavbar();
            }
        } catch (e) {
            console.error('Auth check failed:', e);
        }
    },

    async login(email, password) {
        const errorEl = document.getElementById('loginError');
        const btn = document.getElementById('loginSubmitBtn');
        if (btn) btn.disabled = true;

        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ email, password })
            });
            if (res.status === 429) {
                if (errorEl) { errorEl.textContent = 'Too many attempts — wait and try again'; errorEl.style.display = 'block'; }
                return false;
            }
            const text = await res.text();
            let data;
            try { data = JSON.parse(text); } catch { data = { success: false, error: `Server error (${res.status})` }; }
            if (data.success) {
                this.authenticated = true;
                this.user = data.user;
                this.hideModal();
                this.updateNavbar();
                return true;
            } else {
                if (errorEl) { errorEl.textContent = data.error; errorEl.style.display = 'block'; }
                return false;
            }
        } catch (e) {
            console.error('Login error:', e);
            if (errorEl) { errorEl.textContent = 'Connection failed'; errorEl.style.display = 'block'; }
            return false;
        } finally {
            if (btn) btn.disabled = false;
        }
    },

    async register(email, password) {
        const errorEl = document.getElementById('registerError');
        const btn = document.getElementById('registerSubmitBtn');
        if (btn) btn.disabled = true;

        try {
            const res = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ email, password })
            });
            if (res.status === 429) {
                if (errorEl) { errorEl.textContent = 'Too many attempts — wait and try again'; errorEl.style.display = 'block'; }
                return false;
            }
            const text = await res.text();
            let data;
            try { data = JSON.parse(text); } catch { data = { success: false, error: `Server error (${res.status})` }; }
            if (data.success) {
                this.authenticated = true;
                this.user = data.user;
                this.hideModal();
                this.updateNavbar();
                return true;
            } else {
                if (errorEl) { errorEl.textContent = data.error; errorEl.style.display = 'block'; }
                return false;
            }
        } catch (e) {
            console.error('Register error:', e);
            if (errorEl) { errorEl.textContent = 'Connection failed'; errorEl.style.display = 'block'; }
            return false;
        } finally {
            if (btn) btn.disabled = false;
        }
    },

    async logout() {
        try {
            await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
        } catch (e) { /* ignore */ }
        this.authenticated = false;
        this.user = null;
        this.updateNavbar();
        if (this.authEnabled) this.showModal();
    },

    showModal() {
        const modal = document.getElementById('authModal');
        if (modal) modal.style.display = 'flex';
    },

    hideModal() {
        const modal = document.getElementById('authModal');
        if (modal) modal.style.display = 'none';
    },

    updateNavbar() {
        const statusEl = document.getElementById('authStatus');
        const emailEl = document.getElementById('authUserEmail');
        if (!statusEl) return;

        if (this.authenticated && this.user) {
            statusEl.style.display = 'flex';
            if (emailEl) emailEl.textContent = this.user.email;
        } else {
            statusEl.style.display = 'none';
        }
    },

    initListeners() {
        // Tab switching
        document.querySelectorAll('[data-auth-tab]').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                const mode = tab.dataset.authTab;
                document.getElementById('authLoginForm').style.display = mode === 'login' ? 'block' : 'none';
                document.getElementById('authRegisterForm').style.display = mode === 'register' ? 'block' : 'none';
                // Clear errors
                document.getElementById('loginError').style.display = 'none';
                document.getElementById('registerError').style.display = 'none';
            });
        });

        // Login submit
        document.getElementById('loginSubmitBtn')?.addEventListener('click', () => {
            const email = document.getElementById('loginEmail')?.value?.trim();
            const password = document.getElementById('loginPassword')?.value;
            if (email && password) this.login(email, password);
        });

        // Register submit
        document.getElementById('registerSubmitBtn')?.addEventListener('click', () => {
            const email = document.getElementById('registerEmail')?.value?.trim();
            const password = document.getElementById('registerPassword')?.value;
            const confirm = document.getElementById('registerPasswordConfirm')?.value;
            const errorEl = document.getElementById('registerError');
            if (password !== confirm) {
                if (errorEl) { errorEl.textContent = 'Passwords do not match'; errorEl.style.display = 'block'; }
                return;
            }
            if (email && password) this.register(email, password);
        });

        // Enter key support
        document.getElementById('loginPassword')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') document.getElementById('loginSubmitBtn')?.click();
        });
        document.getElementById('registerPasswordConfirm')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') document.getElementById('registerSubmitBtn')?.click();
        });

        // Logout
        document.getElementById('authLogoutBtn')?.addEventListener('click', () => this.logout());
    }
};

// Init: Demo terms gate → then auth
document.addEventListener('DOMContentLoaded', () => {
    const termsOverlay = document.getElementById('demoTermsOverlay');
    const termsAccept = document.getElementById('demoTermsAccept');
    const termsAcked = sessionStorage.getItem('korum_terms_acked');

    if (termsOverlay && !termsAcked) {
        // Show splash, defer auth until acknowledged
        termsAccept.addEventListener('click', () => {
            sessionStorage.setItem('korum_terms_acked', '1');
            termsOverlay.classList.add('dismissed');
            KorumAuth.initListeners();
            KorumAuth.checkStatus();
        });
    } else {
        // Already accepted this session — go straight to auth
        if (termsOverlay) termsOverlay.classList.add('dismissed');
        KorumAuth.initListeners();
        KorumAuth.checkStatus();
    }
});

// === AUTH-AWARE FETCH WRAPPER ===
async function authFetch(url, options = {}) {
    options.credentials = 'include';
    const response = await fetch(url, options);
    if (response.status === 401 && KorumAuth.authEnabled) {
        KorumAuth.authenticated = false;
        KorumAuth.showModal();
        throw new Error('Authentication required — please log in.');
    }
    return response;
}

// === GLOBAL STATE FOR EXPORTS ===
let lastCouncilData = null;
let lastQueryText = '';

// === PROVIDER NAME MAP (shared across interrogation, verification, score updates) ===
const PROVIDER_NAME_MAP = {
    "Strategic Core": "openai", "Architect": "anthropic", "Critic": "google",
    "Intel": "perplexity", "Analyst": "mistral", "GPT-4o": "openai",
    "Claude": "anthropic", "Gemini": "google", "Perplexity": "perplexity",
    "Mistral": "mistral", "STRATEGIST": "openai", "ARCHITECT": "anthropic",
    "INTEGRATOR": "google", "INTEGRATOR (CRITIC)": "google", "SCOUT": "perplexity",
    "ANALYST": "mistral", "RESEARCHER": "google", "CRITIC": "mistral",
    "CYBER_OPS": "openai", "COUNTERINTEL": "anthropic", "SIGINT": "google",
    "INTEL_ANALYST": "perplexity", "HACKER": "mistral",
    "openai": "openai", "anthropic": "anthropic", "google": "google",
    "perplexity": "perplexity", "mistral": "mistral",
};

function resolveProviderKey(name) {
    if (!name) return null;
    const clean = name.replace(/[^a-zA-Z0-9\s_()-]/g, '').trim();
    const exact = PROVIDER_NAME_MAP[clean];
    if (exact) return exact;
    const partial = Object.keys(PROVIDER_NAME_MAP).find(k => clean.includes(k));
    return partial ? PROVIDER_NAME_MAP[partial] : null;
}

// === TRUTH SCORE RECALIBRATION ===
function updateTruthScore(provider, delta, reason) {
    if (!provider || !lastCouncilData?.results?.[provider]) return;

    const result = lastCouncilData.results[provider];
    const oldScore = result.truth_meter || 85;
    const newScore = Math.max(0, Math.min(100, oldScore + delta));
    result.truth_meter = newScore;

    // Update UI card
    const card = document.querySelector(`.agent-card[data-provider="${provider}"]`);
    if (card) {
        const scoreEl = card.querySelector('.truth-score-val');
        const fillEl = card.querySelector('.truth-fill');
        if (scoreEl) {
            scoreEl.textContent = `TRUTH SCORE: ${newScore}/100`;
            scoreEl.style.color = newScore > 80 ? '#00FF9D' : newScore > 50 ? '#FFB020' : '#FF4444';
            // Flash animation
            scoreEl.style.transition = 'none';
            scoreEl.style.transform = 'scale(1.3)';
            scoreEl.style.textShadow = delta > 0 ? '0 0 12px #00FF9D' : '0 0 12px #FF4444';
            setTimeout(() => {
                scoreEl.style.transition = 'all 0.6s ease';
                scoreEl.style.transform = 'scale(1)';
                scoreEl.style.textShadow = 'none';
            }, 100);
        }
        if (fillEl) {
            fillEl.style.transition = 'width 0.8s ease';
            fillEl.style.width = `${newScore}%`;
        }
    }

    // Update session stats (overall confidence)
    const confEl = document.getElementById('stat-confidence');
    if (confEl && lastCouncilData.results) {
        const scores = Object.values(lastCouncilData.results).filter(r => r?.truth_meter).map(r => r.truth_meter);
        if (scores.length) confEl.textContent = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) + '%';
    }

    const sign = delta > 0 ? '+' : '';
    logTelemetry(`TRUTH RECALIBRATED: ${provider.toUpperCase()} ${sign}${delta} → ${newScore}/100 (${reason})`, delta > 0 ? "success" : "error");
}

// === FILE UPLOAD STATE ===
let pendingFiles = [];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf', '.docx', '.xlsx'];

function renderFilePreview() {
    const bar = document.getElementById('filePreviewBar');
    const attachBtn = document.getElementById('attachBtn');
    if (!bar) return;
    if (!pendingFiles.length) {
        bar.classList.remove('has-files');
        bar.innerHTML = '';
        if (attachBtn) attachBtn.classList.remove('has-files');
        return;
    }
    bar.classList.add('has-files');
    if (attachBtn) attachBtn.classList.add('has-files');
    bar.innerHTML = pendingFiles.map((f, i) => {
        const isImage = f.type.startsWith('image/');
        const isPdf = f.name.toLowerCase().endsWith('.pdf');
        const icon = isImage ? '&#128444;' : (isPdf ? '&#128196;' : '&#128202;');
        const sizeMB = (f.size / 1024 / 1024).toFixed(1);
        return `<div class="file-chip">
            <span class="file-icon">${icon}</span>
            <span class="file-name" title="${f.name}">${f.name}</span>
            <span style="color:#555">${sizeMB}MB</span>
            <button class="file-remove" onclick="removeFile(${i})" title="Remove">&times;</button>
        </div>`;
    }).join('');
}

function removeFile(index) {
    pendingFiles.splice(index, 1);
    renderFilePreview();
}

function addFiles(fileList) {
    for (const file of fileList) {
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (!ALLOWED_EXTENSIONS.includes(ext)) {
            logTelemetry(`Unsupported file type: ${ext}`, "error");
            continue;
        }
        if (file.size > MAX_FILE_SIZE) {
            logTelemetry(`File too large: ${file.name} (${(file.size / 1024 / 1024).toFixed(1)}MB limit: 10MB)`, "error");
            continue;
        }
        pendingFiles.push(file);
    }
    renderFilePreview();
}

// === REPORT LIBRARY ===
async function saveReport() {
    if (!lastCouncilData) {
        showProcessingToast("No report to save. Run a council query first.");
        return;
    }
    try {
        const payload = {
            ...lastCouncilData,
            query: sessionState.originalQuery || lastQueryText || ""
        };
        const resp = await authFetch('/api/reports/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await resp.json();
        if (data.success) {
            showProcessingToast("Report saved to library");
            logTelemetry(`Report saved: ${data.id}`, "success");
        } else {
            showProcessingToast("Save failed: " + (data.error || "Unknown"));
        }
    } catch (e) {
        console.error("Save report error:", e);
        showProcessingToast("Save failed: " + e.message);
    }
}

async function loadReportLibrary() {
    const list = document.getElementById('libraryList');
    if (!list) { console.warn('[Reports] libraryList element not found'); return; }
    list.innerHTML = '<div class="library-empty">Loading...</div>';

    try {
        const resp = await authFetch('/api/reports/list');
        const data = await resp.json();
        if (!data.success) {
            list.innerHTML = `<div class="library-empty">Error: ${data.error || 'Unknown'}</div>`;
            return;
        }
        if (!data.reports || !data.reports.length) {
            list.innerHTML = '<div class="library-empty">No saved reports yet. Run a council query and save the results.</div>';
            return;
        }
        list.innerHTML = data.reports.map(r => `
            <div class="report-card" onclick="recallReport('${r.id}')">
                <div class="report-card-header">
                    <span class="report-card-role">${r.roleName || 'Council'}</span>
                    <span class="report-card-time">${r.timestamp}</span>
                </div>
                <div class="report-card-query">${r.query}</div>
                <div class="report-card-footer">
                    <span class="report-card-providers">${r.provider_count} providers</span>
                    <button class="report-card-delete" onclick="event.stopPropagation(); deleteReport('${r.id}')" title="Delete">&times;</button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.error('[Reports] Load error:', e);
        list.innerHTML = `<div class="library-empty">Failed to load reports: ${e.message}</div>`;
    }
}

async function recallReport(id) {
    try {
        const resp = await authFetch(`/api/reports/${id}`);
        const data = await resp.json();
        if (!data.success || !data.report) {
            showProcessingToast("Failed to load report");
            return;
        }
        const report = data.report;

        // Restore state
        lastCouncilData = { ...report, roleName: report.roleName };
        sessionState.originalQuery = report.query || "";
        sessionState.lastResponses = {};
        if (report.results) {
            Object.keys(report.results).forEach(p => {
                if (report.results[p] && report.results[p].response) {
                    sessionState.lastResponses[p] = report.results[p].response;
                }
            });
        }

        // Re-render
        renderResults(report, report.roleName || "Recalled");
        logTelemetry(`Report recalled: ${id}`, "system");

        // Close library
        toggleReportLibrary(false);
    } catch (e) {
        showProcessingToast("Failed to recall report: " + e.message);
    }
}

async function deleteReport(id) {
    if (!confirm("Delete this saved report?")) return;
    try {
        await authFetch(`/api/reports/${id}`, { method: 'DELETE' });
        logTelemetry(`Report deleted: ${id}`, "system");
        loadReportLibrary(); // Refresh list
    } catch (e) {
        showProcessingToast("Delete failed: " + e.message);
    }
}

function toggleReportLibrary(show) {
    const panel = document.getElementById('reportLibrary');
    const overlay = document.getElementById('libraryOverlay');
    if (!panel) return;
    if (show === undefined) show = !panel.classList.contains('visible');
    if (show) {
        panel.classList.add('visible');
        if (overlay) overlay.classList.add('visible');
        loadReportLibrary();
    } else {
        panel.classList.remove('visible');
        if (overlay) overlay.classList.remove('visible');
    }
}

// === API HEALTH CHECK (Proactive) ===
async function checkAPIHealth() {
    const btn = document.getElementById('healthCheckBtn');
    if (btn) btn.classList.add('checking');
    logTelemetry("Running API health check...", "process");

    try {
        const resp = await authFetch('/api/health/check');
        const data = await resp.json();

        Object.keys(data).forEach(provider => {
            const result = data[provider];
            if (result.status === 'healthy') {
                AIHealth.status[provider] = { state: 'healthy', lastCheck: new Date(), failures: 0, lastError: null };
            } else if (result.status === 'error') {
                AIHealth.status[provider] = { state: 'warning', lastCheck: new Date(), failures: 1, lastError: result.error };
            } else {
                AIHealth.status[provider] = { state: 'offline', lastCheck: new Date(), failures: 3, lastError: result.error };
            }
            AIHealth.updateCardUI(provider);
        });

        const healthy = Object.values(data).filter(r => r.status === 'healthy').length;
        logTelemetry(`Health check complete: ${healthy}/${Object.keys(data).length} providers online`, "system");

        // Update provider status pills in telemetry panel
        updateProviderPills(data);
    } catch (e) {
        logTelemetry("Health check failed: " + e.message, "error");
    } finally {
        if (btn) btn.classList.remove('checking');
    }
}

// Update provider status pills in telemetry panel
function updateProviderPills(data) {
    const strip = document.getElementById('activeProviderStrip');
    if (!strip) return;

    // Clear and re-render dynamic pills
    strip.innerHTML = Object.keys(data).map(provider => {
        const info = data[provider];
        const statusColor = info.status === 'healthy' ? '#00FF9D' : (info.status === 'error' ? '#FFB020' : '#FF4444');
        return `
            <div class="provider-pill" data-provider="${provider}">
                <span class="pill-dot" style="background:${statusColor}; box-shadow:0 0 6px ${statusColor};"></span>
                ${getProviderName(provider)}
            </div>
        `;
    }).join('');
}

function getProviderColor(p) {
    const colors = { openai: "#10a37f", anthropic: "#d97757", google: "#4285f4", perplexity: "#00bcd4", mistral: "#facc15", local: "#a855f7" };
    return colors[p] || "#888";
}

function hexToRgb(hex) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `${r},${g},${b}`;
}

// Session stats — query counter + uptime timer
let sessionQueryCount = 0;
const sessionStartTime = Date.now();

function incrementQueryCount() {
    sessionQueryCount++;
    const el = document.getElementById('statQueries');
    if (el) el.textContent = sessionQueryCount;
}

function updateUptime() {
    // Legacy support or internal tracking
    const elapsed = Math.floor((Date.now() - sessionStartTime) / 60000);
}
setInterval(updateUptime, 30000);

// === RESEARCH DOCK - Smart Clipboard for Research Artifacts ===
const ResearchDock = {
    snippets: [],
    maxSnippets: 20,

    // Content type detection
    detectType(content) {
        const trimmed = content.trim();

        // CSV detection (comma-separated with multiple lines)
        if (/^[^,\n]+(?:,[^,\n]+)+(?:\n[^,\n]+(?:,[^,\n]+)+)+$/m.test(trimmed)) {
            return { type: 'csv', icon: '📋', label: 'CSV Data' };
        }

        // Markdown table detection
        if (/^\|.*\|$/m.test(trimmed) && /\|[-:]+\|/.test(trimmed)) {
            return { type: 'table', icon: '📊', label: 'Table' };
        }

        // Tab-separated table
        if (/^[^\t\n]+\t[^\t\n]+/m.test(trimmed) && trimmed.includes('\n')) {
            return { type: 'table', icon: '📊', label: 'Table' };
        }

        // Code detection (common patterns)
        if (/^(function|const|let|var|class|import|export|def |if |for |while |return )/m.test(trimmed) ||
            /[{}\[\]();]/.test(trimmed) && trimmed.length > 50) {
            return { type: 'code', icon: '💻', label: 'Code' };
        }

        // Number-heavy content (potential chart data)
        const numbers = trimmed.match(/\d+\.?\d*/g) || [];
        if (numbers.length > 3 && numbers.length / trimmed.split(/\s+/).length > 0.3) {
            return { type: 'data', icon: '📈', label: 'Chart Data' };
        }

        // Mermaid diagram
        if (/^(graph|flowchart|pie|sequenceDiagram|classDiagram|gantt)/m.test(trimmed)) {
            return { type: 'mermaid', icon: '🔀', label: 'Diagram' };
        }

        // Default: text
        return { type: 'text', icon: '📝', label: 'Text' };
    },

    // Add snippet to dock
    add(content, source = 'selection') {
        if (!content || content.trim().length < 3) return null;

        const typeInfo = this.detectType(content);
        const snippet = {
            id: `snip-${Date.now()}`,
            content: content.trim(),
            type: typeInfo.type,
            icon: typeInfo.icon,
            label: typeInfo.label,
            source: source,
            tags: [],
            timestamp: new Date(),
            preview: content.trim().substring(0, 80) + (content.length > 80 ? '...' : '')
        };

        this.snippets.unshift(snippet);

        // Limit snippets
        if (this.snippets.length > this.maxSnippets) {
            this.snippets.pop();
        }

        this.render();
        this.save();
        logTelemetry(`Docked: ${typeInfo.label} (${content.length} chars)`, "success");

        return snippet;
    },

    // Remove snippet
    remove(id) {
        this.snippets = this.snippets.filter(s => s.id !== id);
        this.render();
        this.save();
        logTelemetry("Snippet removed from dock", "system");
    },

    // Copy snippet to clipboard
    copy(id) {
        const snippet = this.snippets.find(s => s.id === id);
        if (snippet) {
            navigator.clipboard.writeText(snippet.content).then(() => {
                logTelemetry("Snippet copied to clipboard", "success");
                showProcessingToast("Copied to clipboard!");
            });
        }
    },

    // Tag management
    addTag(id, tag) {
        const snippet = this.snippets.find(s => s.id === id);
        if (snippet && tag && !snippet.tags.includes(tag)) {
            snippet.tags.push(tag);
            this.render();
            this.save();
            logTelemetry(`Tag added: ${tag}`, "success");
        }
    },

    removeTag(id, tag) {
        const snippet = this.snippets.find(s => s.id === id);
        if (snippet) {
            snippet.tags = snippet.tags.filter(t => t !== tag);
            this.render();
            this.save();
        }
    },

    // Summarization Logic
    async summarizeHighlights() {
        if (this.snippets.length === 0) {
            showProcessingToast("No research docked to summarize");
            return;
        }

        logTelemetry("Synthesizing Executive Brief...", "process");
        showProcessingToast("Analyzing research docked...");

        try {
            const response = await authFetch('/api/summarize_snippets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ snippets: this.snippets })
            });

            const data = await response.json();
            if (data.success) {
                // Render summary in a results card
                const container = document.querySelector(".results-content");
                if (container) {
                    const cardEl = document.createElement('div');
                    cardEl.className = 'agent-card google';
                    cardEl.style.cssText = 'grid-column: 1 / -1; border-top: 3px solid #00FF9D;';
                    cardEl.innerHTML = `
                        <div class="agent-header">
                            <span class="agent-name">RESEARCH SUMMARY: EXECUTIVE BRIEF</span>
                            <span class="agent-model">Gemini Flash Synthesis</span>
                        </div>
                        <div class="agent-response">${this.formatMarkdown(data.summary)}</div>
                        <div class="agent-actions" style="margin-top: 20px;">
                            <button class="modal-action-btn copy" id="copyBriefBtn">📋 Copy Brief</button>
                        </div>
                    `;
                    container.innerHTML = '';
                    container.appendChild(cardEl);
                    cardEl.querySelector('#copyBriefBtn').addEventListener('click', () => {
                        navigator.clipboard.writeText(data.summary).then(() => showProcessingToast('Brief copied!'));
                    });
                    document.querySelector(".results-container").classList.add("visible");
                    logTelemetry("Executive Brief Generated", "success");
                }
            } else {
                throw new Error(data.error);
            }
        } catch (e) {
            console.error("Summarization error:", e);
            logTelemetry(`Summarization Failed: ${e.message}`, "error");
        }
    },

    // Sanitize HTML to prevent XSS from AI output
    sanitizeHtml(text) {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    },

    // Helper for basic markdown in summary (sanitizes first, then applies formatting)
    formatMarkdown(text) {
        // Tag Filtering
        const cleanText = text.replace(/\[\/?(DECISION_CANDIDATE|RISK_VECTOR|METRIC_ANCHOR|TRUTH_BOMB)\]/g, "");

        return this.sanitizeHtml(cleanText)
            .replace(/^# (.*$)/gim, '<h2 style="color:#00FF9D; margin-top:20px;">$1</h2>')
            .replace(/^## (.*$)/gim, '<h3 style="color:#FFF; margin-top:15px; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:5px;">$1</h3>')
            .replace(/^### (.*$)/gim, '<h4 style="color:#AAA; margin-top:10px;">$1</h4>')
            .replace(/^\* (.*$)/gim, '<li style="margin-left:20px; color:#DDD;">$1</li>')
            .replace(/^- (.*$)/gim, '<li style="margin-left:20px; color:#DDD;">$1</li>')
            .replace(/\*\*(.*?)\*\*/gim, '<b style="color:#FFF;">$1</b>')
            .replace(/\n/gim, '<br>');
    },

    // Generate chart from snippet
    generateChart(id, chartType = 'auto') {
        const snippet = this.snippets.find(s => s.id === id);
        if (!snippet) return;

        logTelemetry(`Generating ${chartType} chart...`, "process");
        showProcessingToast("Generating visualization...");

        // Build query for chart generation
        let query;
        if (chartType === 'pie') {
            query = `Convert this data into a Mermaid pie chart. Output ONLY the mermaid code block. DATA: "${snippet.content}"`;
        } else if (chartType === 'line') {
            query = `Create a line chart visualization for this data. If using mermaid, use xychart-beta. DATA: "${snippet.content}"`;
        } else if (chartType === 'mermaid') {
            query = `Convert this into a Mermaid flowchart or diagram. Output ONLY the mermaid code block. DATA: "${snippet.content}"`;
        } else {
            // Auto-detect best chart type
            query = `Analyze this data and create the most appropriate visualization (pie chart for proportions, flowchart for processes, or table for comparisons). Use Mermaid syntax. DATA: "${snippet.content}"`;
        }

        triggerCouncil(query);
    },

    // Clear all snippets
    clear() {
        this.snippets = [];
        this.render();
        this.save();
        logTelemetry("Research Dock cleared", "system");
    },

    // Export all snippets
    exportAll(format = 'markdown') {
        if (this.snippets.length === 0) {
            showProcessingToast("No snippets to export");
            return;
        }

        let output = '';
        const timestamp = new Date().toISOString().split('T')[0];

        if (format === 'markdown') {
            output = `# Research Collection\n*Exported: ${timestamp}*\n\n`;
            this.snippets.forEach((s, i) => {
                output += `## ${i + 1}. ${s.icon} ${s.label}\n`;
                output += `*Source: ${s.source} | ${s.timestamp.toLocaleTimeString()}*\n`;
                if (s.tags && s.tags.length > 0) output += `*Tags: ${s.tags.join(', ')}*\n`;
                output += `\n`;
                if (s.type === 'code') {
                    output += `\`\`\`\n${s.content}\n\`\`\`\n\n`;
                } else if (s.type === 'table' || s.type === 'csv') {
                    output += `${s.content}\n\n`;
                } else {
                    output += `${s.content}\n\n`;
                }
                output += `---\n\n`;
            });
        } else if (format === 'csv') {
            // Special logic for CSV export: Find all tables/csv snippets and join them
            const tables = this.snippets.filter(s => s.type === 'table' || s.type === 'csv');
            if (tables.length === 0) {
                showProcessingToast("No tabular data found to export as CSV");
                return;
            }
            output = tables.map(s => {
                if (s.content.includes('|')) return copyAsCSV(s.content);
                return s.content;
            }).join('\n\n---\n\n');
        } else if (format === 'json') {
            output = JSON.stringify(this.snippets, null, 2);
        }

        // Trigger download
        const fileExt = format === 'json' ? 'json' : format === 'csv' ? 'csv' : 'md';
        const blob = new Blob([output], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `research-dock-${timestamp}.${fileExt}`;
        a.click();
        URL.revokeObjectURL(url);

        logTelemetry(`Exported as ${format.toUpperCase()}`, "success");
    },

    // Render dock UI
    render() {
        const container = document.getElementById('researchDock');
        if (!container) return;

        const snippetList = container.querySelector('.dock-snippets');
        if (!snippetList) return;

        // Toolbar Setup
        const toolbar = container.querySelector('.dock-toolbar');
        if (toolbar) {
            if (!toolbar.querySelector('.btn-summarize')) {
                const sumBtn = document.createElement('button');
                sumBtn.className = 'dock-action btn-summarize';
                sumBtn.title = '✨ Generate Executive Summary';
                sumBtn.innerHTML = '✨ Summarize Bits';
                sumBtn.onclick = () => this.summarizeHighlights();
                toolbar.prepend(sumBtn);
            }
            // CSV button already exists in HTML toolbar — no dynamic injection needed
        }

        if (this.snippets.length === 0) {
            snippetList.innerHTML = `<div class="dock-empty">Select text and click 📌 DOCK to collect research</div>`;
            return;
        }

        snippetList.innerHTML = this.snippets.map(s => `
            <div class="dock-snippet" data-id="${s.id}" data-type="${s.type}">
                <div class="snippet-header">
                    <span class="snippet-icon">${s.icon}</span>
                    <span class="snippet-label">${s.label}</span>
                    <div class="snippet-actions">
                        <button onclick="ResearchDock.copy('${s.id}')" title="Copy">📋</button>
                        ${['data', 'csv', 'table'].includes(s.type) ? `
                            <button onclick="ResearchDock.generateChart('${s.id}', 'pie')" title="Pie Chart">🥧</button>
                            <button onclick="ResearchDock.generateChart('${s.id}', 'line')" title="Line Chart">📈</button>
                        ` : ''}
                        ${s.type !== 'mermaid' ? `
                            <button onclick="ResearchDock.generateChart('${s.id}', 'mermaid')" title="Diagram">🔀</button>
                        ` : ''}
                        <button onclick="ResearchDock.remove('${s.id}')" title="Remove">✕</button>
                    </div>
                </div>
                <div class="snippet-preview">${this.escapeHtml(s.preview)}</div>
                
                <div class="snippet-tags">
                    ${(s.tags || []).map(t => `
                        <span class="tag-chip">
                            ${t} <span class="tag-close" onclick="ResearchDock.removeTag('${s.id}', '${t}')">×</span>
                        </span>
                    `).join('')}
                    <input type="text" class="tag-add-input" placeholder="+ Tag" 
                        onkeypress="if(event.key === 'Enter') { ResearchDock.addTag('${s.id}', this.value); this.value=''; }">
                </div>
            </div>
        `).join('');

        // Update counter
        const counter = container.querySelector('.dock-count');
        if (counter) counter.textContent = this.snippets.length;
    },

    // HTML escape helper
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    // Save to localStorage AND Backend
    async save() {
        try {
            // Local fallback
            localStorage.setItem('korum-dock', JSON.stringify(this.snippets));

            // Mission 2: Backend Sync
            await authFetch('/api/dock/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ snippets: this.snippets })
            });

        } catch (e) {
            console.warn('Could not save dock fully', e);
        }
    },

    // Load from Backend OR localStorage
    async load() {
        try {
            // Try backend first
            const response = await authFetch('/api/dock/load');
            const data = await response.json();

            if (data.success && data.snippets && data.snippets.length > 0) {
                this.snippets = data.snippets.map(s => ({
                    ...s,
                    timestamp: new Date(s.timestamp)
                }));
                console.log("📂 Dock loaded from Mission Intelligence Cloud");
            } else {
                // Fallback to local
                const saved = localStorage.getItem('korum-dock');
                if (saved) {
                    this.snippets = JSON.parse(saved).map(s => ({
                        ...s,
                        timestamp: new Date(s.timestamp)
                    }));
                }
            }
        } catch (e) {
            console.warn('Could not load dock from backend, falling back to local', e);
            const saved = localStorage.getItem('korum-dock');
            if (saved) {
                this.snippets = JSON.parse(saved).map(s => ({
                    ...s,
                    timestamp: new Date(s.timestamp)
                }));
            }
        }
    },

    // Initialize dock
    async init() {
        await this.load();
        this.render();
        logTelemetry("Research Dock: ONLINE [Cloud-Sync Active]", "success");
    }
};

// Make globally available
window.ResearchDock = ResearchDock;

// Toggle between Chat and Dock modes
window.toggleCommsMode = function (mode) {
    const chatPanel = document.getElementById('commsChatPanel');
    const dockPanel = document.getElementById('researchDock');
    const tabs = document.querySelectorAll('.comms-tab');

    tabs.forEach(t => t.classList.remove('active'));
    document.querySelector(`.comms-tab[data-comms-mode="${mode}"]`)?.classList.add('active');

    if (mode === 'chat') {
        chatPanel?.classList.add('active');
        dockPanel?.classList.remove('active');
    } else {
        chatPanel?.classList.remove('active');
        dockPanel?.classList.add('active');
        ResearchDock.render(); // Refresh dock view
    }
};

// Dock selected text
window.dockSelection = function () {
    const selection = window.getSelection().toString();
    if (!selection || selection.trim().length < 3) {
        showProcessingToast("Select more text to dock");
        return;
    }

    document.getElementById('interrogation-tooltip').style.display = 'none';

    // Add to dock
    const snippet = ResearchDock.add(selection, 'selection');

    if (snippet) {
        showProcessingToast(`${snippet.icon} ${snippet.label} docked!`);

        // Auto-switch to dock view if first snippet
        if (ResearchDock.snippets.length === 1) {
            toggleCommsMode('dock');
        }

        // Update dock counter badge
        const counter = document.querySelector('.dock-count');
        if (counter) counter.textContent = ResearchDock.snippets.length;
    }
};

// === AI HEALTH MONITORING SYSTEM ===
const AIHealth = {
    // Status: 'healthy' | 'warning' | 'error' | 'offline'
    status: {
        openai: { state: 'healthy', lastCheck: null, failures: 0, lastError: null },
        anthropic: { state: 'healthy', lastCheck: null, failures: 0, lastError: null },
        google: { state: 'healthy', lastCheck: null, failures: 0, lastError: null },
        perplexity: { state: 'healthy', lastCheck: null, failures: 0, lastError: null },
        mistral: { state: 'healthy', lastCheck: null, failures: 0, lastError: null },
        local: { state: 'healthy', lastCheck: null, failures: 0, lastError: null }
    },

    // Update card UI based on health status
    updateCardUI(provider) {
        const card = document.querySelector(`.deck-card.${provider}`);
        if (!card) return;

        const status = this.status[provider];
        card.classList.remove('status-warning', 'status-error', 'status-offline');

        if (status.state === 'warning') {
            card.classList.add('status-warning');
        } else if (status.state === 'error') {
            card.classList.add('status-error');
        } else if (status.state === 'offline') {
            card.classList.add('status-offline');
        }

        if (status.state === 'offline') {
            card.title = `${provider.toUpperCase()} - Offline`;
        } else if (status.lastError) {
            card.title = `${provider.toUpperCase()}: ${status.lastError}`;
        } else {
            card.title = `${provider.toUpperCase()} - Online`;
        }
    },

    // Mark AI as responding (pulse animation)
    setResponding(provider, isResponding) {
        const card = document.querySelector(`.deck-card.${provider}`);
        if (card) {
            isResponding ? card.classList.add('responding') : card.classList.remove('responding');
        }
    },

    // Record success - reset failure count
    recordSuccess(provider) {
        const status = this.status[provider];
        status.state = 'healthy';
        status.failures = 0;
        status.lastCheck = Date.now();
        status.lastError = null;
        this.updateCardUI(provider);
    },

    // Record failure - increment counter, circuit breaker at 3
    recordFailure(provider, errorMsg) {
        const status = this.status[provider];
        status.failures++;
        status.lastCheck = Date.now();
        status.lastError = errorMsg;

        if (status.failures >= 3) {
            status.state = 'offline';
            logTelemetry(`${provider.toUpperCase()}: OFFLINE (circuit breaker)`, "error");
        } else if (status.failures >= 2) {
            status.state = 'error';
            logTelemetry(`${provider.toUpperCase()}: ${errorMsg}`, "error");
        } else {
            status.state = 'warning';
            logTelemetry(`${provider.toUpperCase()}: ${errorMsg}`, "warning");
        }
        this.updateCardUI(provider);
    },

    // Check if provider is available
    isAvailable(provider) {
        return this.status[provider].state !== 'offline';
    },

    // Initialize all card UIs
    init() {
        Object.keys(this.status).forEach(p => this.updateCardUI(p));
        logTelemetry("Health Monitor: ACTIVE", "success");
    }
};

const PROTOCOL_CONFIGS = {
    // --- GENERAL ---
    "War Room": { openai: "strategist", anthropic: "containment", google: "takeover", perplexity: "scout", mistral: "analyst" },
    "Deep Research": { openai: "analyst", anthropic: "researcher", google: "historian", perplexity: "scout", mistral: "validator" },
    "Creative Council": { openai: "writer", anthropic: "innovator", google: "marketing", perplexity: "social", mistral: "creative" },
    "Code Audit": { openai: "architect", anthropic: "integrity", google: "hacker", perplexity: "optimizer", mistral: "coding" },
    "System Core": { openai: "visionary", anthropic: "architect", google: "critic", perplexity: "researcher", mistral: "analyst" },
    // --- DOMAIN-SPECIFIC ---
    "Legal Review": { openai: "jurist", anthropic: "compliance", google: "critic", perplexity: "scout", mistral: "negotiator" },
    "Medical Council": { openai: "medical", anthropic: "bioethicist", google: "researcher", perplexity: "scout", mistral: "analyst" },
    "Finance Desk": { openai: "cfo", anthropic: "auditor", google: "hedge_fund", perplexity: "scout", mistral: "tax" },
    "Science Panel": { openai: "physicist", anthropic: "biologist", google: "chemist", perplexity: "scout", mistral: "professor" },
    "Startup Launch": { openai: "bizstrat", anthropic: "product", google: "marketing", perplexity: "scout", mistral: "cfo" },
    "Tech Council": { openai: "strategist", anthropic: "analyst", google: "researcher", perplexity: "scout", mistral: "critic" },
    // --- DEFENSE & INTELLIGENCE ---
    "Defense Council": { openai: "defense_ops", anthropic: "cyber_ops", google: "intel_analyst", perplexity: "scout", mistral: "hacker" },
    "Cyber Command": { openai: "cyber_ops", anthropic: "counterintel", google: "sigint", perplexity: "intel_analyst", mistral: "hacker" },
    "Quantum Security": { openai: "zero_trust", anthropic: "cryptographer", google: "compliance", perplexity: "ai_architect", mistral: "hacker" },
    "Intel Brief": { openai: "intel_analyst", anthropic: "counterintel", google: "defense_ops", perplexity: "scout", mistral: "sigint" }
};

// Available Roles for Manual Cycling
const AVAILABLE_ROLES = {
    openai: ["STRATEGIST", "ANALYST", "WRITER", "ARCHITECT", "VISIONARY", "JURIST", "MEDICAL", "CFO", "PHYSICIST", "BIZSTRAT", "AI_ARCHITECT", "NETWORK", "HEDGE_FUND", "DEFENSE_OPS", "CYBER_OPS", "INTEL_ANALYST", "DEFENSE_ACQ", "CRYPTOGRAPHER", "ZERO_TRUST"],
    anthropic: ["CONTAINMENT", "RESEARCHER", "INNOVATOR", "INTEGRITY", "ARCHITECT", "COMPLIANCE", "BIOETHICIST", "AUDITOR", "BIOLOGIST", "PRODUCT", "NETWORK", "TELECOM", "HEDGE_FUND", "CYBER_OPS", "COUNTERINTEL", "INTEL_ANALYST", "DEFENSE_ACQ", "CRYPTOGRAPHER", "ZERO_TRUST"],
    google: ["TAKEOVER", "HISTORIAN", "MARKETING", "HACKER", "CRITIC", "ECONOMIST", "CHEMIST", "RESEARCHER", "NETWORK", "TELECOM", "HEDGE_FUND", "DEFENSE_OPS", "CYBER_OPS", "SIGINT", "INTEL_ANALYST", "CRYPTOGRAPHER", "ZERO_TRUST"],
    perplexity: ["SCOUT", "SOCIAL", "OPTIMIZER", "RESEARCHER", "INTEL_ANALYST"],
    mistral: ["ANALYST", "STRATEGIST", "CODING", "CREATIVE", "VALIDATOR", "NEGOTIATOR", "TAX", "PROFESSOR", "CFO", "WEB_DESIGNER", "HACKER", "HEDGE_FUND", "CYBER_OPS", "DEFENSE_OPS", "SIGINT", "CRYPTOGRAPHER", "ZERO_TRUST"],
    local: ["ORACLE", "GUARDIAN", "OFFLINE"]
};

let activeSelection = "";
let customRolesActive = false;
let actionBindingsInitialized = false;

// --- AGENT DECK LOGIC ---
function cycleRole(provider, event) {
    if (event) event.stopPropagation();

    // If clicking the X button, toggle silenced — handled separately
    if (event && event.target.classList.contains('deck-x')) return;

    const card = document.querySelector(`.deck-card.${provider}`);

    // If silenced, clicking the card body re-enables it
    if (card?.classList.contains('silenced')) {
        card.classList.remove('silenced');
        logTelemetry(`${provider.toUpperCase()} ACTIVATED`, "success");
        return;
    }

    // Card body click = cycle persona
    const label = document.getElementById(`roleLabel-${provider}`);
    if (!label) return;

    const current = label.innerText;
    const roles = AVAILABLE_ROLES[provider];
    const nextIndex = (roles.indexOf(current) + 1) % roles.length;

    label.innerText = roles[nextIndex];
    customRolesActive = true;

    // Visual Feedback
    if (card) {
        card.classList.add('active');
        setTimeout(() => card.classList.remove('active'), 200);
    }
}

// X button: toggle provider off/on
function toggleProvider(provider) {
    const card = document.querySelector(`.deck-card.${provider}`);
    if (!card) return;

    if (card.classList.contains('silenced')) {
        card.classList.remove('silenced');
        logTelemetry(`${provider.toUpperCase()} ACTIVATED`, "success");
    } else {
        card.classList.add('silenced');
        logTelemetry(`${provider.toUpperCase()} SILENCED`, "system");
    }
}

// --- MODE SELECTION ---
const activeModes = { v2: true, red: false, serp: false };

function toggleMode(mode) {
    const btn = document.getElementById(`btn-mode-${mode}`);
    if (!btn) return;

    activeModes[mode] = !activeModes[mode];
    const isActive = activeModes[mode];

    btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    btn.classList.toggle('mode-active-v2', mode === 'v2' && isActive);
    btn.classList.toggle('mode-active-red', mode === 'red' && isActive);
    btn.classList.toggle('mode-active-serp', mode === 'serp' && isActive);

    if (isActive) {
        btn.classList.add('active');
        logTelemetry(`${mode.toUpperCase()} MODE ACTIVATED`, "warning");
    } else {
        btn.classList.remove('active');
        logTelemetry(`${mode.toUpperCase()} MODE STANDBY`, "system");
    }
}

// Query pattern detection for smart suggestions
const QUERY_PATTERNS = {
    "War Room": ["crisis", "threat", "emergency", "attack", "vulnerability", "breach", "defend", "strategy", "takeover", "hostile"],
    "Deep Research": ["research", "study", "analyze", "investigate", "explain", "how does", "what is", "history", "scientific", "academic"],
    "Creative Council": ["creative", "design", "write", "story", "marketing", "campaign", "brand", "innovative", "idea", "concept"],
    "Code Audit": ["code", "bug", "debug", "security", "vulnerability", "review", "refactor", "optimize", "performance", "architecture"],
    "Tech Council": ["technology", "infrastructure", "cloud", "devops", "api", "database", "server", "deploy", "saas", "platform", "software", "hardware", "ai", "machine learning", "automation", "integration", "microservice", "kubernetes", "docker", "telecom", "fiber", "wireless", "5g", "bandwidth", "latency", "dns", "cisco", "aws", "azure"],
    "Legal Review": ["legal", "law", "regulation", "compliance", "contract", "liability", "patent", "trademark", "lawsuit", "attorney"],
    "Medical Council": ["medical", "health", "clinical", "patient", "diagnosis", "treatment", "pharmaceutical", "disease", "therapy", "doctor"],
    "Finance Desk": ["finance", "investment", "revenue", "profit", "accounting", "tax", "budget", "portfolio", "stock", "dividend", "roi", "hedge fund", "arbitrage", "equity"],
    "Science Panel": ["science", "physics", "chemistry", "biology", "experiment", "hypothesis", "quantum", "molecular", "genetic", "laboratory"],
    "Startup Launch": ["startup", "launch", "business plan", "mvp", "funding", "venture", "pitch", "scalable", "bootstrap", "market fit"],
    "Defense Council": ["drone", "uav", "uas", "military", "dod", "defense", "pentagon", "nato", "warfare", "missile", "isr", "reconnaissance", "counter-uas", "autonomous weapon", "force projection", "combat", "battalion", "tactical", "operational", "classified", "clearance", "fedramp"],
    "Cyber Command": ["cyber attack", "ransomware", "malware", "zero day", "apt", "threat actor", "incident response", "soc", "nist", "cmmc", "penetration test", "red team", "blue team", "exploit", "phishing", "darknet", "cve", "vulnerability scan", "firewall rule", "ids", "ips", "siem", "encryption", "cryptograph", "zero trust", "pki", "tls", "ssl", "aes", "rsa", "post-quantum", "key management", "micro-segmentation", "least privilege", "cyber intrusion", "reconnaissance activity", "access credentials", "network", "firewall", "vpn", "routing"],
    "Quantum Security": ["post-quantum", "quantum computing", "harvest now decrypt later", "lattice-based", "kyber", "dilithium", "pqc", "cryptographic agility", "quantum-resistant", "quantum-safe", "nist pqc", "fedramp", "cmmc", "zero trust architecture", "micro-segmentation", "sase", "sse"],
    "Intel Brief": ["intelligence", "osint", "sigint", "humint", "geopolitical", "adversary", "threat assessment", "espionage", "counterintelligence", "national security", "classified", "briefing", "surveillance", "reconnaissance", "entity", "encrypted communication", "shell organization", "financial transfer", "logistics movement", "satellite monitoring", "coordinated operation", "deception", "false flag", "operational chain", "threat scenario", "intrusion group", "redacted"],
    "System Core": ["general", "help", "question", "advice"]
};

function analyzeQuery(query) {
    const lowerQuery = query.toLowerCase();
    let maxMatches = 0;
    let bestWorkflow = "System Core";

    for (const [workflow, keywords] of Object.entries(QUERY_PATTERNS)) {
        const matches = keywords.filter(kw => lowerQuery.includes(kw)).length;
        if (matches > maxMatches) {
            maxMatches = matches;
            bestWorkflow = workflow;
        }
    }

    return bestWorkflow;
}

function initViz() {
    positionNodes();
    setupInterrogation();

    document.querySelectorAll('.node').forEach(n => {
        n.classList.add('selected');
        n.style.opacity = 1;
    });

    setInterval(pushHeartbeat, 4000);
    logTelemetry("System Initialized.", "system");
    logTelemetry("Neural Link: ESTABLISHED", "system");
}

function positionNodes() {
    const nodes = document.querySelectorAll(".node"); if (!nodes.length) return;
    const radius = 220;
    nodes.forEach((node, i) => {
        const angleRad = (i / nodes.length) * 2 * Math.PI;
        const x = radius * Math.cos(angleRad); const y = radius * Math.sin(angleRad);

        // Important: Include the centering translation so the node center aligns with the point
        node.style.transform = `translate(-50%, -50%) translate(${x}px, ${y}px)`;

        // Store angle for beam calculations if needed
        node.style.setProperty('--angle-offset', `${(angleRad * 180 / Math.PI) + 180}deg`);
    });
}

function setupActionBindings() {
    if (actionBindingsInitialized) return;
    actionBindingsInitialized = true;

    // 1. NAVIGATION & PROTOCOLS
    const navLinks = document.querySelectorAll('.nav-links a');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
            const role = link.dataset.role;
            const config = PROTOCOL_CONFIGS[role];
            if (config) {
                document.getElementById('roleLabel-openai').innerText = config.openai.toUpperCase();
                document.getElementById('roleLabel-anthropic').innerText = config.anthropic.toUpperCase();
                document.getElementById('roleLabel-google').innerText = config.google.toUpperCase();
                document.getElementById('roleLabel-perplexity').innerText = config.perplexity.toUpperCase();
                if (config.mistral) document.getElementById('roleLabel-mistral').innerText = config.mistral.toUpperCase();
                customRolesActive = false;
            }
            logTelemetry(`Protocol Switched: ${role.toUpperCase()}`, "process");
        });
    });

    // 2. INPUT HANDLING & SUGGESTIONS
    const queryInput = document.getElementById('queryInput');
    const suggestionBox = document.getElementById('suggestionBox');
    const roleCustomization = document.getElementById('roleCustomization');
    let suggestionTimeout;

    queryInput?.addEventListener('input', (e) => {
        const query = e.target.value.trim();
        clearTimeout(suggestionTimeout);
        if (query.length > 20) {
            suggestionTimeout = setTimeout(() => {
                const suggestedWorkflow = analyzeQuery(query);
                const suggestedRoles = PROTOCOL_CONFIGS[suggestedWorkflow];
                const detCat = document.getElementById('detectedCategory');
                const sugWf = document.getElementById('suggestedWorkflow');
                if (detCat) detCat.textContent = suggestedWorkflow;
                if (sugWf) sugWf.textContent = suggestedWorkflow;
                if (suggestionBox) suggestionBox.classList.remove('hidden');
                if (suggestedRoles) {
                    document.getElementById('roleSelectOpenAI').value = suggestedRoles.openai;
                    document.getElementById('roleSelectAnthropic').value = suggestedRoles.anthropic;
                    document.getElementById('roleSelectGoogle').value = suggestedRoles.google;
                    document.getElementById('roleSelectPerplexity').value = suggestedRoles.perplexity;
                }
                logTelemetry(`Query Analyzed: ${suggestedWorkflow}`, "process");
            }, 800);
        } else {
            if (suggestionBox) suggestionBox.classList.add('hidden');
            if (roleCustomization) roleCustomization.classList.add('hidden');
        }
    });

    queryInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            document.querySelector('.trigger-scan')?.click();
        }
    });

    // 3. ACTION BUTTONS
    document.getElementById('useSuggestedBtn')?.addEventListener('click', () => {
        const sugWfEl = document.getElementById('suggestedWorkflow');
        const targetTab = document.querySelector(`.nav-links a[data-role="${sugWfEl ? sugWfEl.textContent : ''}"]`);
        if (targetTab) targetTab.click();
        if (suggestionBox) suggestionBox.classList.add('hidden');
        if (roleCustomization) roleCustomization.classList.add('hidden');
        customRolesActive = false;
    });

    document.getElementById('customizeBtn')?.addEventListener('click', () => {
        if (roleCustomization) roleCustomization.classList.toggle('hidden');
        customRolesActive = !customRolesActive;
    });

    document.getElementById('dismissSuggestionBtn')?.addEventListener('click', () => {
        if (suggestionBox) suggestionBox.classList.add('hidden');
        if (roleCustomization) roleCustomization.classList.add('hidden');
    });

    document.getElementById('clearInputBtn')?.addEventListener('click', () => {
        if (queryInput) queryInput.value = '';
        logTelemetry("Input Cleared", "system");
    });

    // 4. ROSTER & MODES
    document.querySelectorAll('.deck-card[data-provider]').forEach(card => {
        const provider = card.dataset.provider;
        const run = (e) => cycleRole(provider, e);
        card.addEventListener('click', run);
        card.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); run(e); } });
    });

    // X buttons on deck cards — toggle provider on/off
    document.querySelectorAll('.deck-x[data-provider]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleProvider(btn.dataset.provider);
        });
    });

    document.querySelectorAll('[data-mode-toggle]').forEach(btn => {
        btn.addEventListener('click', () => toggleMode(btn.dataset.modeToggle));
    });

    document.querySelectorAll('[data-comms-mode]').forEach(btn => {
        btn.addEventListener('click', () => toggleCommsMode(btn.dataset.commsMode));
    });

    document.querySelectorAll('[data-dock-action]').forEach(btn => {
        btn.addEventListener('click', () => {
            const action = btn.dataset.dockAction;
            if (action === 'export-markdown') ResearchDock.exportAll('markdown');
            if (action === 'export-csv') ResearchDock.exportAll('csv');
            if (action === 'clear') ResearchDock.clear();
        });
    });

    // 5. SYSTEM CONTROLS
    document.getElementById('hamburgerBtn')?.addEventListener('click', () => toggleReportLibrary());

    // Mobile nav toggle
    document.getElementById('mobileNavToggle')?.addEventListener('click', () => {
        document.querySelector('.nav-links')?.classList.toggle('mobile-open');
    });
    // Close mobile nav when a workflow is selected
    document.querySelectorAll('.nav-links a').forEach(a => {
        a.addEventListener('click', () => {
            document.querySelector('.nav-links')?.classList.remove('mobile-open');
        });
    });
    // Close mobile nav on tap outside
    document.addEventListener('click', (e) => {
        const nav = document.querySelector('.nav-links');
        const toggle = document.getElementById('mobileNavToggle');
        if (nav?.classList.contains('mobile-open') && !nav.contains(e.target) && !toggle?.contains(e.target)) {
            nav.classList.remove('mobile-open');
        }
    });
    document.getElementById('healthCheckBtn')?.addEventListener('click', () => checkAPIHealth());
    document.getElementById('rotateRolesBtn')?.addEventListener('click', () => {
        rotateRoles();
        logTelemetry("Council Roles Rotated", "process");
    });

    document.querySelector('.trigger-scan')?.addEventListener('click', () => {
        const query = queryInput?.value.trim();
        if (!query) { alert("Protocol Violation: Query Required."); return; }
        if (!sessionState.isMissionLocked) { openIntakeModal(); return; }
        triggerCouncil(query);
    });

    document.querySelector('.close-results')?.addEventListener('click', closeResults);

    // Mission intake modal controls
    document.getElementById('intakeConfirmBtn')?.addEventListener('click', lockMissionContext);
    document.getElementById('intakeCancelBtn')?.addEventListener('click', () => {
        closeIntakeModal();
        sessionState.isMissionLocked = true; // Skip mission lock
        const query = document.getElementById('queryInput')?.value?.trim();
        if (query) triggerCouncil(query);
    });
    document.getElementById('intakeModal')?.addEventListener('click', (e) => {
        if (e.target?.id === 'intakeModal') closeIntakeModal();
    });

    // 6. COLLECTIONS & EXPORTS
    document.getElementById('attachBtn')?.addEventListener('click', () => document.getElementById('fileInput')?.click());
    document.getElementById('fileInput')?.addEventListener('change', (e) => { addFiles(e.target.files); e.target.value = ''; });

    const recallBtn = document.getElementById('recallAnalysisBtn');
    if (recallBtn) {
        recallBtn.addEventListener('click', () => {
            document.querySelector(".results-container").classList.add("visible");
            recallBtn.style.display = 'none';
        });
    }

    // 7. CONSOLE & INTERROGATION
    const consoleInput = document.getElementById("consoleInput");
    const consoleSubmit = document.getElementById("consoleSubmitBtn");
    if (consoleInput && consoleSubmit) {
        const sendCmd = () => {
            const cmd = consoleInput.value.trim();
            if (cmd) {
                let contextualQuery = cmd;
                if (sessionState.originalQuery) {
                    const targetResponse = sessionState.targetCard ? sessionState.lastResponses[sessionState.targetCard] : Object.values(sessionState.lastResponses).join("\n---\n").substring(0, 2000);
                    contextualQuery = `ORIGINAL TOPIC: ${sessionState.originalQuery}\n\nCONTEXT (THE RESPONSE BEING CHALLENGED):\n${targetResponse.substring(0, 1500)}...\n\nUSER CHALLENGE:\n${cmd}\n\nINSTRUCTIONS: Address the challenge directly. Do NOT lose the context of the ORIGINAL TOPIC.`.trim();
                }
                logTelemetry(`Interrogation: ${cmd}`, "user");
                triggerCouncil(contextualQuery);
                consoleInput.value = "";
            }
        };
        consoleInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendCmd(); });
        consoleSubmit.addEventListener('click', sendCmd);
    }

    // 8. DYNAMIC RESULTS DELEGATION
    document.querySelector('.results-content')?.addEventListener('click', (e) => {
        const target = e.target;
        const cardAction = target.closest('[data-card-action]');
        if (cardAction) {
            e.stopPropagation();
            const action = cardAction.dataset.cardAction;
            const agentCard = cardAction.closest('.agent-card');
            if (!agentCard) return;
            const data = agentCard.dataset;

            if (action === 'interrogate') openInterrogation(data.name);
            if (action === 'save') saveReport();
            if (action === 'visualize') window.visualizeSelection(decodeURIComponent(data.rawContent));
            if (action === 'copy') copyTextToClipboard(decodeURIComponent(data.rawContent), 'Phase intelligence copied');
            return;
        }

        const agentCard = target.closest('.agent-card');
        if (agentCard && !agentCard.classList.contains('no-interrogate') && !target.closest('button') && !target.closest('.tool-action')) {
            const data = agentCard.dataset;
            openCardModal({
                name: data.name || 'Response',
                meta: data.meta || '',
                content: agentCard.querySelector('.agent-response')?.innerHTML
            });
        }
    });
}

function rotateRoles() {
    const selects = document.querySelectorAll('.role-select');
    selects.forEach(select => {
        const options = Array.from(select.options);
        const currentIndex = select.selectedIndex;
        const nextIndex = (currentIndex + 1) % options.length;
        select.selectedIndex = nextIndex;
    });
    customRolesActive = true;
}

// function updateSystemStatus removed (consolidated below)

async function triggerCouncil(query) {
    // --- EXECUTE PROTOCOL BUTTON FEEDBACK ---
    const execBtn = document.querySelector('.trigger-scan');
    if (execBtn) {
        execBtn.classList.add('loading');
        execBtn.textContent = 'PROCESSING...';
        execBtn.disabled = true;
    }

    // Store original query for display
    sessionState.originalQuery = query;

    // Use Context Injection
    const contextQuery = injectMissionContext(query);
    lastQueryText = contextQuery;

    const activeRoleName = document.querySelector('.nav-links a.active')?.dataset.role || 'System Core';

    // --- 2. ACTIVATION ---
    document.body.classList.add("activated");

    // Show Active Agent Card (Starting with System/Planner)
    const activeCard = document.getElementById("activeAgentCard");
    const activeAvatar = document.getElementById("activeAgentAvatar");
    const activeName = document.getElementById("activeAgentName");

    if (activeCard) {
        activeCard.classList.add("visible");
        // Default to System while planning
        activeCard.setAttribute("data-provider", "mistral"); // Use neutral/mistral color for system
        if (activeAvatar) activeAvatar.innerText = "SYS";
        if (activeName) activeName.innerText = "ORCHESTRATING...";
    }

    // Trigger globe animation (speed up)
    const globe = document.querySelector(".globe");
    if (globe) globe.classList.add("processing");

    // --- 3. SEND TO API --- updateSystemStatus("PROCESSING");

    animateActivation();
    startProcessingLogs();

    const isV2 = document.getElementById('v2Toggle')?.checked;

    try {
        if (isV2) {
            // V2 Functional Pipeline
            updateSystemStatus("EXECUTING CHAIN");
            await executeReasoningChain(query);
        } else {
            // V1 Council Mode
            await executeCouncil(query, activeRoleName);
        }
    } catch (error) {
        console.error(error); showErrorCard(error.message); logTelemetry(`ERROR: ${error.message}`, "system"); resetUI();
    } finally {
        // Restore Execute Protocol button
        if (execBtn) {
            execBtn.classList.remove('loading');
            execBtn.classList.add('complete');
            execBtn.textContent = 'EXECUTE PROTOCOL';
            execBtn.disabled = false;
            setTimeout(() => execBtn.classList.remove('complete'), 3000);
        }
    }
}

async function executeReasoningChain(query) {
    logTelemetry("Initiating V2 Functional Pipeline...", "system");
    triggerNetworkAnimation(); // FIRE LIGHTNING

    // Check Hacker Toggle
    const hackerMode = document.getElementById('hackerToggle')?.checked || false;

    const payload = {
        query: query,
        depth: "standard",
        hacker_mode: hackerMode,
        workflow: sessionState.missionContext?.workflow || "RESEARCH"
    };

    const response = await authFetch('/api/v2/reasoning_chain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (!response.ok) throw new Error(`HTTP Error ${response.status}`);
    const data = await response.json();

    if (data.success) {
        renderChainResults(data.pipeline_result);
    } else {
        throw new Error(data.error || "Pipeline Failed");
    }
    resetUI();
}

function renderChainResults(result) {
    const container = document.querySelector(".results-content");
    container.innerHTML = "";
    const grid = document.createElement("div");
    grid.className = "results-grid";

    // Helper to create phase cards
    const createCard = (title, model, content, phase, metricData) => {
        const card = document.createElement("div");
        card.className = `agent-card ${model.toLowerCase().includes('gpt') ? 'openai' : model.toLowerCase().includes('claude') ? 'anthropic' : 'google'}`;
        card.dataset.name = title;
        card.dataset.meta = `<div class="agent-meta"><span>${phase}</span><span>${model}</span></div>`;
        card.dataset.rawContent = encodeURIComponent(content);

        // Use centralized formatter
        const formattedRaw = formatV2Content(content, phase);

        const modelToProvider = { 'claude': 'anthropic', 'gpt': 'openai', 'gemini': 'google', 'mistral': 'mistral', 'oracle': 'local' };
        const providerKey = Object.keys(modelToProvider).find(k => model.toLowerCase().includes(k));
        const res = result.results ? result.results[modelToProvider[providerKey]] : null;
        const verifiedClaims = res?.verified_claims || [];
        const truthScore = res?.truth_meter !== undefined ? res.truth_meter : (metricData?.score || 85);

        const displayContent = highlightClaims(formattedRaw, verifiedClaims);
        const cost = metricData?.cost || 0.0000;
        const time = metricData?.time || 0.00;

        card.innerHTML = `
            <div class="precision-header">
                <div class="ph-left">
                    <div class="ph-model-name">${title}</div>
                    <div class="ph-role-label">${model} • ${phase}</div>
                    <div class="ph-truth-container">
                        <div class="truth-score-val" style="color: ${truthScore > 80 ? '#00FF9D' : truthScore > 50 ? '#FFB020' : '#FF4444'}">
                            TRUTH SCORE: ${truthScore}/100
                        </div>
                        <div class="truth-bar-container">
                            <div class="truth-fill" style="width: ${truthScore}%"></div>
                        </div>
                    </div>
                </div>
                <div class="ph-right">
                    <button class="interrogate-btn" data-card-action="interrogate">
                        🔍 INTERROGATE
                    </button>
                    <div class="metric-pill">$${cost.toFixed(4)}</div>
                    <div class="metric-pill time">${time}s</div>
                    <div class="tool-action" data-card-action="save" title="Save">💾</div>
                    <div class="tool-action" data-card-action="visualize" title="Chart">📊</div>
                    <div class="tool-action" data-card-action="copy" title="Copy">📋</div>
                </div>
            </div>
            <div class="agent-response">${displayContent}</div>
        `;
        return card;
    };

    // 1. Deconstruction (Claude)
    grid.appendChild(createCard("PHASE 1: DECONSTRUCTION", "Claude 3.5 Sonnet", result.constraints, "CONSTRAINT ANALYSIS", result.metrics?.deconstruct));

    // 2. Construction (GPT-4o)
    grid.appendChild(createCard("PHASE 2: ARCHITECTURE", "GPT-4o", result.standard_solution, "STANDARD MODEL", result.metrics?.build));

    // 3. Stress Test (Gemini)
    grid.appendChild(createCard("PHASE 3: STRESS TEST", "Gemini 2.5", result.failure_analysis, "FAILURE PHYSICS", result.metrics?.stress));

    // 3.5 Hacker (If active)
    if (result.exploit_poc) {
        grid.appendChild(createCard("PHASE 3.5: RED TEAM", "Gemini Flash", result.exploit_poc, "EXPLOIT GENERATION", result.metrics?.hacker));
    }

    // 4. Execution (GPT-4o) - formerly Synthesis
    grid.appendChild(createCard("PHASE 4: EXECUTION", "GPT-4o General", result.final_artifact, "EXECUTIVE DIRECTIVE", result.metrics?.synthesize));

    container.appendChild(grid);
    document.querySelector(".results-container").classList.add("visible");
    document.getElementById('recallAnalysisBtn').style.display = 'none'; // Hide recall button

    logTelemetry("Pipeline Execution Complete.", "system");

    // Show Command Console
    const cmdConsole = document.getElementById("commandConsole");
    if (cmdConsole) cmdConsole.style.display = "block";

    // RENDER CHARTS
    setTimeout(() => {
        if (window.mermaid) {
            try {
                mermaid.init(undefined, document.querySelectorAll('.mermaid'));
            } catch (e) {
                console.error("Mermaid Render Error:", e);
            }
        }
    }, 500);
}

// --- SESSION STATE (Context Tracking) ---
let sessionState = {
    originalQuery: "",
    lastResponses: {},
    targetCard: null,
    mainMissionData: null,
    isSubTask: false,
    missionContext: null, // Captures Client, Industry, Priority, etc.
    isMissionLocked: false
};

// NOTE: window.onload is defined later in this file after all functions are declared

// Old functions removed to prevent conflicts with new Event Listeners
// window.openInterrogation handled below
// window.submitConsoleCommand replaced by sendCmd

// --- TEXT SELECTION INTERROGATION ---
// --- TEXT SELECTION INTERROGATION (Cleaned Up) ---
// Note: This logic is now handled by setupInterrogation() to avoid duplicates.
// Keeping empty here to override any previous broken implementation if cached.

window.challengeSelection = function () {
    const selection = window.getSelection().toString();
    if (!selection) return;

    document.getElementById('interrogation-tooltip').style.display = 'none';

    // Show processing feedback
    logTelemetry("CHALLENGING SELECTION...", "process");
    showProcessingToast("Verifying claim...");

    // Build challenge query
    const query = `FACT CHECK THIS CLAIM: "${selection}". Verify accuracy, identify potential errors or hallucinations, and provide supporting or contradicting evidence.`;

    // Trigger the council to verify
    triggerCouncil(query);
};

window.openInterrogation = function (targetName) {
    // Auto-close the card modal so user can see interrogation running
    closeCardModal();
    // Resolve provider key using shared map
    const providerKey = resolveProviderKey(targetName);
    sessionState.targetCard = providerKey;

    // Get defender's role from the deck labels
    const defenderRole = providerKey
        ? (document.getElementById(`roleLabel-${providerKey}`)?.innerText.toLowerCase() || 'analyst')
        : 'analyst';

    // Get target response text — fall back to first available if key not matched
    let targetResponse = providerKey ? sessionState.lastResponses[providerKey] : '';
    if (!targetResponse) {
        const fallback = Object.entries(sessionState.lastResponses).find(([k, v]) => v);
        if (fallback) {
            targetResponse = fallback[1];
            sessionState.targetCard = fallback[0];
        } else {
            showProcessingToast("No response to interrogate.");
            return;
        }
    }

    // Show adversarial persona picker
    showInterrogationPicker(targetName, defenderRole, targetResponse);
};

// ── ADVERSARIAL FACE-OFF PICKER ──────────────────────────────────────────
function showInterrogationPicker(targetName, defenderRole, targetResponse) {
    // Remove any existing picker
    document.getElementById('interrogation-picker')?.remove();

    // Smart attacker suggestions based on defender role
    const attackerSuggestions = {
        'cryptographer': ['hacker', 'physicist', 'zero_trust'],
        'hacker': ['cryptographer', 'zero_trust', 'counterintel'],
        'architect': ['critic', 'hacker', 'auditor'],
        'strategist': ['critic', 'takeover', 'economist'],
        'analyst': ['hacker', 'critic', 'auditor'],
        'critic': ['architect', 'innovator', 'visionary'],
        'scout': ['counterintel', 'analyst', 'critic'],
        'cfo': ['auditor', 'tax', 'hedge_fund'],
        'jurist': ['compliance', 'bioethicist', 'critic'],
        'coding': ['hacker', 'ai_architect', 'architect'],
        'medical': ['biologist', 'bioethicist', 'chemist'],
        'cyber_ops': ['hacker', 'counterintel', 'zero_trust'],
        'defense_ops': ['intel_analyst', 'counterintel', 'strategist'],
    };

    const suggested = attackerSuggestions[defenderRole] || ['hacker', 'critic', 'auditor'];
    const allAttackers = ['hacker', 'critic', 'auditor', 'cryptographer', 'counterintel', 'zero_trust',
        'physicist', 'jurist', 'economist', 'takeover', 'intel_analyst', 'cyber_ops', 'validator'];

    const picker = document.createElement('div');
    picker.id = 'interrogation-picker';
    picker.style.cssText = `
        position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
        background: rgba(10, 10, 15, 0.97); border: 1px solid rgba(255, 68, 68, 0.6);
        border-radius: 6px; padding: 20px 24px; z-index: 10000; min-width: 340px;
        box-shadow: 0 0 40px rgba(255, 68, 68, 0.15); font-family: var(--font-tactical, 'Courier New', monospace);
    `;

    picker.innerHTML = `
        <div style="color: #FF4444; font-size: 0.7rem; letter-spacing: 0.15em; margin-bottom: 12px;">
            ⚔️ ADVERSARIAL FACE-OFF
        </div>
        <div style="color: #888; font-size: 0.6rem; margin-bottom: 14px;">
            TARGET: <span style="color: #FF8888">${targetName.toUpperCase()}</span>
            &nbsp;·&nbsp; ROLE: <span style="color: #FFB020">${defenderRole.toUpperCase()}</span>
        </div>
        <div style="color: #AAA; font-size: 0.6rem; letter-spacing: 0.1em; margin-bottom: 8px;">SELECT ATTACKER:</div>
        <div id="attacker-grid" style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px;">
            ${suggested.map(role => `
                <button class="attacker-pick suggested" data-role="${role}" style="
                    background: rgba(255,68,68,0.12); border: 1px solid rgba(255,68,68,0.5);
                    color: #FF8888; padding: 5px 10px; border-radius: 3px; cursor: pointer;
                    font-family: inherit; font-size: 0.6rem; letter-spacing: 0.08em;
                    transition: all 0.15s;
                ">${role.replace(/_/g, ' ').toUpperCase()}</button>
            `).join('')}
        </div>
        <details style="margin-bottom: 14px;">
            <summary style="color: #666; font-size: 0.55rem; cursor: pointer; letter-spacing: 0.1em;">ALL PERSONAS</summary>
            <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px;">
                ${allAttackers.filter(r => !suggested.includes(r)).map(role => `
                    <button class="attacker-pick" data-role="${role}" style="
                        background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.15);
                        color: #888; padding: 4px 8px; border-radius: 3px; cursor: pointer;
                        font-family: inherit; font-size: 0.55rem; letter-spacing: 0.05em;
                        transition: all 0.15s;
                    ">${role.replace(/_/g, ' ').toUpperCase()}</button>
                `).join('')}
            </div>
        </details>
        <div style="display: flex; gap: 8px;">
            <button id="interrogation-cancel" style="
                flex: 1; background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.2);
                color: #888; padding: 7px; border-radius: 3px; cursor: pointer;
                font-family: inherit; font-size: 0.6rem; letter-spacing: 0.1em;
            ">CANCEL</button>
        </div>
    `;

    document.body.appendChild(picker);

    // Handle attacker selection
    picker.querySelectorAll('.attacker-pick').forEach(btn => {
        btn.addEventListener('mouseenter', () => { btn.style.background = 'rgba(255,68,68,0.25)'; btn.style.color = '#FF4444'; });
        btn.addEventListener('mouseleave', () => { btn.style.background = btn.classList.contains('suggested') ? 'rgba(255,68,68,0.12)' : 'rgba(255,255,255,0.04)'; btn.style.color = btn.classList.contains('suggested') ? '#FF8888' : '#888'; });
        btn.addEventListener('click', () => {
            const attackerRole = btn.dataset.role;
            picker.remove();
            executeInterrogation(attackerRole, defenderRole, targetResponse, targetName);
        });
    });

    // Cancel
    document.getElementById('interrogation-cancel').addEventListener('click', () => picker.remove());

    // ESC to close
    const escHandler = (e) => { if (e.key === 'Escape') { picker.remove(); document.removeEventListener('keydown', escHandler); } };
    document.addEventListener('keydown', escHandler);
}

// ── SCALPEL MODE: SOURCE VERIFICATION ────────────────────────────────────
window.executeVerify = async function (claimText, providerName) {
    // If full response passed, truncate to selected text or first 500 chars
    const selection = window.getSelection()?.toString().trim();
    const claim = selection && selection.length > 10 ? selection : claimText.substring(0, 500);

    logTelemetry(`🔎 VERIFY: "${claim.slice(0, 60)}..."`, "user");
    sentinelChat.appendMessage(`SOURCE CHECK: "${claim.slice(0, 80)}..."`, 'user');

    // Create verification card
    const grid = document.querySelector('.results-content');
    const verifyCard = document.createElement('div');
    verifyCard.className = 'agent-card verify-card no-interrogate';
    verifyCard.dataset.name = 'SOURCE VERIFICATION';
    verifyCard.style.cssText = 'border: 1px solid #00BFFF; background: rgba(0,191,255,0.03); margin-top: 16px;';
    verifyCard.innerHTML = `
        <div class="precision-header" style="border-bottom: 1px solid #00BFFF;">
            <div class="ph-left">
                <div class="ph-model-name" style="color:#00BFFF">🔎 SOURCE VERIFICATION</div>
                <div class="ph-role-label" style="color:#66D9FF">PERPLEXITY · FACT CHECK</div>
            </div>
            <div class="ph-right">
                <div class="metric-pill" style="color:#FFB020; animation: pulse 1.5s infinite;">SEARCHING...</div>
            </div>
        </div>
        <div class="agent-response" style="color:#999; padding: 20px; text-align: center;">
            <div>Querying authoritative sources...</div>
        </div>
    `;
    grid.appendChild(verifyCard);
    verifyCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    try {
        const resp = await authFetch('/api/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                claim: claim,
                original_query: sessionState.originalQuery || '',
            })
        });

        const result = await resp.json();

        if (!result.success) {
            verifyCard.querySelector('.agent-response').innerHTML = `<span style="color:#FF4444">Verification failed: ${result.error || 'Unknown error'}</span>`;
            return;
        }

        const verifiedHtml = formatText(result.verification);
        verifyCard.innerHTML = `
            <div class="precision-header" style="border-bottom: 1px solid #00BFFF;">
                <div class="ph-left">
                    <div class="ph-model-name" style="color:#00BFFF">🔎 SOURCE VERIFICATION</div>
                    <div class="ph-role-label" style="color:#66D9FF">PERPLEXITY · ${result.model || 'sonar'}</div>
                </div>
                <div class="ph-right">
                    <div class="metric-pill" style="color:#00FF9D">COMPLETE</div>
                    <div class="tool-action" onclick="event.stopPropagation(); copyTextToClipboard(this.closest('.agent-card').querySelector('.agent-response').innerText, 'Verification copied')" title="Copy">📋</div>
                </div>
            </div>
            <div style="padding: 12px 16px; border-bottom: 1px solid rgba(0,191,255,0.15);">
                <div style="color:#66D9FF; font-size: 0.6rem; letter-spacing: 0.1em; margin-bottom: 4px;">CLAIM UNDER REVIEW</div>
                <div style="color:#AAA; font-size: 0.75rem; font-style: italic;">"${claim.length > 200 ? claim.substring(0, 200) + '...' : claim}"</div>
            </div>
            <div class="agent-response">${verifiedHtml}</div>
        `;

        sentinelChat.appendMessage(`Source verification complete for: "${claim.slice(0, 50)}..."`, 'sentinel');
        logTelemetry("🔎 Verification complete", "success");

        // === TRUTH SCORE FEEDBACK ===
        const vText = (result.verification || '').toUpperCase();
        const sourceProvider = resolveProviderKey(providerName);
        if (sourceProvider) {
            let delta = 0;
            let verdict = '';
            if (vText.includes('INACCURATE') && !vText.includes('PARTIALLY')) {
                delta = -10; verdict = 'CLAIM INACCURATE';
            } else if (vText.includes('PARTIALLY ACCURATE') || vText.includes('PARTIALLY')) {
                delta = -3; verdict = 'PARTIALLY ACCURATE';
            } else if (vText.includes('ACCURATE') || vText.includes('CONFIRMED') || vText.includes('VERIFIED')) {
                delta = 5; verdict = 'CLAIM VERIFIED';
            }
            if (delta !== 0) {
                updateTruthScore(sourceProvider, delta, verdict);
            }
        }

    } catch (e) {
        console.error('Verify error:', e);
        verifyCard.querySelector('.agent-response').innerHTML = `<span style="color:#FF4444">Verification error: ${e.message}</span>`;
    }
};

// ── EXECUTE ADVERSARIAL INTERROGATION ────────────────────────────────────
async function executeInterrogation(attackerRole, defenderRole, targetResponse, targetName) {
    logTelemetry(`⚔️ ${attackerRole.toUpperCase()} vs ${defenderRole.toUpperCase()}`, "user");
    sentinelChat.appendMessage(`INITIATING FACE-OFF: ${attackerRole.toUpperCase()} vs ${defenderRole.toUpperCase()}`, 'user');

    // Create face-off card
    const grid = document.querySelector('.results-content');
    const faceoffCard = document.createElement('div');
    faceoffCard.className = 'agent-card interrogation-card no-interrogate';
    faceoffCard.dataset.name = `CROSS-EXAMINATION: ${attackerRole.toUpperCase()} vs ${defenderRole.toUpperCase()}`;
    faceoffCard.style.cssText = 'border: 1px solid #FF4444; background: rgba(255,68,68,0.03); margin-top: 16px;';
    faceoffCard.innerHTML = `
        <div class="precision-header" style="border-bottom: 1px solid #FF4444;">
            <div class="ph-left">
                <div class="ph-model-name" style="color:#FF4444">⚔️ CROSS-EXAMINATION</div>
                <div class="ph-role-label" style="color:#FF8888">${attackerRole.replace(/_/g,' ').toUpperCase()} vs ${defenderRole.replace(/_/g,' ').toUpperCase()}</div>
            </div>
            <div class="ph-right">
                <div id="interrogation-heartbeat" class="metric-pill" style="color:#FFB020; animation: pulse 1.5s infinite;">INITIALIZING...</div>
            </div>
        </div>
        <div class="agent-response" style="color:#999; padding: 20px; text-align: center;">
            <div id="heartbeat-text">Consulting NIST 800-207 Policy Engine...</div>
            <div class="loading-bar-min" style="width:100px; height:1px; background:rgba(255,68,68,0.1); margin:10px auto; position:relative; overflow:hidden;">
                <div class="loading-fill-min" style="position:absolute; width:50%; height:100%; background:#FF4444; animation: slide 1s infinite ease-in-out;"></div>
            </div>
        </div>
    `;
    grid.appendChild(faceoffCard);
    faceoffCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    // Reasoning Trace Heartbeats
    const heartbeats = [
        "Consulting NIST 800-207 Policy Engine...",
        "Comparing QANAPI_HASH with known APT signatures...",
        "Running Monte Carlo simulation on Truth Score...",
        "Adversarial logic expansion in progress...",
        "Finalizing tactical dissent..."
    ];
    let hbIdx = 0;
    const hbInterval = setInterval(() => {
        const hbText = document.getElementById('heartbeat-text');
        const hbStatus = document.getElementById('interrogation-heartbeat');
        if (hbText && heartbeats[hbIdx]) {
            hbText.innerText = heartbeats[hbIdx];
            if (hbStatus) hbStatus.innerText = "PROCESSING METADATA...";
            hbIdx++;
        } else {
            clearInterval(hbInterval);
        }
    }, 1500);

    try {
        const resp = await authFetch('/api/interrogate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                original_query: sessionState.originalQuery || '',
                target_response: targetResponse,
                attacker_role: attackerRole,
                defender_role: defenderRole,
            }),
        });

        const result = await resp.json();

        if (!result.success) {
            clearInterval(hbInterval);
            faceoffCard.querySelector('.agent-response').innerHTML = `<span style="color:#FF4444">Interrogation failed: ${result.error || 'Unknown error'}</span>`;
            return;
        }

        clearInterval(hbInterval);

        // Render the face-off transcript
        const attackerHtml = formatText(result.attacker.response);
        const defenderHtml = formatText(result.defender.response);

        faceoffCard.innerHTML = `
            <div class="precision-header" style="border-bottom: 1px solid rgba(255,68,68,0.3);">
                <div class="ph-left">
                    <div class="ph-model-name" style="color:#FF4444">⚔️ CROSS-EXAMINATION COMPLETE</div>
                    <div class="ph-role-label" style="color:#FF8888">
                        ${attackerRole.replace(/_/g,' ').toUpperCase()} (${result.attacker.model}) vs ${defenderRole.replace(/_/g,' ').toUpperCase()} (${result.defender.model})
                    </div>
                </div>
                <div class="ph-right">
                    <div class="tool-action" onclick="event.stopPropagation(); copyTextToClipboard(this.closest('.agent-card').innerText, 'Cross-examination copied')" title="Copy">📋</div>
                </div>
            </div>
            <div style="padding: 12px 16px;">
                <div style="border-left: 3px solid #FF4444; padding: 10px 14px; margin-bottom: 16px; background: rgba(255,68,68,0.04);">
                    <div style="color: #FF4444; font-size: 0.6rem; letter-spacing: 0.12em; margin-bottom: 6px;">
                        🗡️ ATTACKER · ${result.attacker.role_display.toUpperCase()}
                    </div>
                    <div class="agent-response" style="margin: 0;">${attackerHtml}</div>
                </div>
                <div style="border-left: 3px solid #00FF9D; padding: 10px 14px; background: rgba(0,255,157,0.04);">
                    <div style="color: #00FF9D; font-size: 0.6rem; letter-spacing: 0.12em; margin-bottom: 6px;">
                        🛡️ DEFENDER · ${result.defender.role_display.toUpperCase()}
                    </div>
                    <div class="agent-response" style="margin: 0;">${defenderHtml}</div>
                </div>
            </div>
        `;

        sentinelChat.appendMessage(`Cross-examination complete. ${attackerRole.toUpperCase()} challenged ${defenderRole.toUpperCase()}.`, 'sentinel');
        logTelemetry(`Interrogation complete: ${attackerRole} vs ${defenderRole}`, "process");

        // === TRUTH SCORE FEEDBACK ===
        const targetProvider = sessionState.targetCard || resolveProviderKey(targetName);
        if (targetProvider) {
            const defText = (result.defender.response || '').toLowerCase();
            const atkText = (result.attacker.response || '').toLowerCase();
            const concessionWords = ['concede', 'concession', 'acknowledged', 'valid point', 'correctly identifies',
                                     'fair criticism', 'legitimate concern', 'understated', 'overlooked', 'gap in'];
            const strongDefense = ['no evidence', 'unfounded', 'speculative', 'maintains', 'stands firm',
                                   'logic maintained', 'evidence supports', 'rebuttal'];

            const concessions = concessionWords.filter(w => defText.includes(w)).length;
            const holds = strongDefense.filter(w => defText.includes(w) || atkText.includes(w)).length;

            let delta = 0;
            let verdict = '';
            if (concessions >= 3) {
                delta = -15; verdict = `${concessions} CONCESSIONS`;
            } else if (concessions >= 2) {
                delta = -10; verdict = `${concessions} CONCESSIONS`;
            } else if (concessions >= 1) {
                delta = -5; verdict = `${concessions} CONCESSION`;
            } else if (holds >= 2) {
                delta = 3; verdict = 'DEFENSE HELD';
            } else {
                delta = -2; verdict = 'CHALLENGED';
            }
            updateTruthScore(targetProvider, delta, verdict);
        }

    } catch (err) {
        faceoffCard.querySelector('.agent-response').innerHTML = `<span style="color:#FF4444">Network error: ${err.message}</span>`;
        console.error('Interrogation failed:', err);
    }
}

// --- PROMPT REFINEMENT (Enhance) ---
function openEnhanceModal(originalText, enhancedText) {
    const modal = document.getElementById('enhanceModal');
    const originalEl = document.getElementById('enhanceOriginalText');
    const editArea = document.getElementById('enhanceEditArea');
    if (!modal || !originalEl || !editArea) return;

    originalEl.textContent = originalText;
    editArea.value = enhancedText;
    modal.classList.add('visible');

    // Auto-resize textarea to fit content
    setTimeout(() => {
        editArea.style.height = 'auto';
        editArea.style.height = Math.min(editArea.scrollHeight + 4, 300) + 'px';
        editArea.focus();
    }, 100);
}

function closeEnhanceModal() {
    document.getElementById('enhanceModal')?.classList.remove('visible');
}

window.enhancePrompt = async function () {
    const input = document.getElementById('queryInput');
    const btn = document.getElementById('enhanceBtn');
    if (!input || !btn) return;

    const draft = input.value.trim();
    if (!draft) {
        showProcessingToast("Enter a rough draft to enhance.");
        return;
    }

    // Visual Feedback
    btn.classList.add('enhancing');
    const originalIcon = btn.innerHTML;
    btn.innerHTML = `<div class="spinner-sm"></div>`;
    input.style.opacity = '0.5';

    logTelemetry("Optimizing Directive Signal...", "process");

    try {
        const response = await authFetch('/api/enhance_prompt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ draft: draft })
        });

        const data = await response.json();

        if (data.success) {
            logTelemetry(`Directive Optimized (${data.model})`, "success");
            openEnhanceModal(draft, data.enhanced_text);
        } else {
            showProcessingToast("Enhancement Failed: " + (data.error || "Unknown"));
        }
    } catch (e) {
        console.error(e);
        showProcessingToast("Network Error during Enhancement.");
    } finally {
        btn.classList.remove('enhancing');
        btn.innerHTML = originalIcon;
        input.style.opacity = '1';
    }
};

// Bind Enhancement Button + Modal Controls
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('enhanceBtn')?.addEventListener('click', window.enhancePrompt);

    // Accept: deploy enhanced text to prompt box
    document.getElementById('enhanceAcceptBtn')?.addEventListener('click', () => {
        const editArea = document.getElementById('enhanceEditArea');
        const input = document.getElementById('queryInput');
        if (editArea && input) {
            input.value = editArea.value;
            logTelemetry("Enhanced Directive Deployed", "success");
            showProcessingToast("Enhanced prompt deployed.");
        }
        closeEnhanceModal();
    });

    // Reject: close modal, keep original
    document.getElementById('enhanceRejectBtn')?.addEventListener('click', () => {
        logTelemetry("Enhancement Discarded", "system");
        showProcessingToast("Original prompt retained.");
        closeEnhanceModal();
    });

    // Click overlay to close
    document.getElementById('enhanceModal')?.addEventListener('click', (e) => {
        if (e.target.id === 'enhanceModal') closeEnhanceModal();
    });
});

window.visualizeSelection = function (fallbackText) {
    const selection = window.getSelection().toString();
    const textToProcess = selection || fallbackText;

    if (!textToProcess) {
        showProcessingToast("Highlight some data first!");
        return;
    }

    document.getElementById('interrogation-tooltip').style.display = 'none';

    // Show processing feedback
    logTelemetry("VISUALIZING SELECTION...", "process");
    showProcessingToast("Generating visualization...");

    // Build the query for table/chart generation
    const query = `Convert this data into a formatted table or chart. If it's tabular data, create a clean markdown table. If it's numerical, suggest a chart type. DATA: "${textToProcess}"`;
    // Trigger the council to process it
    triggerCouncil(query);
};

// Consolidated System Status Handler
function updateSystemStatus(status) {
    updateSystemStatusText(status);
    const el = document.getElementById('system-status-text');
    if (el) {
        el.classList.add('pulse');
        setTimeout(() => el.classList.remove('pulse'), 500);
    }
}

function updateSystemStatusText(status) {
    const el = document.getElementById('system-status-text');
    if (el) el.innerText = status.toUpperCase();
}

function openIntakeModal() {
    const modal = document.getElementById('intakeModal');
    if (modal) modal.classList.add('visible');
}

function closeIntakeModal() {
    const modal = document.getElementById('intakeModal');
    if (modal) modal.classList.remove('visible');
}

function lockMissionContext() {
    const client = document.getElementById('intake-client').value;
    const industry = document.getElementById('intake-industry').value;
    const priority = document.getElementById('intake-priority').value;
    const horizon = document.getElementById('intake-horizon').value;
    const risk = document.getElementById('intake-risk').value;
    const scope = document.getElementById('intake-scope').value;
    const budget = document.getElementById('intake-budget').value;

    const workflow = document.getElementById('intake-workflow')?.value || "RESEARCH";

    if (!client || !industry) {
        showProcessingToast("Client Name and Industry are required.");
        return;
    }

    sessionState.missionContext = {
        client, industry, priority, horizon, risk, scope, budget,
        workflow,
        lockedAt: new Date().toISOString()
    };
    sessionState.isMissionLocked = true;

    // Mission Lock Persistence: Save to local storage
    localStorage.setItem('korum-mission-context', JSON.stringify(sessionState.missionContext));

    closeIntakeModal();
    logTelemetry(`Mission Locked for Client: ${client}`, "success");
    showProcessingToast("Mission Profile Locked. Convening Council...");

    // Proceed to trigger council now that context is locked
    const query = document.getElementById('queryInput').value;
    triggerCouncil(query);
}

function injectMissionContext(rawQuery) {
    if (!sessionState.isMissionLocked || !sessionState.missionContext) return rawQuery;

    const ctx = sessionState.missionContext;
    const contextHeader = `
[MISSION CONTEXT - DO NOT IGNORE]
CLIENT: ${ctx.client}
INDUSTRY: ${ctx.industry}
STRATEGIC PRIORITY: ${ctx.priority}
TIME HORIZON: ${ctx.horizon}
RISK TOLERANCE: ${ctx.risk}
SCOPE: ${ctx.scope}
BUDGET/STRATEGIC VALUE: ${ctx.budget}
[END MISSION CONTEXT]

PRIMARY OBJECTIVE: ${rawQuery}
`;
    return contextHeader.trim();
}

// Processing Toast for user feedback
function showLoadingState(taskName) {
    const container = document.querySelector(".results-content");
    const resultsPanel = document.querySelector(".results-container");

    if (resultsPanel) resultsPanel.classList.add("visible");
    if (container) {
        container.innerHTML = `
            <div class="decoding-state" style="padding:40px; text-align:center; font-family:var(--font-head);">
                <div class="neural-pulse" style="width:60px; height:60px; margin:0 auto 20px; border:2px solid #00FF9D; border-radius:50%; animation: pulse 1.5s infinite;"></div>
                <h2 style="color:#FFF; letter-spacing:2px; font-size:14px; text-transform:uppercase;">${taskName || 'Decoding Intelligence'}</h2>
                <p style="color:#00FF9D; font-size:11px; margin-top:10px; opacity:0.7;">Council is synthesizing your selection...</p>
                <div class="loading-bar-min" style="width:200px; height:2px; background:rgba(0,255,157,0.1); margin:20px auto; position:relative; overflow:hidden;">
                    <div class="loading-fill-min" style="position:absolute; width:50%; height:100%; background:#00FF9D; animation: slide 1s infinite ease-in-out;"></div>
                </div>
            </div>
        `;
    }
    logTelemetry(`TASK INITIATED: ${taskName}`, "process");
}

function showProcessingToast(message) {
    let toast = document.getElementById('processing-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'processing-toast';
        toast.style.cssText = `
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0, 255, 157, 0.15);
            backdrop-filter: blur(10px);
            border: 1px solid #00FF9D;
            color: #00FF9D;
            padding: 14px 28px;
            border-radius: 50px;
            font-family: var(--font-head);
            font-size: 13px;
            font-weight: 700;
            z-index: 10000;
            display: flex;
            align-items: center;
            gap: 12px;
            box-shadow: 0 0 30px rgba(0, 255, 157, 0.2), inset 0 0 10px rgba(0, 255, 157, 0.1);
            letter-spacing: 0.1em;
            text-transform: uppercase;
            opacity: 0;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        `;
        document.body.appendChild(toast);
    }

    toast.innerHTML = `<span style="font-size:18px">⚡</span> <span>${message}</span>`;
    toast.style.opacity = '1';
    toast.style.bottom = '50px';

    // Optional: Success flash on screen
    if (message.toLowerCase().includes('success') || message.toLowerCase().includes('copied') || message.toLowerCase().includes('saved') || message.toLowerCase().includes('downloaded')) {
        document.body.style.boxShadow = "inset 0 0 100px rgba(0, 255, 157, 0.2)";
        setTimeout(() => document.body.style.boxShadow = "none", 400);
    }

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.bottom = '30px';
    }, 3000);
}

function formatV2Content(content, phase) {
    if (!content) return "";

    // NEW: Clean internal structuring tags
    let displayContent = (typeof content === 'string') ? content : JSON.stringify(content, null, 2);
    displayContent = displayContent.replace(/\[\/?(DECISION_CANDIDATE|RISK_VECTOR|METRIC_ANCHOR|TRUTH_BOMB)\]/g, "");

    // SPECIAL RENDERING FOR PHASE 1 (JSON)
    if (phase === "CONSTRAINT ANALYSIS" && typeof content === 'object') {
        let metaContent = `<div style="margin-bottom:10px;"><strong style="color:#00FF9D">CORE GOAL:</strong><br>${content.core_goal || "N/A"}</div>`;

        if (content.explicit_constraints?.length) {
            metaContent += `<strong style="color:#FFB020">EXPLICIT CONSTRAINTS:</strong><ul style="margin-top:5px; padding-left:20px; color:#ddd;">`;
            content.explicit_constraints.forEach(c => metaContent += `<li>${c}</li>`);
            metaContent += `</ul>`;
        }
        return metaContent;
    } else {
        // Standard Text Formatting for Phases 2-4
        displayContent = formatV2Text(typeof content === 'object' ? JSON.stringify(content, null, 2) : content);
    }
    return displayContent;
}

function formatV2Text(text) {
    if (!text) return "";
    return text
        .replace(/^## (.*?)$/gm, '<h3 style="color:#00FF9D; margin-top:15px; border-bottom:1px solid #333; padding-bottom:5px;">$1</h3>')
        .replace(/^### (.*?)$/gm, '<h4 style="color:#FFB020; margin-top:10px;">$1</h4>')
        .replace(/\*\*(.*?)\*\*/g, '<strong style="color:#FFF;">$1</strong>')
        .replace(/^- (.*?)$/gm, '• $1<br>')
        .replace(/\n\d\. (.*?)$/gm, '<div style="margin-left:10px; margin-bottom:4px;"><strong>$1</strong></div>')
        .replace(/```mermaid([\s\S]*?)```/g, (match, code) => {
            const cleanCode = code.trim().replace(/^mermaid\n/i, '');
            return `<div class="mermaid-container"><div class="mermaid">${cleanCode}</div></div>`;
        })
        .replace(/```([\s\S]*?)```/g, (match, code) => `<pre class="code-block">${code.trim()}</pre>`)
        .replace(/\|(.+)\|/g, (match) => {
            const cells = match.split('|').filter(c => c.trim().length > 0 || match.indexOf(c) > 0);
            if (cells.some(c => c.includes('---'))) return '<hr style="border:0; border-bottom:1px solid #333; margin:10px 0;">';
            return `<div class="table-row" style="display:flex; border-bottom:1px solid rgba(255,255,255,0.05); padding:4px 0;">${cells.map(c => `<div style="flex:1; padding:4px; font-size:11px;">${c.trim()}</div>`).join('')}</div>`;
        });
}

function copyToClipboard(htmlContent) {
    // Detect if content contains a table
    const hasTable = htmlContent.includes('<table') || htmlContent.includes('|---');

    // Convert HTML back to cleaned Markdown/Text
    let text = htmlContent
        .replace(/<h3[^>]*>(.*?)<\/h3>/g, '\n## $1\n')
        .replace(/<h4[^>]*>(.*?)<\/h4>/g, '\n### $1\n')
        .replace(/<strong[^>]*>(.*?)<\/strong>/g, '$1') // Remove formatting to keep colors clean in apps
        .replace(/<br\s*\/?>/g, '\n')
        .replace(/<div[^>]*>(.*?)<\/div>/g, '$1\n')
        .replace(/<[^>]*>/g, '')
        .trim();

    if (hasTable) {
        // Offer CSV conversion for Excel
        const csvData = copyAsCSV(htmlContent);
        navigator.clipboard.writeText(csvData).then(() => {
            logTelemetry("Table copied as CSV (Excel optimized)", "success");
            showProcessingToast("Table copied! Optimized for Excel.");
        });
        return;
    }

    navigator.clipboard.writeText(text).then(() => {
        logTelemetry("Response copied as plain text", "system");
        showProcessingToast("✓ Content copied!");
    }).catch(err => {
        console.error('Failed to copy locally: ', err);
    });
}

function copyAsCSV(content) {
    if (!content) return "";

    // If it's HTML, extract table rows
    if (content.includes('<table')) {
        const div = document.createElement('div');
        div.innerHTML = content;
        const rows = Array.from(div.querySelectorAll('tr'));
        return rows.map(tr => {
            const cells = Array.from(tr.querySelectorAll('td, th'));
            return cells.map(cell => `"${cell.innerText.replace(/"/g, '""')}"`).join(',');
        }).join('\n');
    }

    // If it's Markdown table
    const lines = content.trim().split('\n');
    return lines
        .filter(line => line.includes('|') && !line.includes('|---')) // Skip separator rows
        .map(line => {
            const cells = line.split('|').filter(c => c.trim().length > 0 || line.indexOf(c) > 0);
            return cells.map(cell => `"${cell.trim().replace(/"/g, '""')}"`).join(',');
        }).join('\n');
}

async function executeCouncil(query, roleName) {
    // Check if it's a sub-task (visualization/interrogation)
    const isSubTask = query.startsWith("INTERROGATE") || query.startsWith("FACT CHECK") || query.startsWith("VISUALIZE");

    if (isSubTask) {
        const taskType = query.split(":")[0];
        showLoadingState(taskType);
    }

    triggerNetworkAnimation(); // FIRE LIGHTNING

    // Set all AIs to "responding" state
    ["openai", "anthropic", "google", "perplexity", "mistral", "local"].forEach(p => {
        if (AIHealth.isAvailable(p)) {
            AIHealth.setResponding(p, true);
        }
    });

    let roleConfig;

    // Use custom roles from DECK
    if (customRolesActive) {
        roleConfig = {
            openai: document.getElementById('roleLabel-openai')?.innerText.toLowerCase() || 'strategist',
            anthropic: document.getElementById('roleLabel-anthropic')?.innerText.toLowerCase() || 'architect',
            google: document.getElementById('roleLabel-google')?.innerText.toLowerCase() || 'critic',
            perplexity: document.getElementById('roleLabel-perplexity')?.innerText.toLowerCase() || 'scout',
            mistral: document.getElementById('roleLabel-mistral')?.innerText.toLowerCase() || 'analyst',
            local: document.getElementById('roleLabel-local')?.innerText.toLowerCase() || 'oracle'
        };
        logTelemetry("Using Custom Agent Config", "process");
    } else {
        roleConfig = PROTOCOL_CONFIGS[roleName] || PROTOCOL_CONFIGS['System Core'];
        // Ensure mistral/local defaults are set if not in protocol
        if (!roleConfig.mistral) roleConfig.mistral = "analyst";
        if (!roleConfig.local) roleConfig.local = "oracle";
    }

    // MODE FLAGS
    const useV2 = activeModes.v2;
    const isRedTeam = activeModes.red;
    const useSerpAPI = activeModes.serp;
    if (useSerpAPI) logTelemetry("LIVE MODE ACTIVE: Fetching Real-Time Data...", "process");

    const payload = {
        question: query,
        council_mode: true,
        council_roles: roleConfig,
        active_models: ["openai", "anthropic", "google", "perplexity", "mistral", "local"].filter(p => AIHealth.isAvailable(p) && !document.querySelector(`.deck-card.${p}`)?.classList.contains('silenced')),
        use_v2: true,
        is_red_team: isRedTeam,
        use_serp: useSerpAPI,  // Real-time data via SerpAPI
        workflow: sessionState.missionContext?.workflow || "RESEARCH"
    };

    // Use FormData when files are attached, JSON otherwise
    let response;
    if (pendingFiles.length > 0) {
        const formData = new FormData();
        formData.append('payload', JSON.stringify(payload));
        for (const file of pendingFiles) {
            formData.append('files', file);
        }
        logTelemetry(`${pendingFiles.length} file(s) attached to query`, "process");
        response = await authFetch('/api/ask', { method: 'POST', body: formData });
        pendingFiles = [];
        renderFilePreview();
    } else {
        response = await authFetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    }
    if (!response.ok) throw new Error(`HTTP Error ${response.status}`);
    const data = await response.json();

    // Cache as Main Mission if not a sub-task
    if (!sessionState.isSubTask) {
        sessionState.mainMissionData = data;
    }

    renderResults(data, roleName);
    incrementQueryCount();
    resetUI();
}

function renderResults(data, roleName) {
    // Store for export functionality
    lastCouncilData = { ...data, roleName };

    // Hide processing toast
    const toast = document.getElementById('processing-toast');
    if (toast) toast.style.display = 'none';

    const container = document.querySelector(".results-content");
    const grid = document.createElement("div"); grid.className = "results-grid";

    // Update Mission Stats
    const totalTime = data.results ? Object.values(data.results).reduce((acc, r) => acc + (r.time || 0), 0) : 0;
    const avgConfidence = data.results ? (Object.values(data.results).reduce((acc, r) => acc + (r.truth_meter || 85), 0) / Object.keys(data.results).length) : 85;
    const violations = data.results ? Object.values(data.results).reduce((acc, r) => acc + (r.violations?.length || 0), 0) : 0;

    const latEl = document.getElementById('stat-latency');
    const confEl = document.getElementById('stat-confidence');
    const violEl = document.getElementById('stat-violations');

    if (latEl) latEl.textContent = totalTime.toFixed(1) + 's';
    if (confEl) confEl.textContent = Math.round(avgConfidence) + '%';
    if (violEl) {
        violEl.textContent = violations;
        violEl.style.color = violations > 0 ? '#FF4444' : '#00FF9D';
    }

    // Consensus
    const consensusCard = document.createElement("div"); consensusCard.className = "consensus-card";
    consensusCard.innerHTML = `<div class="consensus-title"><span style="font-size:16px">🏛️</span> COUNCIL DECISION: ${roleName.toUpperCase()}</div><div class="consensus-body">${formatText(data.consensus || "No consensus reached.")}</div>`;
    grid.appendChild(consensusCard);

    // Agents - Process results and update health status
    ["openai", "anthropic", "google", "perplexity", "mistral", "local"].forEach(provider => {
        const res = data.results[provider];

        // Update AI Health Status
        AIHealth.setResponding(provider, false); // Stop responding animation

        if (!res) {
            // No response - might be disabled or not called
            return;
        }

        if (res.success) {
            AIHealth.recordSuccess(provider);
        } else {
            AIHealth.recordFailure(provider, res.error || 'Request failed');
            // CONTINUE anyway to render the error card
        }

        // Capture for Context
        if (sessionState && sessionState.lastResponses && res.success) {
            sessionState.lastResponses[provider] = res.response;
        }

        // Create card
        const card = document.createElement("div");
        card.className = `agent-card ${provider} ${!res.success ? 'failed' : ''}`;
        card.dataset.name = res.role ? res.role.toUpperCase() : getProviderName(provider);
        card.dataset.provider = provider;

        // --- NEW: CLAIM HIGHLIGHTING ---
        const rawResponse = res.response;
        const verifiedClaims = res.verified_claims || [];
        const truthScore = res.truth_meter !== undefined ? res.truth_meter : 85;

        const displayContent = highlightClaims(formatText(rawResponse), verifiedClaims);
        const cost = res.cost || 0.0091;
        const time = res.time || 12.34;

        card.innerHTML = `
            <div class="precision-header">
                <div class="ph-left">
                    <div class="ph-model-name">${res.role ? res.role.toUpperCase() : getProviderName(provider)}</div>
                    <div class="ph-role-label">${getProviderName(provider)} | ${res.model || "v2.0"}</div>
                    
                    <div class="ph-truth-container">
                        <div class="truth-score-val" style="color: ${truthScore > 80 ? '#00FF9D' : truthScore > 50 ? '#FFB020' : '#FF4444'}">
                            TRUTH SCORE: ${truthScore}/100
                        </div>
                        <div class="truth-bar-container">
                            <div class="truth-fill" style="width: ${truthScore}%"></div>
                        </div>
                    </div>
                </div>
                <div class="ph-right">
                    <button class="interrogate-btn" onclick="event.stopPropagation(); openInterrogation('${getProviderName(provider)}')">
                        🔍 INTERROGATE
                    </button>
                    <button class="verify-btn" onclick="event.stopPropagation(); executeVerify(decodeURIComponent('${encodeURIComponent(rawResponse)}'), '${getProviderName(provider)}')">
                        🔎 VERIFY
                    </button>
                    <div class="metric-pill">$${cost.toFixed(4)}</div>
                    <div class="metric-pill time">${time}s</div>
                    <div class="tool-action" onclick="event.stopPropagation(); this.classList.add('success'); setTimeout(()=>this.classList.remove('success'), 1000); saveReport()" title="Save">💾</div>
                    <div class="tool-action" onclick="event.stopPropagation(); this.classList.add('success'); setTimeout(()=>this.classList.remove('success'), 1000); window.visualizeSelection(decodeURIComponent('${encodeURIComponent(rawResponse)}'))" title="Chart">📊</div>
                    <div class="tool-action" onclick="event.stopPropagation(); this.classList.add('success'); setTimeout(()=>this.classList.remove('success'), 1000); copyTextToClipboard(decodeURIComponent('${encodeURIComponent(rawResponse)}'), '${getProviderName(provider)} output copied')" title="Copy">📋</div>
                </div>
            </div>
            <div class="agent-response">${displayContent}</div>
        `;

        // Make card clickable
        card.addEventListener('click', () => {
            openCardModal({
                name: getProviderName(provider),
                meta: `<div class="agent-meta"><span>${getProviderName(provider)}</span><span>${res.model || provider}</span></div>`,
                content: res.response,
                model: res.model || provider
            });
        });

        // Store Response for Context
        sessionState.lastResponses[provider] = res.response;

        grid.appendChild(card);
    });

    // 5TH CARD: RED TEAM EXPLOIT (ADDITIVE)
    if (data.results && data.results['red_team'] && data.results['red_team'].success) {
        const res = data.results['red_team'];
        const card = document.createElement("div");
        card.className = "agent-card red-team-card";

        // Critical Styling
        card.style.border = "1px solid #FF4444";
        card.style.background = "rgba(255, 68, 68, 0.05)";
        card.style.marginTop = "20px";

        const displayContent = formatText(res.response);

        card.innerHTML = `
            <div class="precision-header" style="border-bottom: 1px solid #FF4444;">
                <div class="ph-left">
                    <div class="ph-model-name" style="color:#FF4444">☠️ RED TEAM</div>
                    <div class="ph-role-label" style="color:#FF8888">EXPLOIT VECTOR</div>
                    <div class="badge-stack">
                        <div class="status-badge" style="border-color:#FF4444; color:#FF4444;">SEVERITY: CRITICAL</div>
                    </div>
                </div>
                <div class="ph-right">
                   <div class="metric-pill" style="color:#FF4444">THREAT DETECTED</div>
                   <div class="tool-action" onclick="event.stopPropagation(); saveReport()" title="Save">💾</div>
                   <div class="tool-action" onclick="event.stopPropagation(); copyTextToClipboard(decodeURIComponent('${encodeURIComponent(res.response)}'), 'Threat vector copied')" title="Copy">📋</div>
                </div>
            </div>
            <div class="agent-response" style="color:#FFDDDD">${displayContent}</div>
        `;

        // Custom Modal for Red Team
        card.addEventListener('click', () => {
            openCardModal({
                name: "RED TEAM EXPLOIT",
                meta: `<div class="agent-meta"><span style="color:#FF4444">RED TEAM</span><span>EXPLOIT</span></div>`,
                content: res.response,
                model: "CRITICAL"
            });
        });

        grid.appendChild(card);
    }

    // EXECUTIVE BRIEF CARD (Synthesis) - renders full intelligence object
    if (data.synthesis && data.synthesis.meta) {
        const briefCard = document.createElement("div");
        briefCard.className = "agent-card exec-brief-card";
        const synthesis = data.synthesis;
        const meta = synthesis.meta || {};
        const sections = synthesis.sections || {};
        const structured = synthesis.structured_data || {};
        const tags = synthesis.intelligence_tags || {};

        let briefHtml = `<div class="exec-brief">`;
        briefHtml += `<div class="exec-brief-header">
            <div class="exec-brief-title">${meta.title || 'EXECUTIVE INTELLIGENCE BRIEF'}</div>
            <div class="exec-brief-meta">
                <span>${meta.workflow || 'RESEARCH'}</span>
                <span>TRUTH: ${(() => { let s = meta.composite_truth_score; if (s === undefined || s === null) return '—'; s = parseFloat(s); if (s <= 1) s = Math.round(s * 100); return s; })()}/100</span>
                <span>${(meta.models_used || []).length} AGENTS</span>
                <button class="qanapi-sign-btn" onclick="event.stopPropagation(); showProcessingToast('Secure Enclave · FedRAMP High · Cryptographic Signature Ready [STAGING]')">
                    <span style="font-size:10px">🔏</span> SIGN REPORT
                </button>
            </div>
        </div>`;

        if (meta.summary) {
            briefHtml += `<div class="exec-brief-summary">${formatText(meta.summary)}</div>`;
        }

        const sectionEntries = Object.entries(sections).filter(([, v]) => v && v !== 'Full narrative text...');
        if (sectionEntries.length > 0) {
            briefHtml += `<div class="exec-brief-sections">`;
            sectionEntries.forEach(([title, content]) => {
                const displayTitle = title.replace(/_/g, ' ').toUpperCase();
                briefHtml += `<div class="exec-brief-section">
                    <div class="exec-brief-section-title">${displayTitle}</div>
                    <div class="exec-brief-section-body">${formatText(content)}</div>
                </div>`;
            });
            briefHtml += `</div>`;
        }

        if (structured.key_metrics?.length) {
            briefHtml += `<div class="exec-brief-metrics">
                <div class="exec-brief-section-title">KEY METRICS</div>
                <div class="exec-brief-metrics-grid">`;
            structured.key_metrics.forEach(m => {
                briefHtml += `<div class="exec-metric-card">
                    <div class="exec-metric-label">${m.metric || ''}</div>
                    <div class="exec-metric-value">${m.value || ''}</div>
                    <div class="exec-metric-context">${m.context || ''}</div>
                </div>`;
            });
            briefHtml += `</div></div>`;
        }

        if (structured.action_items?.length) {
            briefHtml += `<div class="exec-brief-actions">
                <div class="exec-brief-section-title">ACTION ITEMS</div>`;
            structured.action_items.forEach(item => {
                const priorityColor = item.priority === 'high' ? '#FF4444' : item.priority === 'med' ? '#FFB020' : '#00FF9D';
                briefHtml += `<div class="exec-action-item">
                    <span class="exec-action-priority" style="background:${priorityColor}20; color:${priorityColor}; border:1px solid ${priorityColor}40">${(item.priority || 'med').toUpperCase()}</span>
                    <span class="exec-action-task">${item.task || ''}</span>
                    ${item.timeline ? `<span class="exec-action-timeline">${item.timeline}</span>` : ''}
                </div>`;
            });
            briefHtml += `</div>`;
        }

        if (structured.risks?.length) {
            briefHtml += `<div class="exec-brief-risks">
                <div class="exec-brief-section-title">RISK VECTORS</div>`;
            structured.risks.forEach(r => {
                briefHtml += `<div class="exec-risk-item">
                    <div class="exec-risk-header">
                        <span class="exec-risk-label">${r.risk || ''}</span>
                        <span class="exec-risk-severity">${r.severity || ''}</span>
                    </div>
                    ${r.mitigation ? `<div class="exec-risk-mitigation">MITIGATION: ${r.mitigation}</div>` : ''}
                </div>`;
            });
            briefHtml += `</div>`;
        }

        if (tags.decisions?.length) {
            briefHtml += `<div class="exec-brief-decisions">
                <div class="exec-brief-section-title">DECISION CANDIDATES</div>
                <ul class="exec-decision-list">`;
            tags.decisions.forEach(d => { briefHtml += `<li>${d}</li>`; });
            briefHtml += `</ul></div>`;
        }

        briefHtml += `</div>`;
        briefCard.innerHTML = briefHtml;
        grid.appendChild(briefCard);
    }

    // --- ANALYTIC DIVERGENCE PANEL ---
    if (data.divergence) {
        const div = data.divergence;
        const varianceStat = document.getElementById('protocol-variance-stat');
        const divScore = document.getElementById('stat-divergence');

        if (varianceStat && divScore) {
            varianceStat.style.display = 'flex';
            const score = div.divergence_score || 0;
            divScore.textContent = score + '%';
            if (div.protocol_variance) {
                divScore.style.color = score > 50 ? '#FF4444' : '#FFB020';
                varianceStat.classList.add('variance-active');
            } else {
                divScore.style.color = '#00FF9D';
                varianceStat.classList.remove('variance-active');
            }
        }

        const divCard = document.createElement("div");
        divCard.className = `agent-card divergence-card ${div.protocol_variance ? 'variance-detected' : 'consensus-strong'}`;
        divCard.style.marginTop = '16px';

        let divHtml = `<div class="divergence-header">
            <div class="divergence-title-row">
                <span class="divergence-icon">${div.protocol_variance ? '⚠' : '✓'}</span>
                <span class="divergence-label">ANALYTIC DIVERGENCE ${div.protocol_variance ? '— PROTOCOL VARIANCE DETECTED' : '— CONSENSUS STABLE'}</span>
            </div>
            <div class="divergence-scores">
                <span class="div-score consensus-score">CONSENSUS: ${div.consensus_score || 0}/100</span>
                <span class="div-score divergence-score-val">DIVERGENCE: ${div.divergence_score || 0}/100</span>
            </div>
        </div>`;

        if (div.divergence_summary) {
            divHtml += `<div class="divergence-summary">${formatText(div.divergence_summary)}</div>`;
        }

        if (div.agreement_topics?.length) {
            divHtml += `<div class="div-section"><div class="div-section-title">AREAS OF AGREEMENT</div>`;
            div.agreement_topics.forEach(a => {
                const providers = (a.providers || []).map(p => p.toUpperCase()).join(', ');
                divHtml += `<div class="div-agreement-item">
                    <span class="div-confidence-badge confidence-${(a.confidence || 'moderate').toLowerCase()}">${(a.confidence || 'MODERATE').toUpperCase()}</span>
                    <span class="div-topic-name">${a.topic || ''}</span>
                    <div class="div-topic-detail">${a.detail || ''}</div>
                    ${providers ? `<div class="div-providers">Supported by: ${providers}</div>` : ''}
                </div>`;
            });
            divHtml += `</div>`;
        }

        if (div.contested_topics?.length) {
            divHtml += `<div class="div-section"><div class="div-section-title contested">CONTESTED POSITIONS</div>`;
            div.contested_topics.forEach(c => {
                divHtml += `<div class="div-contested-item">
                    <div class="div-contested-header">
                        <span class="div-topic-name">${c.topic || ''}</span>
                        <span class="div-severity severity-${(c.severity || 'medium').toLowerCase()}">${(c.severity || 'MEDIUM').toUpperCase()}</span>
                    </div>`;
                if (c.positions?.length) {
                    c.positions.forEach(pos => {
                        divHtml += `<div class="div-position">
                            <span class="div-provider-badge">${(pos.provider || '').toUpperCase()}</span>
                            <span class="div-position-text">${pos.position || ''}</span>
                        </div>`;
                    });
                }
                if (c.operational_impact) {
                    divHtml += `<div class="div-impact">OPERATIONAL IMPACT: ${c.operational_impact}</div>`;
                }
                divHtml += `</div>`;
            });
            divHtml += `</div>`;
        }

        if (div.confidence_gaps?.length) {
            divHtml += `<div class="div-section"><div class="div-section-title">CONFIDENCE GAPS</div>`;
            div.confidence_gaps.forEach(g => {
                divHtml += `<div class="div-gap-item severity-${(g.severity || 'medium').toLowerCase()}">
                    <span class="div-gap-severity">${(g.severity || 'MEDIUM').toUpperCase()}</span>
                    ${g.description || ''}
                    ${g.spread ? `<span class="div-gap-spread">(Spread: ${g.spread})</span>` : ''}
                </div>`;
            });
            divHtml += `</div>`;
        }

        if (div.resolution_requirements?.length) {
            divHtml += `<div class="div-section"><div class="div-section-title">RESOLUTION REQUIREMENTS</div>`;
            div.resolution_requirements.forEach(r => {
                divHtml += `<div class="div-resolution-item">
                    <span class="div-resolution-priority priority-${(r.priority || 'medium').toLowerCase()}">${(r.priority || 'MED').toUpperCase()}</span>
                    ${r.question || ''}
                </div>`;
            });
            divHtml += `</div>`;
        }

        divCard.innerHTML = divHtml;
        divCard.addEventListener('click', () => openDivergenceModal());
        grid.appendChild(divCard);
    }

    container.innerHTML = "";

    // EXPORT COMMAND CENTER (Phase 6)
    renderExportToolbar(container, data);

    container.appendChild(grid);
    document.querySelector(".results-container").classList.add("visible");
    document.getElementById('recallAnalysisBtn').style.display = 'none'; // Hide recall button when showing fresh results
    logTelemetry("Consensus Reached. Displaying Output.", "system");

    // RENDER CHARTS
    setTimeout(() => {
        if (window.mermaid) {
            try {
                mermaid.init(undefined, document.querySelectorAll('.mermaid'));
            } catch (e) {
                console.error("Mermaid Render Error:", e);
            }
        }
    }, 500);

    // RENDER ACTION PANEL (Phase 5)
    if (data.synthesis) {
        logTelemetry("Synthesizing Smart Actions...", "process");
        renderActionPanel(data.synthesis, data.classification);

        // Phase 4/6: Background Prefetch
        PrefetchManager.initPrefetch('current_session', {
            synthesis: data.synthesis,
            classification: data.classification
        });
    }

    // RENDER CHARTS
    setTimeout(() => {
        if (window.mermaid) mermaid.init(undefined, document.querySelectorAll('.mermaid'));
    }, 500);
}

// === ANALYTIC DIVERGENCE MODAL ===
function openDivergenceModal() {
    if (!lastCouncilData?.divergence) return;
    const div = lastCouncilData.divergence;

    // Remove existing modal
    const existing = document.getElementById('divergence-modal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'divergence-modal';
    modal.className = 'divergence-modal-overlay';

    let modalHtml = `<div class="divergence-modal-content">
        <div class="divergence-modal-header">
            <div class="divergence-modal-title">
                <span>${div.protocol_variance ? '⚠' : '✓'} ANALYTIC DIVERGENCE REPORT</span>
                <span class="divergence-modal-close" onclick="document.getElementById('divergence-modal').remove()">&times;</span>
            </div>
            <div class="divergence-modal-scores">
                <div class="modal-score-block">
                    <div class="modal-score-value" style="color:${div.consensus_score >= 70 ? '#00FF9D' : '#FFB020'}">${div.consensus_score || 0}</div>
                    <div class="modal-score-label">CONSENSUS</div>
                </div>
                <div class="modal-score-block">
                    <div class="modal-score-value" style="color:${div.divergence_score > 50 ? '#FF4444' : div.divergence_score > 30 ? '#FFB020' : '#00FF9D'}">${div.divergence_score || 0}</div>
                    <div class="modal-score-label">DIVERGENCE</div>
                </div>
                <div class="modal-score-block">
                    <div class="modal-score-value ${div.protocol_variance ? 'variance-flash' : ''}" style="color:${div.protocol_variance ? '#FF4444' : '#00FF9D'}">${div.protocol_variance ? 'ACTIVE' : 'CLEAR'}</div>
                    <div class="modal-score-label">VARIANCE</div>
                </div>
            </div>
        </div>
        <div class="divergence-modal-body">`;

    if (div.divergence_summary) {
        modalHtml += `<div class="modal-div-summary">${div.divergence_summary}</div>`;
    }

    // Agreement
    if (div.agreement_topics?.length) {
        modalHtml += `<div class="modal-div-section">
            <div class="modal-div-section-title">AREAS OF AGREEMENT</div>`;
        div.agreement_topics.forEach(a => {
            const providers = (a.providers || []).map(p => `<span class="modal-provider-chip">${p.toUpperCase()}</span>`).join(' ');
            modalHtml += `<div class="modal-agreement-item">
                <div class="modal-item-header">
                    <span class="modal-confidence confidence-${(a.confidence || 'moderate').toLowerCase()}">${(a.confidence || 'MODERATE').toUpperCase()}</span>
                    <strong>${a.topic || ''}</strong>
                </div>
                <div class="modal-item-detail">${a.detail || ''}</div>
                <div class="modal-item-providers">${providers}</div>
            </div>`;
        });
        modalHtml += `</div>`;
    }

    // Contested
    if (div.contested_topics?.length) {
        modalHtml += `<div class="modal-div-section">
            <div class="modal-div-section-title contested">CONTESTED POSITIONS</div>`;
        div.contested_topics.forEach(c => {
            modalHtml += `<div class="modal-contested-item">
                <div class="modal-contested-header">
                    <strong>${c.topic || ''}</strong>
                    <span class="modal-severity severity-${(c.severity || 'medium').toLowerCase()}">${(c.severity || 'MEDIUM').toUpperCase()}</span>
                </div>`;
            (c.positions || []).forEach(pos => {
                modalHtml += `<div class="modal-position">
                    <span class="modal-provider-chip contested">${(pos.provider || '').toUpperCase()}</span>
                    <span>${pos.position || ''}</span>
                </div>`;
                if (pos.evidence) {
                    modalHtml += `<div class="modal-evidence">Evidence: ${pos.evidence}</div>`;
                }
            });
            if (c.operational_impact) {
                modalHtml += `<div class="modal-impact">OPERATIONAL IMPACT: ${c.operational_impact}</div>`;
            }
            modalHtml += `</div>`;
        });
        modalHtml += `</div>`;
    }

    // Confidence Gaps
    if (div.confidence_gaps?.length) {
        modalHtml += `<div class="modal-div-section">
            <div class="modal-div-section-title">CONFIDENCE GAPS</div>`;
        div.confidence_gaps.forEach(g => {
            modalHtml += `<div class="modal-gap-item">
                <span class="modal-severity severity-${(g.severity || 'medium').toLowerCase()}">${(g.severity || 'MED').toUpperCase()}</span>
                ${g.description || ''}
            </div>`;
        });
        modalHtml += `</div>`;
    }

    // Resolution
    if (div.resolution_requirements?.length) {
        modalHtml += `<div class="modal-div-section">
            <div class="modal-div-section-title">WHAT WOULD RESOLVE DISAGREEMENT</div>`;
        div.resolution_requirements.forEach(r => {
            modalHtml += `<div class="modal-resolution-item">
                <span class="modal-priority priority-${(r.priority || 'medium').toLowerCase()}">${(r.priority || 'MED').toUpperCase()}</span>
                ${r.question || ''}
            </div>`;
        });
        modalHtml += `</div>`;
    }

    modalHtml += `</div></div>`;
    modal.innerHTML = modalHtml;

    // Close on overlay click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });

    document.body.appendChild(modal);
}

function setupInterrogation() {
    const tooltip = document.getElementById('interrogation-tooltip');

    document.addEventListener('mouseup', (e) => {
        const selection = window.getSelection().toString().trim();
        if (selection && selection.length > 5) {
            // Show Tooltip
            activeSelection = selection;
            tooltip.style.display = 'flex';
            tooltip.style.left = `${e.pageX + 10}px`;
            tooltip.style.top = `${e.pageY - 40}px`;
        } else {
            // Delay hidding slightly to allow clicking buttons
            setTimeout(() => {
                if (!window.getSelection().toString().trim()) {
                    tooltip.style.display = 'none';
                }
            }, 200);
        }
    });

    document.getElementById('btn-dock').addEventListener('click', () => {
        if (activeSelection) {
            ResearchDock.add(activeSelection, 'selection');
            showProcessingToast("Snippet docked!");
            tooltip.style.display = 'none';
            window.getSelection().removeAllRanges();
            activeSelection = "";
        }
    });

    document.getElementById('btn-challenge').addEventListener('click', () => {
        if (activeSelection) {
            tooltip.style.display = 'none';

            // Find which agent card the selection came from
            const sel = window.getSelection();
            const agentCard = sel.anchorNode?.parentElement?.closest('.agent-card');
            const providerName = agentCard?.querySelector('.ph-model-name')?.innerText || 'Target';

            // Use the new interrogation flow (2 API calls, not full council)
            openInterrogation(providerName);

            window.getSelection().removeAllRanges();
            activeSelection = "";
        }
    });

    document.getElementById('btn-verify-select')?.addEventListener('click', () => {
        if (activeSelection) {
            tooltip.style.display = 'none';

            // Find which agent card the selection came from
            const sel = window.getSelection();
            const agentCard = sel.anchorNode?.parentElement?.closest('.agent-card');
            const providerName = agentCard?.querySelector('.ph-model-name')?.innerText || 'Council';

            executeVerify(activeSelection, providerName);

            window.getSelection().removeAllRanges();
            activeSelection = "";
        }
    });

    document.getElementById('btn-visualize-select').addEventListener('click', () => {
        if (activeSelection) {
            const query = `VISUALIZE SELECTION: "${activeSelection}". 
            Create a Mermaid JS chart (flowchart or pie) specifically based on this data.`;
            tooltip.style.display = 'none';

            logTelemetry("VISUALIZATION REQUESTED", "process");
            sentinelChat.appendMessage(`VISUALIZING: "${activeSelection.slice(0, 50)}..."`, 'user');

            triggerCouncil(query);
            window.getSelection().removeAllRanges();
            activeSelection = "";
        }
    });
}

// Global listener for highlighted claims
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('claim')) {
        const claimText = e.target.innerText;
        const providerName = e.target.closest('.agent-card')?.querySelector('.ph-model-name')?.innerText || 'Target';

        // Use the new interrogation flow (persona picker → 2 API calls)
        sentinelChat.appendMessage(`Targeting violation: "${claimText}"`, 'user');
        openInterrogation(providerName);
    }
});
// --- KORUM OS - ORBITAL ---
// Consolidated JS for Visuals & Interactions

// --- CONFIG ---
const API_ENDPOINT = "/api/ask";
const SENTINEL_API = "/api/sentinel";

// --- STATE ---
let isProcessing = false;
let orbitalRotation = 0;
let activeSpeaker = null;

// --- DOM ELEMENTS ---
// (Will be populated in init)

// --- SYSTEM STATUS ---

function startProcessingLogs() {
    // Only runs during active Council sessions to show activity
    const logs = ["Initializing Neural Handshake...", "Deconstructing Query...", "Scanning External Sources...", "Validating Architecture...", "Cross-Referencing Data...", "Enforcing Truth Contracts..."];
    let i = 0;
    // We can update the status text instead of a feed
    const interval = setInterval(() => {
        if (i >= logs.length || !document.body.classList.contains("activated")) { clearInterval(interval); return; }
        updateSystemStatus(logs[i]);
        i++;
    }, 800);
}

// --- SENTINEL CHAT LOGIC ---
const sentinelChat = {
    history: [],

    refreshEmptyState: function () {
        const emptyState = document.getElementById('commsEmptyState');
        const hasMessages = document.querySelectorAll('.sentinel-wrapper .chat-message').length > 0;
        if (emptyState) {
            emptyState.classList.toggle('hidden', hasMessages);
        }
    },

    init: function () {
        const input = document.getElementById('sentinelInput');
        const sendBtn = document.getElementById('sentinelSendBtn');

        if (input && sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.sendMessage();
            });
        }

        this.refreshEmptyState();
    },

    sendMessage: async function () {
        const input = document.getElementById('sentinelInput');
        const query = input.value.trim();
        if (!query) return;

        // User Message
        this.appendMessage(query, 'user');
        this.history.push({ role: 'user', content: query });
        input.value = '';
        input.disabled = true;

        try {
            // Sentinel "Thinking" indicator
            const thinkingId = this.appendMessage("Analyzing...", 'sentinel thinking');

            // Send last 6 exchanges (12 messages) for context
            const recentHistory = this.history.slice(-12);

            const response = await authFetch('/api/sentinel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query, history: recentHistory })
            });

            const data = await response.json();

            // Remove thinking indicator
            const thinkingEl = document.getElementById(thinkingId);
            if (thinkingEl) thinkingEl.remove();

            if (data.success) {
                this.appendMessage(data.response, 'sentinel');
                this.history.push({ role: 'assistant', content: data.response });
            } else {
                this.appendMessage("Connection Lost. Re-establishing...", 'sentinel error');
            }
        } catch (e) {
            this.appendMessage("Error: Neural Link Unstable.", 'sentinel error');
            console.error(e);
        } finally {
            input.disabled = false;
            input.focus();
        }
    },

    clear: function () {
        this.history = [];
        const wrapper = document.querySelector('.sentinel-wrapper');
        if (wrapper) wrapper.innerHTML = '';
        this.refreshEmptyState();
        logTelemetry("Global Comms cleared", "system");
    },

    appendMessage: function (text, type) {
        const wrapper = document.querySelector('.sentinel-wrapper');
        if (!wrapper) return null;
        const id = 'msg-' + Date.now();
        const msgDiv = document.createElement('div');
        msgDiv.className = `chat-message ${type}`;
        msgDiv.id = id;

        // Simple markdown parsing for bold/code
        let formatted = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/`(.*?)`/g, '<code style="background:rgba(255,255,255,0.1); padding:2px 4px; border-radius:3px;">$1</code>');

        msgDiv.innerHTML = `<span class="chat-text">${formatted}</span>`;
        wrapper.appendChild(msgDiv);
        this.refreshEmptyState();

        // Auto-scroll to bottom
        const container = document.getElementById('sentinelChat');
        container.scrollTop = container.scrollHeight;

        return id;
    }
};

// Main initialization - consolidates all onload logic
window.onload = async function () {
    console.log("Korum OS Initialized...");

    positionNodes();
    setupActionBindings();
    sentinelChat.init();
    setupInterrogation();
    pushHeartbeat();
    setInterval(pushHeartbeat, 5000);

    // --- INITIALIZATION ---
    // --- INITIALIZATION ---
    // Restore Mission Lock if exists
    // COMMENTED OUT: Forces new session for demo purposes (User Request)
    /*
    const savedMission = localStorage.getItem('korum-mission-context');
    if (savedMission) {
        try {
            sessionState.missionContext = JSON.parse(savedMission);
            sessionState.isMissionLocked = true;
            logTelemetry(`Mission Restored: ${sessionState.missionContext.client}`, "system");
        } catch (e) {
            console.warn("Failed to restore mission context", e);
        }
    }
    */

    // Initialize AI Health Monitoring
    AIHealth.init();
    // Initialize Research Dock
    await ResearchDock.init();
    // Initialize Visualization
    initViz();

    logTelemetry("System Boot Sequence Complete", "system");
};

// UTILS
function getProviderName(key) { const names = { openai: "Strategic Core", anthropic: "Architect", google: "Critic", perplexity: "Intel", mistral: "Analyst", local: "Oracle" }; return names[key] || key; }
function formatText(text) {
    if (!text) return "";
    // Convert intelligence tags into styled inline highlights
    const cleanText = text
        .replace(/\[DECISION_CANDIDATE\]([\s\S]*?)\[\/DECISION_CANDIDATE\]/g, '<span class="intel-tag tag-decision" title="DECISION CANDIDATE">$1</span>')
        .replace(/\[RISK_VECTOR\]([\s\S]*?)\[\/RISK_VECTOR\]/g, '<span class="intel-tag tag-risk" title="RISK VECTOR">$1</span>')
        .replace(/\[METRIC_ANCHOR\]([\s\S]*?)\[\/METRIC_ANCHOR\]/g, '<span class="intel-tag tag-metric" title="KEY METRIC">$1</span>')
        .replace(/\[TRUTH_BOMB\]([\s\S]*?)\[\/TRUTH_BOMB\]/g, '<span class="intel-tag tag-truth" title="VERIFIED FACT">$1</span>')
        // Fallback: strip any unpaired/malformed tags
        .replace(/\[\/?(DECISION_CANDIDATE|RISK_VECTOR|METRIC_ANCHOR|TRUTH_BOMB)\]/g, "");

    return cleanText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/### (.*?)\n/g, '<h4 style="color:#FFF; margin:10px 0;">$1</h4>')
        .replace(/- (.*?)\n/g, '• $1<br>')
        .replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener" style="color:#00DCFF; text-decoration:underline;">$1</a>')
        .replace(/```mermaid([\s\S]*?)```/g, (match, code) => {
            const cleanCode = code.trim().replace(/^mermaid\n/i, '');
            return `<div class="mermaid-container"><div class="mermaid">${cleanCode}</div></div>`;
        })
        .replace(/```([\s\S]*?)```/g, (match, code) => `<pre class="code-block">${code.trim()}</pre>`)
        .replace(/\|(.+)\|/g, (match) => {
            const cells = match.split('|').filter(c => c.trim().length > 0 || match.indexOf(c) > 0);
            if (cells.some(c => c.includes('---'))) return '<hr style="border:0; border-bottom:1px solid #333; margin:10px 0;">';
            return `<div class="table-row" style="display:flex; border-bottom:1px solid rgba(255,255,255,0.05); padding:4px 0;">${cells.map(c => `<div style="flex:1; padding:4px; font-size:11px;">${c.trim()}</div>`).join('')}</div>`;
        });
}
function showErrorCard(msg) { const container = document.querySelector(".results-content"); container.innerHTML = `<div class="consensus-card" style="border-color: red;"><div class="consensus-title" style="color:red;">SYSTEM FAILURE</div><div class="consensus-body">${msg}</div></div>`; document.querySelector(".results-container").classList.add("visible"); }
function closeResults() {
    const container = document.querySelector(".results-container");
    if (container) container.classList.remove("visible");
    setTimeout(() => {
        // Reset UI
        document.body.classList.remove("activated");
        const globe = document.querySelector(".globe");
        if (globe) globe.classList.remove("processing");
        updateSystemStatus("READY");

        // Hide Active Agent Card
        const activeCard = document.getElementById("activeAgentCard");
        if (activeCard) {
            activeCard.classList.remove("visible");
        }

        // Show Recall Button if we have results
        const content = document.querySelector(".results-content");
        if (content && content.children.length > 0) {
            document.getElementById('recallAnalysisBtn').style.display = 'block';
        }
    }, 500);
}
function resetUI() { const btn = document.querySelector('.trigger-scan'); const field = document.querySelector('.glass-textarea'); if (btn) btn.innerText = "Convene Council"; if (field) field.disabled = false; updateSystemStatus("READY"); }
function triggerNetworkAnimation() {
    document.body.classList.add("activated");
    updateSystemStatus("PROCESSING");

    // Energize all nodes for the full council effect
    const nodes = document.querySelectorAll('.node');
    nodes.forEach(n => n.classList.add('selected'));

    animateActivation();
    startProcessingLogs();
}

function animateActivation() {
    const nodes = document.querySelectorAll('.node.selected'); if (nodes.length === 0) return;
    const lightningLayer = document.getElementById('lightning-layer');
    if (!lightningLayer) {
        // Create layer if missing
        const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.id = "lightning-layer";
        svg.style.position = "absolute";
        svg.style.top = "0";
        svg.style.left = "0";
        svg.style.width = "100%";
        svg.style.height = "100%";
        svg.style.pointerEvents = "none";
        svg.style.zIndex = "0";
        document.querySelector('.globe').appendChild(svg);
    }

    // Ensure nodes are positioned correctly before animation
    positionNodes();

    nodes.forEach((node, i) => {
        setTimeout(() => {
            node.classList.add("energized");
            fireLightning(node);
            const interval = setInterval(() => {
                if (document.body.classList.contains("activated")) {
                    fireLightning(node);
                } else {
                    clearInterval(interval);
                    node.classList.remove("energized");
                    node.classList.remove("selected");
                }
            }, 1200 + Math.random() * 1500);
        }, i * 300);
    });
}

function pollV2Progress() {
    authFetch('/api/v2/progress')
        .then(res => res.json())
        .then(data => {
            if (data.status === 'processing') {
                // Continue polling
                setTimeout(pollV2Progress, 1000);
            } else if (data.status === 'complete') {
                updateSystemStatus("SYNTHESIZING");

                // Fetch final result
                authFetch('/api/v2/result')
                    .then(res => res.json())
                    .then(resultData => {
                        renderV2Results(resultData);
                        logTelemetry("Protocol Complete. Rendering Output.", "success");

                        // Start Background Prefetch (Phase 6)
                        PrefetchManager.initPrefetch("current_session", resultData);
                    });
            }
        })
        .catch(err => {
            console.error("V2 Poll Error", err);
            setTimeout(pollV2Progress, 2000);
        });
}

// --- TELEMETRY SYSTEM ---
const telemetryLog = document.getElementById('telemetryLog');
const telemetryEvents = [
    "Analyzing neural weights...",
    "Optimizing context window...",
    "Pinging vector database...",
    "Sanitizing input buffer...",
    "Syncing with global clock...",
    "Verifying API handshake...",
    "Re-calibrating attention heads...",
    "Flushing memory cache...",
    "Encrypting transport layer..."
];

function logTelemetry(msg, type = "info") {
    // 1. Update Scrolling Log (Right Panel)
    if (telemetryLog) {
        const line = document.createElement('div');
        line.className = "log-line";
        line.style.opacity = "0";
        line.style.transform = "translateX(-10px)";
        line.style.transition = "all 0.3s ease";

        // Timestamp
        const now = new Date();
        const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;

        let color = "#888"; // info
        if (type === "process") color = "#00BFFF";
        if (type === "success") color = "#00FF9D";
        if (type === "error") color = "#FF4444";
        if (type === "user") color = "#FFB020";

        line.innerHTML = `<span style="color:#444; margin-right:5px;">[${time}]</span> <span style="color:${color}">${msg}</span>`;

        telemetryLog.appendChild(line);

        // Animate in
        setTimeout(() => {
            line.style.opacity = "1";
            line.style.transform = "translateX(0)";
        }, 50);

        // Keep only last 30 lines
        while (telemetryLog.children.length > 30) {
            telemetryLog.removeChild(telemetryLog.firstChild);
        }
    }

    // 2. Update Micro Tracker (Left Panel)
    const tracker = document.getElementById('tracker-status');
    const trackerMsg = document.getElementById('system-status-text');
    const trackerAgent = document.getElementById('tracker-agent');

    if (tracker && trackerMsg) {
        tracker.style.display = 'flex';
        trackerMsg.innerText = msg.toUpperCase();

        if (msg.includes("GPT") || msg.includes("Strategist")) trackerAgent.innerText = "OPENAI";
        else if (msg.includes("Claude") || msg.includes("Architect")) trackerAgent.innerText = "ANTHROPIC";
        else if (msg.includes("Gemini") || msg.includes("Critic")) trackerAgent.innerText = "GOOGLE";
        else if (msg.includes("Perplexity") || msg.includes("Scout")) trackerAgent.innerText = "PERPLEXITY";
        else if (msg.includes("Mistral") || msg.includes("Analyst")) trackerAgent.innerText = "MISTRAL";
        else if (msg.includes("Oracle")) trackerAgent.innerText = "LOCAL";
        else trackerAgent.innerText = "SYSTEM";

        trackerAgent.style.color = type === 'error' ? '#ff4444' : '#fff';
    }

    // Console Fallback
    console.log(`[TELEMETRY] ${msg}`);
}

// Export to window
window.logTelemetry = logTelemetry;

// Background Heartbeat
setInterval(() => {
    if (Math.random() > 0.7) {
        const randomMsg = telemetryEvents[Math.floor(Math.random() * telemetryEvents.length)];
        logTelemetry(randomMsg, "info");
    }
}, 3500);

logTelemetry("KORUM-OS KERNEL INITIATED", "success");

function fireLightning(node) {
    const svg = document.getElementById('lightning-layer'); if (!svg) return;
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path"); path.classList.add("lightning-path");
    const color = getComputedStyle(node).getPropertyValue('--node-color').trim() || '#FFF'; path.style.stroke = color; svg.appendChild(path);
    const duration = 400; const startTime = Date.now(); const sphere = document.querySelector('.sphere-container');
    function animate() { const elapsed = Date.now() - startTime; if (elapsed > duration) { path.remove(); sphere?.classList.remove('impact'); return; } const nodeRect = node.getBoundingClientRect(); const svgRect = svg.getBoundingClientRect(); const startX = nodeRect.left + nodeRect.width / 2 - svgRect.left; const startY = nodeRect.top + nodeRect.height / 2 - svgRect.top; const endX = svgRect.width / 2; const endY = svgRect.height / 2; const d = generateLightningPath(startX, startY, endX, endY, 8); path.setAttribute("d", d); path.style.opacity = Math.random() > 0.5 ? 1 : 0.3; if (Math.random() > 0.8) sphere?.classList.add('impact'); else sphere?.classList.remove('impact'); requestAnimationFrame(animate); } animate();
}

function generateLightningPath(x1, y1, x2, y2, segments) {
    let d = `M ${x1} ${y1}`;
    const dx = x2 - x1;
    const dy = y2 - y1;
    const len = Math.sqrt(dx * dx + dy * dy);
    const normalX = -dy / len;
    const normalY = dx / len;
    for (let i = 1; i < segments; i++) {
        const t = i / segments;
        let px = x1 + dx * t;
        let py = y1 + dy * t;
        const jitter = (Math.random() - 0.5) * 50 * (1 - t);
        px += normalX * jitter;
        py += normalY * jitter;
        d += ` L ${px} ${py}`;
    }
    d += ` L ${x2} ${y2}`;
    return d;
}

function pushHeartbeat() {
    // Simple heartbeat for system status
    const status = document.getElementById('system-status-text');
    if (status && !document.body.classList.contains('activated')) {
        status.innerText = 'READY';
    }
}

function renderV2Results(data) {
    // Delegate to renderChainResults for V2 pipeline output
    if (data && data.pipeline_result) {
        renderChainResults(data.pipeline_result);
    } else {
        console.warn("[V2] No pipeline_result in data", data);
    }
}

// --- CARD EXPANSION MODAL ---
let currentModalData = null;

function openCardModal(cardData) {
    currentModalData = cardData;
    const modal = document.getElementById('cardModal');
    if (!modal) return;
    document.getElementById('modalTitle').textContent = cardData.name;
    document.getElementById('modalMeta').innerHTML = cardData.meta;
    document.getElementById('modalContent').innerHTML = formatText(cardData.content);
    modal.classList.add('visible');

    if (window.mermaid) {
        setTimeout(() => mermaid.init(undefined, document.querySelectorAll('.card-modal .mermaid')), 100);
    }
    logTelemetry(`Expanded Card: ${cardData.name}`, "system");
}

function closeCardModal() {
    const modal = document.getElementById('cardModal');
    if (modal) modal.classList.remove('visible');
    currentModalData = null;
}

// Modal button handlers
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('closeModal')?.addEventListener('click', (e) => {
        e.stopPropagation();
        closeCardModal();
    });
    document.getElementById('modalCopyBtn')?.addEventListener('click', () => {
        if (currentModalData) {
            navigator.clipboard.writeText(currentModalData.content);
            logTelemetry("Response Copied to Clipboard", "system");
        }
    });
    document.getElementById('cardModal')?.addEventListener('click', (e) => {
        if (e.target.id === 'cardModal') closeCardModal();
    });
});

// updateSystemStatusText defined earlier (line ~1447)

// --- EXPORT TOOLBAR (Rendered in RESULTS PANEL for immediate visibility) ---
function renderExportToolbar(container, _data) {
    const existing = document.querySelector('.export-command-center');
    if (existing) existing.remove();

    const toolbar = document.createElement("div");
    toolbar.className = "export-command-center";

    // Sub-task warning if active
    const subTaskStatus = sessionState.isSubTask ?
        `<div class="sub-task-badge" style="background:#FFB020; color:#000; padding:2px 8px; border-radius:4px; font-size:10px; margin-right:10px; font-weight:700;">SUB-MISSION ACTIVE</div>` : '';

    toolbar.innerHTML = `
        <div class="ecc-label">
            ${subTaskStatus}
            DEPLOY INTELLIGENCE
        </div>
        <div class="ecc-controls">
            <button class="ecc-preview-btn" onclick="PreviewManager.open()" style="background:var(--accent-green); color:#000; border:none; padding:8px 15px; border-radius:6px; cursor:pointer; font-family:var(--font-head); font-size:11px; font-weight:800; margin-right:15px; box-shadow:0 0 15px rgba(0,255,157,0.2);">💎 PREVIEW PACKAGE</button>
            ${sessionState.mainMissionData && sessionState.isSubTask ? `
                <button class="ecc-back-btn" onclick="returnToMainMission()" style="background:rgba(0,188,212,0.2); border:1px solid #00bcd4; color:#00bcd4; padding:8px 12px; border-radius:6px; cursor:pointer; font-family:var(--font-head); font-size:11px; font-weight:700;">↩ RETURN TO MAIN MISSION</button>
            ` : ''}
            <select id="exportDoc" onchange="handleDocExport(this.value)">
                <option value="" disabled selected>Export Report...</option>
                <option value="paper-docx">Research Paper (.docx)</option>
                <option value="paper">Research Paper (PDF)</option>
                <option value="pdf">Board Brief (PDF)</option>
                <option value="docx">Executive Memo (.docx)</option>
                <option value="xlsx">Intelligence Workbook (.xlsx)</option>
                <option value="csv">Flat Data (.csv)</option>
                <option value="json">Raw Intelligence (.json)</option>
                <option value="md">Markdown Brief (.md)</option>
                <option value="txt">Text Report (.txt)</option>
            </select>
            <select id="exportPresent" onchange="handlePresentExport(this.value)">
                <option value="" disabled selected>Create Deck...</option>
                <option value="pptx">PowerPoint (.pptx)</option>
                <option value="slides">Google Slides Draft</option>
                <option value="reveal">Reveal.js</option>
            </select>
            <select id="exportSocial" onchange="handleSocialExport(this.value)">
                <option value="" disabled selected>Share to Social...</option>
                <option value="linkedin">LinkedIn Post</option>
                <option value="twitter">X / Twitter Thread</option>
                <option value="threads">Threads</option>
                <option value="reddit">Reddit Post</option>
                <option value="medium">Medium Article</option>
            </select>
            <button class="ecc-save-btn" onclick="saveReport()" title="Save to Report Library">SAVE</button>
        </div>
    `;

    // Insert at the TOP of results content, before the grid
    container.prepend(toolbar);
}

function returnToMainMission() {
    if (sessionState.mainMissionData) {
        logTelemetry("RECALLING PRIMARY MISSION DATA", "success");
        sessionState.isSubTask = false;

        // Use the appropriate render engine
        if (sessionState.mainMissionData.standard_solution) {
            renderChainResults(sessionState.mainMissionData);
        } else {
            renderResults(sessionState.mainMissionData, sessionState.mainMissionData.roleName || "Main Mission");
        }
    }
}

function handleSocialExport(platform) {
    if (!platform) return;

    if (!lastCouncilData || !lastCouncilData.synthesis) {
        showProcessingToast("No synthesized intelligence available. Execute protocol first.");
        logTelemetry("Social export failed: No synthesis data", "error");
        document.getElementById('exportSocial').selectedIndex = 0;
        return;
    }

    try {
        const social = buildSocialPayload(lastCouncilData.synthesis);
        let url = '';

        if (platform === 'linkedin') {
            url = `https://www.linkedin.com/feed/?shareActive=true&text=${encodeURIComponent(social.linkedin)}`;
            copyTextToClipboard(social.linkedin, "LinkedIn post copied. Opening LinkedIn composer...");
        } else if (platform === 'twitter') {
            url = `https://twitter.com/intent/tweet?text=${encodeURIComponent(social.twitter)}`;
            copyTextToClipboard(social.twitter, "X post copied. Opening composer...");
        } else if (platform === 'threads') {
            url = `https://www.threads.net/intent/post?text=${encodeURIComponent(social.threads)}`;
            copyTextToClipboard(social.threads, "Threads post copied.");
        } else if (platform === 'reddit') {
            const title = social.redditTitle.slice(0, 300);
            url = `https://www.reddit.com/submit?title=${encodeURIComponent(title)}&text=${encodeURIComponent(social.redditBody)}`;
            copyTextToClipboard(`${title}\n\n${social.redditBody}`, "Reddit draft copied. Opening submit page...");
        } else if (platform === 'medium') {
            url = 'https://medium.com/new-story';
            copyTextToClipboard(social.medium, "Medium draft copied. Opening Medium...");
        }

        if (url) window.open(url, '_blank', 'noopener,noreferrer');
        logTelemetry(`Social draft prepared for ${platform.toUpperCase()}`, "success");
    } catch (error) {
        console.error("Social export error:", error);
        logTelemetry(`Social export error: ${error.message}`, "error");
        showProcessingToast(`Social export failed: ${error.message}`);
    }

    document.getElementById('exportSocial').selectedIndex = 0;
}

async function handleDocExport(format) {
    if (!format) return;

    const select = document.getElementById('exportDoc');
    const formatNames = {
        'paper-docx': 'Research Paper (Word)', paper: 'Research Paper', pdf: 'Board Brief', docx: 'Executive Memo', xlsx: 'Intelligence Workbook',
        csv: 'Flat Data', json: 'Raw Intelligence', md: 'Markdown Brief', txt: 'Text Report'
    };

    if (!lastCouncilData || !lastCouncilData.synthesis) {
        showProcessingToast("Execute protocol first to generate intelligence data.");
        logTelemetry("Deployment failed: No synthesis data", "error");
        if (select) select.selectedIndex = 0;
        return;
    }

    // Visual feedback: disable dropdown and show building state
    if (select) select.disabled = true;
    const buildingToast = `Building ${formatNames[format] || format.toUpperCase()}...`;
    showProcessingToast(buildingToast);
    logTelemetry(`DEPLOYING ASSET: ${format.toUpperCase()}...`, "process");

    try {
        const intelligenceObj = { ...lastCouncilData.synthesis };
        // Inject divergence data into intelligence object for exporters
        if (lastCouncilData.divergence) {
            intelligenceObj.divergence_analysis = lastCouncilData.divergence;
        }
        console.log('[EXPORT] Divergence in payload:', !!intelligenceObj.divergence_analysis, intelligenceObj.divergence_analysis);
        const payload = {
            intelligence_object: intelligenceObj,
            card_results: lastCouncilData.results || {},
            format: format,
            mission_context: sessionState.missionContext || null
        };

        const response = await authFetch('/api/deploy_intelligence', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;

            const contentDisposition = response.headers.get('Content-Disposition') || '';
            const serverFilenameMatch = contentDisposition.match(/filename="?([^"]+)"?/i);
            const serverFilename = serverFilenameMatch ? serverFilenameMatch[1] : '';
            const timestamp = formatTimestampForFilename();
            a.download = serverFilename || `korum_intelligence_${timestamp}.${format}`;

            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            logTelemetry(`Intelligence Asset Deployed: ${formatNames[format] || format.toUpperCase()}`, "success");
            showProcessingToast(`${formatNames[format] || format.toUpperCase()} Downloaded`);
        } else {
            const err = await response.json();
            throw new Error(err.error || "Server failed to build asset");
        }
    } catch (error) {
        console.error("Deployment Error", error);
        logTelemetry(`Deployment Error: ${error.message}`, "error");
        showProcessingToast(`Export failed: ${error.message}`);
    }

    // Re-enable and reset dropdown
    if (select) {
        select.disabled = false;
        select.selectedIndex = 0;
    }
}

function formatTimestampForFilename() {
    const d = new Date();
    const pad = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}`;
}

function buildSocialPayload(synthesis) {
    const meta = synthesis.meta || {};
    const sections = synthesis.sections || {};
    const title = meta.title || "Korum Intelligence Brief";
    const summary = (meta.summary || sections.executive_summary || "").trim();

    const bullets = [
        sections.market_analysis,
        sections.technical_architecture,
        sections.risk_assessment,
        sections.strategic_recommendations
    ].filter(Boolean).map(s => `- ${String(s).replace(/\s+/g, ' ').slice(0, 200)}`);

    const base = `${title}\n\n${summary}`.trim();
    const clippedBase = base.slice(0, 1200);

    return {
        linkedin: `${clippedBase}\n\n${bullets.slice(0, 3).join('\n')}\n\n#AI #Strategy #DecisionIntelligence`,
        twitter: `${title}: ${summary}`.replace(/\s+/g, ' ').slice(0, 250),
        threads: `${title}\n${summary}`.slice(0, 450),
        redditTitle: title,
        redditBody: `${summary}\n\n${bullets.join('\n')}`.trim(),
        medium: `# ${title}\n\n${summary}\n\n${Object.entries(sections).map(([k, v]) => `## ${k.replace(/_/g, ' ')}\n\n${v || ''}`).join('\n\n')}`
    };
}

function copyTextToClipboard(text, successMessage) {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
        showProcessingToast(successMessage);
    }).catch(() => {
        showProcessingToast("Draft ready. Copy manually from console output.");
        console.log("Draft content:", text);
    });
}

// Helper: Convert markdown to basic HTML for Word export
function markdownToHtml(md) {
    if (!md) return '';
    return md
        .replace(/^### (.*$)/gm, '<h3>$1</h3>')
        .replace(/^## (.*$)/gm, '<h2>$1</h2>')
        .replace(/^# (.*$)/gm, '<h1>$1</h1>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/```[\s\S]*?```/g, m => `<pre>${m.slice(3, -3)}</pre>`)
        .replace(/^\- (.*$)/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
        .replace(/\n\n/g, '</p><p>')
        .replace(/\|(.+)\|/g, (match) => {
            const cells = match.split('|').filter(c => c.trim());
            if (cells.some(c => /^[-:]+$/.test(c.trim()))) return '';
            return '<tr>' + cells.map(c => `<td>${c.trim()}</td>`).join('') + '</tr>';
        });
}

// Helper: Escape HTML entities
function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function handlePresentExport(format) {
    if (!format) return;
    const names = { slides: "Google Slides", pptx: "PowerPoint", reveal: "Reveal.js" };
    logTelemetry(`Generating ${names[format] || format} Presentation...`, "process");

    if (!lastCouncilData || !lastCouncilData.synthesis) {
        showProcessingToast("No synthesized intelligence available. Execute protocol first.");
        logTelemetry("Presentation export failed: No synthesis data", "error");
        document.getElementById('exportPresent').selectedIndex = 0;
        return;
    }

    if (format === 'pptx') {
        authFetch('/api/generate_preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: 'presentation',
                synthesis: lastCouncilData.synthesis,
                classification: lastCouncilData.classification || {}
            })
        })
            .then(resp => {
                if (!resp.ok) throw new Error(`Preview failed: ${resp.status}`);
                return resp.json();
            })
            .then(preview => {
                if (typeof openArtifactModal === 'function') {
                    openArtifactModal('presentation', preview);
                    logTelemetry("Presentation preview ready", "success");
                } else {
                    throw new Error("Artifact editor not available");
                }
            })
            .catch(err => {
                console.error(err);
                logTelemetry(`Presentation export error: ${err.message}`, "error");
                showProcessingToast(`Error: ${err.message}`);
            })
            .finally(() => {
                document.getElementById('exportPresent').selectedIndex = 0;
            });
        return;
    }

    const social = buildSocialPayload(lastCouncilData.synthesis);
    const extension = format === 'slides' ? 'txt' : 'md';
    const content = format === 'slides'
        ? `Google Slides Draft\n\n${social.medium}`
        : `# Reveal.js Draft\n\n${social.medium}`;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `korum_${format}_draft_${formatTimestampForFilename()}.${extension}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showProcessingToast(`${names[format]} draft downloaded`);
    logTelemetry(`${names[format]} draft generated`, "success");
    document.getElementById('exportPresent').selectedIndex = 0;
}

// --- ACTION PANEL ---
function renderActionPanel(synthesis, classification) {
    const container = document.getElementById('mission-context-panel');
    if (!container || !synthesis) return;

    const meta = synthesis.meta || {};
    const sections = synthesis.sections || {};
    const structured = synthesis.structured_data || {};
    const tags = synthesis.intelligence_tags || {};

    let html = `<div class="exec-brief">`;

    // Header
    html += `<div class="exec-brief-header">
        <div class="exec-brief-title">${meta.title || 'EXECUTIVE INTELLIGENCE BRIEF'}</div>
        <div class="exec-brief-meta">
            <span>${meta.workflow || 'RESEARCH'}</span>
            <span>TRUTH: ${(() => { let s = meta.composite_truth_score; if (s === undefined || s === null) return '—'; s = parseFloat(s); if (s <= 1) s = Math.round(s * 100); return s; })()}/100</span>
            <span>${(meta.models_used || []).length} AGENTS</span>
        </div>
    </div>`;

    // Executive Summary
    if (meta.summary) {
        html += `<div class="exec-brief-summary">${formatText(meta.summary)}</div>`;
    }

    // Sections from synthesis
    const sectionEntries = Object.entries(sections).filter(([, v]) => v && v !== 'Full narrative text...');
    if (sectionEntries.length > 0) {
        html += `<div class="exec-brief-sections">`;
        sectionEntries.forEach(([title, content]) => {
            const displayTitle = title.replace(/_/g, ' ').toUpperCase();
            html += `<div class="exec-brief-section">
                <div class="exec-brief-section-title">${displayTitle}</div>
                <div class="exec-brief-section-body">${formatText(content)}</div>
            </div>`;
        });
        html += `</div>`;
    }

    // Key Metrics
    if (structured.key_metrics?.length) {
        html += `<div class="exec-brief-metrics">
            <div class="exec-brief-section-title">KEY METRICS</div>
            <div class="exec-brief-metrics-grid">`;
        structured.key_metrics.forEach(m => {
            html += `<div class="exec-metric-card">
                <div class="exec-metric-label">${m.metric || ''}</div>
                <div class="exec-metric-value">${m.value || ''}</div>
                <div class="exec-metric-context">${m.context || ''}</div>
            </div>`;
        });
        html += `</div></div>`;
    }

    // Action Items
    if (structured.action_items?.length) {
        html += `<div class="exec-brief-actions">
            <div class="exec-brief-section-title">ACTION ITEMS</div>`;
        structured.action_items.forEach(item => {
            const priorityColor = item.priority === 'high' ? '#FF4444' : item.priority === 'med' ? '#FFB020' : '#00FF9D';
            html += `<div class="exec-action-item">
                <span class="exec-action-priority" style="background:${priorityColor}20; color:${priorityColor}; border:1px solid ${priorityColor}40">${(item.priority || 'med').toUpperCase()}</span>
                <span class="exec-action-task">${item.task || ''}</span>
                ${item.timeline ? `<span class="exec-action-timeline">${item.timeline}</span>` : ''}
            </div>`;
        });
        html += `</div>`;
    }

    // Risks
    if (structured.risks?.length) {
        html += `<div class="exec-brief-risks">
            <div class="exec-brief-section-title">RISK VECTORS</div>`;
        structured.risks.forEach(r => {
            html += `<div class="exec-risk-item">
                <div class="exec-risk-header">
                    <span class="exec-risk-label">${r.risk || ''}</span>
                    <span class="exec-risk-severity">${r.severity || ''}</span>
                </div>
                ${r.mitigation ? `<div class="exec-risk-mitigation">MITIGATION: ${r.mitigation}</div>` : ''}
            </div>`;
        });
        html += `</div>`;
    }

    // Decision Candidates (from intelligence tags)
    if (tags.decisions?.length) {
        html += `<div class="exec-brief-decisions">
            <div class="exec-brief-section-title">DECISION CANDIDATES</div>
            <ul class="exec-decision-list">`;
        tags.decisions.forEach(d => {
            html += `<li>${d}</li>`;
        });
        html += `</ul></div>`;
    }

    html += `</div>`;

    container.innerHTML = html;
    container.style.opacity = '1';
}

// --- PREFETCH MANAGER ---
const PrefetchManager = {
    cache: new Map(),

    async initPrefetch(sessionId, councilData) {
        if (!councilData.synthesis) return;
        this.cache.set(sessionId, {
            synthesis: councilData.synthesis,
            classification: councilData.classification,
            previews: {}
        });
        logTelemetry("Background Prefetch Started...", "system");
    },

    getPreview(sessionId, type) {
        return this.cache.get(sessionId)?.previews[type];
    },

    getSynthesis(sessionId) {
        return this.cache.get(sessionId)?.synthesis;
    },

    getClassification(sessionId) {
        return this.cache.get(sessionId)?.classification;
    }
};

function highlightClaims(html, claims) {
    if (!claims || claims.length === 0) return html;

    // 1. Temporarily pull out Mermaid blocks and Code blocks to avoid breaking syntax
    const placeholders = [];
    let processingHtml = html.replace(/(<div class="mermaid">[\s\S]*?<\/div>|<pre[\s\S]*?<\/pre>)/g, (match) => {
        const id = `##PLACEHOLDER_${placeholders.length}##`;
        placeholders.push({ id, original: match });
        return id;
    });

    // 2. Run Highlight on pure text
    let highlighted = processingHtml;
    const sortedClaims = [...claims].sort((a, b) => b.claim.length - a.claim.length);

    sortedClaims.forEach(c => {
        const claimText = c.claim;
        const status = c.status.toLowerCase();
        const score = c.score;
        const type = c.type;

        // Skip very short claims
        if (claimText.length < 5) return;

        const escapedClaim = claimText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(?![^<]*>)${escapedClaim}`, 'g'); // Regex to avoid matching inside HTML tags

        const replacement = `<span class="claim ${status}" data-status="${status.toUpperCase()} (${score}%)" data-type="${type}" title="VERIFICATION: ${status.toUpperCase()}">${claimText}</span>`;

        highlighted = highlighted.replace(regex, replacement);
    });

    // 3. Put original blocks back
    placeholders.forEach(p => {
        highlighted = highlighted.replace(p.id, p.original);
    });

    return highlighted;
}

// --- PHASE 4: CLIENT PACKAGE PREVIEW MANAGER ---
const PreviewManager = {
    currentData: null,

    init() {
        const modal = document.getElementById('clientPackagePreview');
        if (!modal) return;

        // Close handlers
        document.getElementById('closePreviewBtn')?.addEventListener('click', () => this.close());
        modal.addEventListener('click', (e) => { if (e.target === modal) this.close(); });

        // Deploy PDF button
        document.getElementById('deployPdfBtn')?.addEventListener('click', () => {
            this.close();
            handleDocExport('pdf');
        });

        // Tab switching
        const tabs = document.querySelectorAll('.preview-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                const paneId = `pane-${tab.dataset.tab}`;
                document.querySelectorAll('.preview-pane').forEach(p => p.classList.remove('active'));
                document.getElementById(paneId)?.classList.add('active');
            });
        });
    },

    open() {
        if (!lastCouncilData || !lastCouncilData.synthesis) {
            showProcessingToast("No synthesized intelligence available.");
            return;
        }
        this.populate(lastCouncilData.synthesis, lastCouncilData);
        const modal = document.getElementById('clientPackagePreview');
        modal.style.display = 'flex';
        setTimeout(() => modal.classList.add('visible'), 10);
        logTelemetry("Opening Intelligence Package Preview", "system");
    },

    close() {
        const modal = document.getElementById('clientPackagePreview');
        modal.classList.remove('visible');
        setTimeout(() => modal.style.display = 'none', 300);
    },

    populate(synthesis, fullData) {
        const meta = synthesis.meta || {};
        const sections = synthesis.sections || {};
        const structured = synthesis.structured_data || {};
        const tags = synthesis.intelligence_tags || {};

        document.getElementById('previewTitle').textContent = meta.title || "INTELLIGENCE PACKAGE";
        document.getElementById('previewWorkflow').textContent = meta.workflow || "RESEARCH";
        document.getElementById('previewMeta').textContent = `Mission ID: ${Math.random().toString(36).substr(2, 9).toUpperCase()} | ${meta.generated_at || new Date().toISOString()}`;

        // 1. Executive View — Synthesis + All Agent Responses
        let execHtml = `<h2>EXECUTIVE SUMMARY</h2><p>${meta.summary || "No summary available."}</p>`;
        for (const [title, content] of Object.entries(sections)) {
            const displayTitle = title.replace(/_/g, ' ').toUpperCase();
            execHtml += `<div style="margin-top:25px;"><h3 style="color:var(--accent-green); border-bottom:1px solid rgba(0,255,157,0.1); padding-bottom:10px;">${displayTitle}</h3><div style="margin-top:10px;">${formatText(content)}</div></div>`;
        }

        // Add individual agent responses if available
        const responses = fullData?.responses || fullData?.phases || fullData?.results || {};
        const responseEntries = Object.entries(responses).filter(([, v]) => v && (v.response || v.content || v.text));
        if (responseEntries.length > 0) {
            execHtml += `<div style="margin-top:40px; border-top:1px solid rgba(255,255,255,0.08); padding-top:30px;">
                <h2 style="color:var(--accent-green); margin-bottom:20px;">AGENT INTELLIGENCE</h2>`;
            responseEntries.forEach(([agent, data]) => {
                const content = data.response || data.content || data.text || '';
                const role = data.role || agent.toUpperCase();
                const score = data.truth_score || data.score || null;
                const agentName = agent.toUpperCase();
                execHtml += `
                    <div style="margin-bottom:25px; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.06); border-left:3px solid rgba(0,255,157,0.4); border-radius:8px; padding:20px;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                            <div>
                                <span style="font-size:10px; color:var(--accent-green); font-weight:700; letter-spacing:0.1em;">${agentName}</span>
                                <span style="font-size:10px; color:#666; margin-left:10px;">${role}</span>
                            </div>
                            ${score ? `<span style="font-size:10px; background:rgba(0,255,157,0.1); color:var(--accent-green); padding:2px 8px; border-radius:4px;">${score}/100</span>` : ''}
                        </div>
                        <div style="font-size:13px; line-height:1.7; color:#ccc;">${formatText(content)}</div>
                    </div>`;
            });
            execHtml += `</div>`;
        }

        document.getElementById('execPreviewContent').innerHTML = execHtml;

        // 2. Data & Metrics
        let dataHtml = `<h2>STRATEGIC INTELLIGENCE</h2>`;

        if (structured.key_metrics?.length) {
            dataHtml += `<h3 style="color:#FFF;">KEY METRICS</h3><div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:15px; margin-top:15px;">`;
            structured.key_metrics.forEach(m => {
                dataHtml += `<div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); padding:15px; border-radius:8px;">
                    <div style="font-size:10px; color:#888;">${m.metric}</div>
                    <div style="font-size:18px; color:var(--accent-green); font-weight:700; margin:5px 0;">${m.value}</div>
                    <div style="font-size:11px; color:#666;">${m.context || ""}</div>
                </div>`;
            });
            dataHtml += `</div>`;
        }

        if (tags.decisions?.length) {
            dataHtml += `<h3 style="color:#FFF; margin-top:30px;">DECISION CANDIDATES</h3><ul style="margin-top:15px; color:#CCC;">`;
            tags.decisions.forEach(d => dataHtml += `<li style="margin-bottom:10px; border-left:2px solid var(--accent-gold); padding-left:15px;">${d}</li>`);
            dataHtml += `</ul>`;
        }

        document.getElementById('dataPreviewContent').innerHTML = dataHtml;

        // 3. Slides Preview
        document.getElementById('slidesPreviewContent').innerHTML = `<h2>PRESENTATION DECK PREVIEW</h2><div style="opacity:0.5; padding:40px; text-align:center;">Real-time deck rendering in development... Use 'DEPLOY' for full Powerpoint.</div>`;

        // 4. Public Summary
        const publicSummaries = [
            `LinkedIn: ${meta.title} - ${meta.summary} #AI #Strategy`,
            `X (Twitter): ${meta.summary.slice(0, 240)}...`,
            `Reddit: ${meta.title}\n\nKey Findings:\n${Object.keys(sections).map(s => `- ${s}`).join('\n')}`
        ];
        document.getElementById('publicPreviewContent').innerHTML = `<h2>DEPLOYMENT CHANNELS</h2><div style="padding-top:10px;">${publicSummaries.map(s => `<pre style="background:rgba(0,0,0,0.3); padding:15px; border-radius:6px; font-family:monospace; margin-bottom:15px; white-space:pre-wrap;">${s}</pre>`).join('')}</div>`;
    }
};

// Initialize Preview Manager on load
PreviewManager.init();

// --- SAVED REPORTS CLOSE HANDLERS ---
document.getElementById('closeLibraryBtn')?.addEventListener('click', () => toggleReportLibrary(false));
document.getElementById('libraryOverlay')?.addEventListener('click', () => toggleReportLibrary(false));

// ============================================================
// KORUM WORLDVIEW BRIDGE
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const anomalyId = params.get('worldview_anomaly');
    if (anomalyId) {
        logTelemetry("Korum WorldView Handoff Detected: anomaly_id=" + anomalyId, "system");
        showProcessingToast("Importing context from WorldView Engine...");
        
        // Fetch the anomaly context from WorldView backend (runs on 5001)
        fetch(`http://localhost:5001/api/anomalies/${anomalyId}`)
            .then(res => res.json())
            .then(data => {
                if (data && data.severity) {
                    const qInput = document.getElementById('queryInput');
                    if (qInput) {
                        const eventsText = (data.contributing_events || []).slice(0, 10).map(e => 
                            `- [${(e.feed_type || 'UNKNOWN').toUpperCase()}] ${e.title || 'Event'} at ${parseFloat(e.latitude).toFixed(2)},${parseFloat(e.longitude).toFixed(2)}`
                        ).join('\n');

                        qInput.value = `[KORUM WORLDVIEW DIRECTIVE]\nPRIORITY: ${data.severity}\nLOCATION: H3 Cell ${data.h3_cell}\n\nCORRELATED INTELLIGENCE:\n${eventsText}\n\nProvide an immediate threat assessment, kinetic escalation pathways, and recommended countermeasures for this anomaly cluster.`;
                        
                        // Auto-show the intake modal since the query is prepopulated
                        const modal = document.getElementById('intakeModal');
                        if (modal) {
                            modal.style.display = 'flex';
                            // Switch to War Room DNA naturally
                            const workflowSelect = document.getElementById('workflowSelect');
                            if (workflowSelect) workflowSelect.value = 'WAR_ROOM';
                        }
                        showProcessingToast("Context Imported Successfully!");
                    }
                }
            })
            .catch(err => {
                console.error("WorldView Bridge Error: Could not fetch anomaly data", err);
                logTelemetry("WorldView context sync failed", "error");
            });
    }
});

// ============================================================
// AUDIT LOG PANEL
// ============================================================
const AuditPanel = {
    logs: [],

    open() {
        document.getElementById('auditPanel')?.classList.add('open');
        document.getElementById('auditOverlay')?.classList.add('active');
        this.load();
    },

    close() {
        document.getElementById('auditPanel')?.classList.remove('open');
        document.getElementById('auditOverlay')?.classList.remove('active');
    },

    async load() {
        const list = document.getElementById('auditList');
        const stats = document.getElementById('auditStats');
        if (!list) return;
        list.innerHTML = '<div class="library-empty">Loading audit log...</div>';

        try {
            const res = await authFetch('/api/auth/audit?limit=500');
            const data = await res.json();
            if (!data.success) {
                list.innerHTML = `<div class="library-empty">Error: ${data.error || 'Access denied'}</div>`;
                return;
            }
            this.logs = data.logs || [];
            this.renderStats(stats);
            this.render();
        } catch (e) {
            list.innerHTML = `<div class="library-empty">Failed to load audit log. Admin access required.</div>`;
        }
    },

    renderStats(container) {
        if (!container) return;
        const counts = { council_query: 0, interrogation: 0, verify_claim: 0, login: 0, login_failed: 0 };
        this.logs.forEach(l => { if (counts[l.event_type] !== undefined) counts[l.event_type]++; });
        container.innerHTML = `
            <div class="audit-stat"><span class="audit-stat-value">${counts.council_query}</span><span class="audit-stat-label">Queries</span></div>
            <div class="audit-stat"><span class="audit-stat-value">${counts.interrogation}</span><span class="audit-stat-label">Interrogations</span></div>
            <div class="audit-stat"><span class="audit-stat-value">${counts.verify_claim}</span><span class="audit-stat-label">Verifications</span></div>
            <div class="audit-stat"><span class="audit-stat-value">${counts.login}</span><span class="audit-stat-label">Logins</span></div>
            <div class="audit-stat"><span class="audit-stat-value">${counts.login_failed}</span><span class="audit-stat-label">Failed</span></div>
        `;
    },

    render() {
        const list = document.getElementById('auditList');
        const filter = document.getElementById('auditFilter')?.value || 'all';
        const filtered = filter === 'all' ? this.logs : this.logs.filter(l => l.event_type === filter);

        if (filtered.length === 0) {
            list.innerHTML = '<div class="library-empty">No audit events found.</div>';
            return;
        }

        list.innerHTML = filtered.map(l => {
            const ts = l.timestamp ? new Date(l.timestamp).toLocaleString() : 'N/A';
            const eventLabel = (l.event_type || 'unknown').replace(/_/g, ' ').toUpperCase();

            // Parse details for council queries
            let detailsHtml = '';
            if (l.details) {
                const parts = l.details.split(' | ');
                detailsHtml = parts.map(p => {
                    const [key, ...val] = p.split('=');
                    const v = val.join('=');
                    if (key === 'query') return `<div><strong>Query:</strong> ${v}</div>`;
                    if (key === 'providers') return `<div><strong>Providers:</strong> ${v}</div>`;
                    if (key === 'truth_score') return `<div><strong>Truth Score:</strong> ${v}</div>`;
                    if (key === 'workflow') return `<div><strong>Workflow:</strong> ${v}</div>`;
                    if (key === 'attacker') return `<div><strong>Attacker:</strong> ${v.toUpperCase()}</div>`;
                    if (key === 'defender') return `<div><strong>Defender:</strong> ${v.toUpperCase()}</div>`;
                    if (key === 'claim') return `<div><strong>Claim:</strong> ${v}</div>`;
                    if (key === 'model' || key === 'attacker_model' || key === 'defender_model') return `<div><strong>${key.replace(/_/g, ' ')}:</strong> ${v}</div>`;
                    if (key === 'red_team') return v === 'True' ? `<div><strong>Red Team:</strong> ACTIVE</div>` : '';
                    return `<div>${p}</div>`;
                }).join('');
            }

            return `<div class="audit-entry ${l.event_type || ''}">
                <div class="audit-entry-header">
                    <span class="audit-event-type">${eventLabel}</span>
                    <span class="audit-timestamp">${ts}</span>
                </div>
                ${l.user_email ? `<div class="audit-user">${l.user_email}</div>` : ''}
                ${detailsHtml ? `<div class="audit-details">${detailsHtml}</div>` : ''}
                ${l.ip_address ? `<div class="audit-ip">${l.ip_address}</div>` : ''}
            </div>`;
        }).join('');
    }
};

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('auditNavBtn')?.addEventListener('click', () => AuditPanel.open());
    document.getElementById('closeAuditBtn')?.addEventListener('click', () => AuditPanel.close());
    document.getElementById('auditOverlay')?.addEventListener('click', () => AuditPanel.close());
    document.getElementById('auditRefreshBtn')?.addEventListener('click', () => AuditPanel.load());
    document.getElementById('auditFilter')?.addEventListener('change', () => AuditPanel.render());
});
