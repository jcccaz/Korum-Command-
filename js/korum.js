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

// Handle window resizing to clean up mobile states
window.addEventListener('resize', () => {
    if (window.innerWidth > 768) {
        document.querySelector('.nav-links')?.classList.remove('mobile-open');
        document.body.classList.remove('mobile-nav-open');
    }
});

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
async function authFetch(url, options = {}, timeoutMs = 120000) {
    options.credentials = 'include';
    const controller = new AbortController();
    options.signal = controller.signal;
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    let response;
    try {
        response = await fetch(url, options);
    } catch (e) {
        clearTimeout(timer);
        if (e.name === 'AbortError') {
            throw new Error('Request timed out — the server took too long to respond. Please try again.');
        }
        throw e;
    }
    clearTimeout(timer);
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

// --- PROVIDER MAPPING (Mythical Labels) ---
const PROVIDER_MYTHICAL_LABELS = {
    "openai": "Odin / OpenAI",
    "anthropic": "Tyr / Claude",
    "google": "Heimdall / Gemini",
    "perplexity": "Huginn / Perplexity",
    "mistral": "Mimir / Mistral",
    "local": "Oracle / Local AI"
};

function resolveProviderKey(name) {
    if (!name) return null;
    const clean = name.replace(/[^a-zA-Z0-9\s_()-]/g, '').trim();
    
    // Check mythical labels first
    for (const [key, label] of Object.entries(PROVIDER_MYTHICAL_LABELS)) {
        if (clean === label || clean.includes(label)) return key;
    }

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
            logTelemetry(`Save failed: ${data.error}`, "error");
            showProcessingToast("Report could not be saved. Please try again.");
        }
    } catch (e) {
        logTelemetry(`Save report error: ${e.message}`, "error");
        showProcessingToast("Report could not be saved. Please try again.");
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
            list.innerHTML = `<div class="library-empty">Unable to load reports. Please refresh and try again.</div>`;
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
        logTelemetry(`Report library error: ${e.message}`, "error");
        list.innerHTML = `<div class="library-empty">Unable to load reports. Please refresh and try again.</div>`;
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
        logTelemetry(`Report recall error: ${e.message}`, "error");
        showProcessingToast("Unable to recall report. Please try again.");
    }
}

async function deleteReport(id) {
    if (!confirm("Delete this saved report?")) return;
    try {
        await authFetch(`/api/reports/${id}`, { method: 'DELETE' });
        logTelemetry(`Report deleted: ${id}`, "system");
        loadReportLibrary(); // Refresh list
    } catch (e) {
        logTelemetry(`Report delete error: ${e.message}`, "error");
        showProcessingToast("Unable to delete report. Please try again.");
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
        document.body.classList.add('report-library-open');
        sessionState.archivePanelOpen = true;
        loadReportLibrary();
    } else {
        panel.classList.remove('visible');
        if (overlay) overlay.classList.remove('visible');
        document.body.classList.remove('report-library-open');
        sessionState.archivePanelOpen = false;
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
                const container = document.getElementById('pane-analysis') || document.querySelector(".results-content");
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
        const cleanText = text
            .replace(/\[DECISION_CANDIDATE\]([\s\S]*?)\[\/DECISION_CANDIDATE\]/g, '<span class="intel-tag tag-decision" title="DECISION CANDIDATE">$1</span>')
            .replace(/\[RISK_VECTOR\]([\s\S]*?)\[\/RISK_VECTOR\]/g, '<span class="intel-tag tag-risk" title="RISK VECTOR">$1</span>')
            .replace(/\[METRIC_ANCHOR\]([\s\S]*?)\[\/METRIC_ANCHOR\]/g, '<span class="intel-tag tag-metric" title="KEY METRIC">$1</span>')
            .replace(/\[TRUTH_BOMB\]([\s\S]*?)\[\/TRUTH_BOMB\]/g, '<span class="intel-tag tag-truth" title="VERIFIED FACT">$1</span>')
            .replace(/\[\/?(DECISION_CANDIDATE|RISK_VECTOR|METRIC_ANCHOR|TRUTH_BOMB)\]/g, "");

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
                logTelemetry("Dock loaded from Mission Intelligence Cloud", "system");
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

    hideHighlightToolbar();

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
const activeModes = { v2: true, red: false, serp: false, falcon: false };

function toggleMode(mode) {
    const btn = document.getElementById(`btn-mode-${mode}`);
    if (!btn) return;

    activeModes[mode] = !activeModes[mode];
    const isActive = activeModes[mode];

    btn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    btn.classList.toggle('mode-active-v2', mode === 'v2' && isActive);
    btn.classList.toggle('mode-active-red', mode === 'red' && isActive);
    btn.classList.toggle('mode-active-serp', mode === 'serp' && isActive);
    btn.classList.toggle('mode-active-falcon', mode === 'falcon' && isActive);

    if (isActive) {
        btn.classList.add('active');
        logTelemetry(`${mode.toUpperCase()} MODE ACTIVATED`, "warning");
        if (mode === 'falcon') {
            document.querySelector('.falcon-brand-container')?.classList.add('falcon-active');
        }
    } else {
        btn.classList.remove('active');
        logTelemetry(`${mode.toUpperCase()} MODE STANDBY`, "system");
        if (mode === 'falcon') {
            document.querySelector('.falcon-brand-container')?.classList.remove('falcon-active');
        }
    }

    // Falcon level picker + custom terms + ghost preview visibility
    if (mode === 'falcon') {
        const levelPicker = document.getElementById('falcon-level-select');
        if (levelPicker) levelPicker.style.display = isActive ? 'inline-block' : 'none';
        const termsPanel = document.getElementById('falcon-custom-terms');
        if (termsPanel) termsPanel.style.display = isActive ? 'block' : 'none';
        const ghostBtn = document.getElementById('ghostPreviewBtn');
        if (ghostBtn) ghostBtn.style.display = isActive ? 'inline-flex' : 'none';
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
                    const rsOai = document.getElementById('roleSelectOpenAI');
                    const rsAnt = document.getElementById('roleSelectAnthropic');
                    const rsGoo = document.getElementById('roleSelectGoogle');
                    const rsPer = document.getElementById('roleSelectPerplexity');
                    if (rsOai) rsOai.value = suggestedRoles.openai;
                    if (rsAnt) rsAnt.value = suggestedRoles.anthropic;
                    if (rsGoo) rsGoo.value = suggestedRoles.google;
                    if (rsPer) rsPer.value = suggestedRoles.perplexity;
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

    document.querySelector('.suggestion-dismiss-btn')?.addEventListener('click', () => {
        if (suggestionBox) suggestionBox.classList.add('hidden');
        if (roleCustomization) roleCustomization.classList.add('hidden');
    });

    document.getElementById('clearInputBtn')?.addEventListener('click', () => {
        if (queryInput) queryInput.value = '';
        logTelemetry("Input Cleared", "system");
    });

    // FALCON CUSTOM TERMS
    const falconTermInput = document.getElementById('falconTermInput');
    const falconTermAddBtn = document.getElementById('falconTermAddBtn');
    const falconTermsList = document.getElementById('falconTermsList');
    window._falconCustomTerms = [];

    function addFalconTerm(term) {
        term = term.trim();
        if (!term || window._falconCustomTerms.includes(term)) return;
        window._falconCustomTerms.push(term);
        const chip = document.createElement('span');
        chip.className = 'falcon-term-chip';
        chip.innerHTML = `${term} <span class="falcon-term-remove" data-term="${term}">&times;</span>`;
        chip.querySelector('.falcon-term-remove').addEventListener('click', () => {
            window._falconCustomTerms = window._falconCustomTerms.filter(t => t !== term);
            chip.remove();
        });
        falconTermsList?.appendChild(chip);
    }

    falconTermAddBtn?.addEventListener('click', () => {
        if (falconTermInput?.value) {
            addFalconTerm(falconTermInput.value);
            falconTermInput.value = '';
            falconTermInput.focus();
        }
    });
    falconTermInput?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            if (falconTermInput.value) {
                addFalconTerm(falconTermInput.value);
                falconTermInput.value = '';
            }
        }
    });

    // NEW SESSION RESET
    document.getElementById('resetSessionBtn')?.addEventListener('click', () => {
        // Clear input
        if (queryInput) queryInput.value = '';
        // Close and clear results dock
        const dock = document.querySelector('.results-container');
        if (dock) dock.classList.remove('visible', 'active');
        const councilPane = document.getElementById('pane-council');
        if (councilPane) councilPane.innerHTML = '';
        const analysisPane = document.getElementById('pane-analysis');
        if (analysisPane) analysisPane.innerHTML = '';
        // Clear comms log
        const commsLog = document.getElementById('comms-log');
        if (commsLog) commsLog.innerHTML = '<div class="comms-empty-text">Submit a query to start.</div>';
        // Reset all UI state
        resetUI();
        // Hide recall and reset button
        const recallBtn = document.getElementById('recallAnalysisBtn');
        if (recallBtn) recallBtn.style.display = 'none';
        document.getElementById('resetSessionBtn').style.display = 'none';
        // Clear stored data
        lastCouncilData = null;
        lastQueryText = '';
        logTelemetry("Session Reset — Ready for new query", "system");
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
    const mobileNavToggle = document.getElementById('mobileNavToggle');
    const navMenu = document.querySelector('.nav-links');
    if (navMenu && !navMenu.id) navMenu.id = 'workflowNav';
    if (mobileNavToggle && navMenu) {
        mobileNavToggle.setAttribute('aria-controls', navMenu.id);
        mobileNavToggle.setAttribute('aria-expanded', 'false');
    }

    const closeMobileNav = () => {
        if (!navMenu || !mobileNavToggle) return;
        navMenu.classList.remove('mobile-open');
        mobileNavToggle.setAttribute('aria-expanded', 'false');
        document.body.classList.remove('mobile-nav-open');
    };

    const openMobileNav = () => {
        if (!navMenu || !mobileNavToggle) return;
        navMenu.classList.add('mobile-open');
        mobileNavToggle.setAttribute('aria-expanded', 'true');
        document.body.classList.add('mobile-nav-open');
    };

    mobileNavToggle?.addEventListener('click', () => {
        if (navMenu?.classList.contains('mobile-open')) {
            closeMobileNav();
        } else {
            openMobileNav();
        }
    });

    // Close mobile nav when a workflow is selected
    document.querySelectorAll('.nav-links a').forEach(a => {
        a.addEventListener('click', () => {
            closeMobileNav();
        });
    });

    // Close mobile nav on tap outside
    document.addEventListener('click', (e) => {
        if (navMenu?.classList.contains('mobile-open') && !navMenu.contains(e.target) && !mobileNavToggle?.contains(e.target)) {
            closeMobileNav();
        }
    });

    // Close mobile nav with Escape or when switching to desktop width
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeMobileNav();
    });
    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) closeMobileNav();
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
        if (agentCard && !target.closest('button') && !target.closest('.tool-action') && !target.closest('.analysis-action-bar')) {
            // Special cards (divergence, exec-brief, verify, interrogation) open modal directly
            if (agentCard.classList.contains('no-interrogate') || agentCard.classList.contains('divergence-card') || agentCard.classList.contains('exec-brief-card')) {
                openCardModal({
                    name: agentCard.dataset.name || agentCard.querySelector('.ph-model-name')?.innerText || 'Analysis',
                    meta: '',
                    content: agentCard.querySelector('.agent-response, .exec-brief, .divergence-summary')?.innerHTML || agentCard.innerHTML
                });
            } else {
                selectCard(agentCard);
            }
        }

        // Consensus card — open modal on click
        const consensusCard = target.closest('.consensus-card');
        if (consensusCard) {
            openCardModal({
                name: 'COUNCIL DECISION',
                meta: '',
                content: consensusCard.querySelector('.consensus-body')?.innerHTML || consensusCard.innerHTML
            });
        }

        // Deselect when clicking empty space
        if (target.classList.contains('results-content') || target.classList.contains('results-grid') || target.classList.contains('dock-pane')) {
            deselectCard();
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

    const isV2 = activeModes.v2;

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
        // Show New Session button
        document.getElementById('resetSessionBtn').style.display = 'block';
    }
}

async function executeReasoningChain(query) {
    logTelemetry("Initiating V2 Functional Pipeline...", "system");
    triggerNetworkAnimation(); // FIRE LIGHTNING

    // Check Hacker Toggle
    const hackerMode = activeModes.red || document.getElementById('hackerToggle')?.checked || false;

    // Build role config from deck (same logic as executeCouncil)
    let roleConfig;
    if (customRolesActive) {
        roleConfig = {
            openai: document.getElementById('roleLabel-openai')?.innerText.toLowerCase() || 'strategist',
            anthropic: document.getElementById('roleLabel-anthropic')?.innerText.toLowerCase() || 'architect',
            google: document.getElementById('roleLabel-google')?.innerText.toLowerCase() || 'critic',
            perplexity: document.getElementById('roleLabel-perplexity')?.innerText.toLowerCase() || 'scout',
            mistral: document.getElementById('roleLabel-mistral')?.innerText.toLowerCase() || 'analyst',
            local: document.getElementById('roleLabel-local')?.innerText.toLowerCase() || 'oracle'
        };
    } else {
        const activeRoleName = document.querySelector('.nav-links a.active')?.dataset.role || 'System Core';
        roleConfig = PROTOCOL_CONFIGS[activeRoleName] || PROTOCOL_CONFIGS['System Core'];
        if (!roleConfig.mistral) roleConfig.mistral = "analyst";
        if (!roleConfig.local) roleConfig.local = "oracle";
    }

    const payload = {
        query: query,
        depth: "standard",
        hacker_mode: hackerMode,
        workflow: sessionState.missionContext?.workflow || "RESEARCH",
        council_roles: roleConfig,
        active_models: ["openai", "anthropic", "google", "perplexity", "mistral", "local"].filter(p =>
            AIHealth.isAvailable(p) && !document.querySelector(`.deck-card.${p}`)?.classList.contains('silenced')
        ),
        use_falcon: activeModes.falcon,
        falcon_level: document.getElementById('falcon-level-select')?.value || 'STANDARD',
        falcon_custom_terms: window._falconCustomTerms || []
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
        if (data.execution_metrics) {
            renderExecutionDashboard(data.execution_metrics);
        }
    } else {
        throw new Error(data.error || "Pipeline Failed");
    }
    resetUI();
}

function renderChainResults(result) {
    const councilPane = document.getElementById('pane-council');
    const analysisPane = document.getElementById('pane-analysis');
    const interPane = document.getElementById('pane-interrogation');
    councilPane.innerHTML = "";
    analysisPane.innerHTML = "";
    interPane.innerHTML = '<div class="interrogation-empty-state">No interrogation or verification results yet.</div>';

    // Store for export functionality — use backend synthesis when available
    const totalTime = (result.metrics?.deconstruct?.time || 0) + (result.metrics?.build?.time || 0) +
                      (result.metrics?.stress?.time || 0) + (result.metrics?.synthesize?.time || 0);
    const backendSynthesis = result.synthesis || {};
    const backendMeta = backendSynthesis.meta || {};
    const backendStructured = backendSynthesis.structured_data || {};

    const synthesisData = {
        meta: {
            title: backendMeta.title || (sessionState.originalQuery || 'V2 Reasoning Chain Analysis').substring(0, 120).split('\n')[0],
            summary: backendMeta.summary || result.final_artifact || '',
            workflow: backendMeta.workflow || sessionState.missionContext?.workflow || 'RESEARCH',
            models_used: backendMeta.models_used || [],
            composite_truth_score: backendMeta.composite_truth_score || 85,
            generated_at: backendMeta.generated_at || new Date().toISOString()
        },
        sections: backendSynthesis.sections || {
            executive_summary: result.final_artifact || '',
            constraint_analysis: result.constraints || '',
            architecture: result.standard_solution || '',
            stress_test: result.failure_analysis || ''
        },
        structured_data: {
            key_metrics: backendStructured.key_metrics || [
                { metric: 'Pipeline Phases', value: result.exploit_poc ? '5' : '4', context: 'Sequential reasoning chain' },
                { metric: 'Total Execution Time', value: `${totalTime.toFixed(1)}s`, context: 'Across all phases' }
            ],
            risks: backendStructured.risks || [],
            actions: backendStructured.actions || []
        },
        // Pass through council_contributors from backend synthesis
        council_contributors: backendSynthesis.council_contributors || [],
        confidence_and_assumptions: backendSynthesis.confidence_and_assumptions || null
    };
    // Supplement risks from RISK_VECTOR tags if backend didn't provide structured risks
    if (!backendStructured.risks || backendStructured.risks.length === 0) {
        const riskMatches = (result.failure_analysis || '').match(/\[RISK_VECTOR\](.*?)\[\/RISK_VECTOR\]/g) || [];
        riskMatches.forEach(r => {
            const text = r.replace(/\[\/?\s*RISK_VECTOR\s*\]/g, '').trim();
            synthesisData.structured_data.risks.push({ risk: text, severity: 'HIGH', mitigation: 'Requires assessment' });
        });
    }
    // Supplement actions from DECISION_CANDIDATE tags if backend didn't provide them
    if (!backendStructured.actions || backendStructured.actions.length === 0) {
        const actionMatches = (result.failure_analysis || '').match(/\[DECISION_CANDIDATE\](.*?)\[\/DECISION_CANDIDATE\]/g) || [];
        actionMatches.forEach(a => {
            const text = a.replace(/\[\/?\s*DECISION_CANDIDATE\s*\]/g, '').trim();
            synthesisData.structured_data.actions.push({ action: text, priority: 'HIGH' });
        });
    }
    if (result.exploit_poc) {
        synthesisData.sections.red_team_analysis = result.exploit_poc;
    }
    lastCouncilData = {
        synthesis: synthesisData,
        results: result.results || {},
        roleName: 'V2 Reasoning Chain',
        pipeline_result: result
    };

    // Export toolbar
    renderExportToolbar(councilPane, lastCouncilData);

    // ANALYSIS tab — cross-phase comparison + full content cards
    const analysisGrid = document.createElement("div");
    analysisGrid.className = "results-grid";

    // Cross-phase comparison card
    const allRisks = riskMatches.map(r => r.replace(/\[\/?\s*RISK_VECTOR\s*\]/g, '').trim());
    const allActions = actionMatches.map(a => a.replace(/\[\/?\s*DECISION_CANDIDATE\s*\]/g, '').trim());
    const truthBombs = [...(result.constraints || ''), ...(result.standard_solution || ''), ...(result.failure_analysis || ''), ...(result.final_artifact || '')]
        .join?.('') || '';
    const tbMatches = ((result.constraints || '') + (result.standard_solution || '') + (result.failure_analysis || '') + (result.final_artifact || ''))
        .match(/\[TRUTH_BOMB\](.*?)\[\/TRUTH_BOMB\]/g) || [];

    const comparisonCard = document.createElement("div");
    comparisonCard.className = "agent-card no-interrogate";
    comparisonCard.dataset.name = "CROSS-PHASE ANALYSIS";
    comparisonCard.style.gridColumn = "1 / -1";
    comparisonCard.innerHTML = `
        <div class="precision-header">
            <div class="ph-left">
                <div class="ph-model-name">CROSS-PHASE INTELLIGENCE SUMMARY</div>
                <div class="ph-role-label">Aggregated findings across all pipeline phases</div>
            </div>
            <div class="ph-right">
                <div class="metric-pill">${tbMatches.length} FACTS</div>
                <div class="metric-pill" style="border-color:#FF4444; color:#FF4444;">${allRisks.length} RISKS</div>
                <div class="metric-pill" style="border-color:#00E5FF; color:#00E5FF;">${allActions.length} ACTIONS</div>
                <div class="metric-pill time">${totalTime.toFixed(1)}s</div>
            </div>
        </div>
        <div class="agent-response" style="font-size:0.62rem; line-height:1.7;">
            ${allRisks.length ? `<div style="margin-bottom:12px;"><strong style="color:#FF4444;">RISK VECTORS IDENTIFIED</strong><br>${allRisks.map(r => `<span style="color:#CCC;">• ${r}</span>`).join('<br>')}</div>` : ''}
            ${allActions.length ? `<div style="margin-bottom:12px;"><strong style="color:#00E5FF;">RECOMMENDED ACTIONS</strong><br>${allActions.map(a => `<span style="color:#CCC;">• ${a}</span>`).join('<br>')}</div>` : ''}
            ${tbMatches.length ? `<div><strong style="color:#00FF9D;">VERIFIED FACTS (${tbMatches.length})</strong><br>${tbMatches.slice(0, 8).map(t => `<span style="color:#999;">• ${t.replace(/\[\/?\s*TRUTH_BOMB\s*\]/g, '').trim()}</span>`).join('<br>')}${tbMatches.length > 8 ? `<br><span style="color:#555;">...and ${tbMatches.length - 8} more</span>` : ''}</div>` : ''}
        </div>
    `;
    analysisGrid.appendChild(comparisonCard);

    // Full phase content cards
    const phases = [
        { label: 'DECONSTRUCTION', content: result.constraints, metric: result.metrics?.deconstruct, provider: 'anthropic' },
        { label: 'ARCHITECTURE', content: result.standard_solution, metric: result.metrics?.build, provider: 'openai' },
        { label: 'STRESS TEST', content: result.failure_analysis, metric: result.metrics?.stress, provider: 'google' },
        { label: 'EXECUTION', content: result.final_artifact, metric: result.metrics?.synthesize, provider: 'openai' }
    ];
    phases.forEach(p => {
        if (!p.content) return;
        const card = document.createElement("div");
        card.className = `agent-card no-interrogate ${p.provider}`;
        card.dataset.name = p.label;
        card.innerHTML = `
            <div class="precision-header">
                <div class="ph-left">
                    <div class="ph-model-name">${p.label}</div>
                    <div class="ph-role-label">Full Phase Output</div>
                </div>
                <div class="ph-right">
                    <div class="metric-pill time">${(p.metric?.time || 0).toFixed(1)}s</div>
                    <div class="tool-action" onclick="event.stopPropagation(); copyTextToClipboard(this.closest('.agent-card').querySelector('.agent-response').innerText, '${p.label} copied')" title="Copy">📋</div>
                </div>
            </div>
            <div class="agent-response">${formatText(p.content)}</div>
        `;
        analysisGrid.appendChild(card);
    });
    analysisPane.appendChild(analysisGrid);
    const grid = document.createElement("div");
    grid.className = "results-grid";

    // Helper to create phase cards
    const createCard = (title, model, content, phase, metricData) => {
        const card = document.createElement("div");
        card.className = `agent-card ${model.toLowerCase().includes('gpt') ? 'openai' : model.toLowerCase().includes('claude') ? 'anthropic' : 'google'}`;
        card.dataset.name = title;
        card.dataset.meta = `<div class="agent-meta"><span>${phase}</span><span>${model}</span></div>`;
        card.dataset.rawContent = encodeURIComponent(content);

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

    councilPane.appendChild(grid);
    document.querySelector(".results-container").classList.add("visible");
    switchDockTab('council');
    document.getElementById('recallAnalysisBtn').style.display = 'none';

    // Populate sessionState.lastResponses so follow-ups and interrogations have context
    if (result.constraints) sessionState.lastResponses['anthropic'] = result.constraints;
    if (result.standard_solution) sessionState.lastResponses['openai'] = result.standard_solution;
    if (result.failure_analysis) sessionState.lastResponses['google'] = result.failure_analysis;
    if (result.final_artifact) sessionState.lastResponses['openai_exec'] = result.final_artifact;

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
    isMissionLocked: false,
    threadHistory: [],  // Follow-up memory: accumulates prior session summaries
    activeThreadId: null, // Persistent thread UUID (server-side)
    selectedCardId: null,
    selectedCardProvider: null,
    selectedCardResponse: null,
    selectedText: "",
    highlightToolbarVisible: false,
    archivePanelOpen: false
};

// --- CARD SELECTION & ANALYSIS ACTION BAR ---

function selectCard(cardEl) {
    // Remove selection from all cards
    document.querySelectorAll('.agent-card.card-selected').forEach(c => {
        c.classList.remove('card-selected');
        c.querySelector('.analysis-action-bar')?.remove();
    });

    if (!cardEl || cardEl.classList.contains('no-interrogate')) return;

    // Infer provider if card is missing data-provider (legacy/special cards)
    if (!cardEl.dataset.provider) {
        const nameHint = cardEl.dataset.name || cardEl.querySelector('.ph-model-name, .agent-name')?.innerText || '';
        const inferredProvider = resolveProviderKey(nameHint);
        if (inferredProvider) cardEl.dataset.provider = inferredProvider;
    }

    // Select this card
    cardEl.classList.add('card-selected');
    sessionState.selectedCardId = cardEl.dataset.cardId || null;
    sessionState.selectedCardProvider = cardEl.dataset.provider || null;
    sessionState.selectedCardResponse = cardEl.querySelector('.agent-response')?.innerText || '';

    // Inject action bar after known card headers (for backward compatibility/hover-like selection)
    const actionBar = buildAnalysisActionBar();
    const header = cardEl.querySelector('.precision-header, .agent-header');
    if (header) {
        header.insertAdjacentElement('afterend', actionBar);
    } else {
        cardEl.insertAdjacentElement('afterbegin', actionBar);
    }

    // NEW: Card Expansion on Selection
    const provider = cardEl.dataset.provider || "";
    const name = cardEl.dataset.name || getProviderName(provider);
    const content = cardEl.querySelector('.agent-response')?.innerText || "";
    const model = cardEl.querySelector('.ph-role-label')?.innerText || provider;

    openCardModal({
        name: name,
        provider: provider,
        meta: `<div class="agent-meta"><span>${provider.toUpperCase()}</span><span>${model}</span></div>`,
        content: content,
        model: model
    });
}

function deselectCard() {
    document.querySelectorAll('.agent-card.card-selected').forEach(c => {
        c.classList.remove('card-selected');
        c.querySelector('.analysis-action-bar')?.remove();
    });
    sessionState.selectedCardId = null;
    sessionState.selectedCardProvider = null;
    sessionState.selectedCardResponse = null;
}

function buildAnalysisActionBar() {
    const bar = document.createElement('div');
    bar.className = 'analysis-action-bar';
    bar.innerHTML = `
        <button class="aab-btn aab-interrogate" data-action="interrogate">
            <span class="aab-icon">&#x1F50D;</span> INTERROGATE
        </button>
        <button class="aab-btn aab-verify" data-action="verify">
            <span class="aab-icon">&#x1F50E;</span> VERIFY
        </button>
        <button class="aab-btn aab-defend" data-action="defend">
            <span class="aab-icon">&#x1F6E1;</span> DEFEND
        </button>
        <button class="aab-btn aab-visualize" data-action="visualize">
            <span class="aab-icon">&#x1F4CA;</span> VISUALIZE
        </button>
        <button class="aab-btn aab-document" data-action="document">
            <span class="aab-icon">&#x1F4C4;</span> DOCUMENT
        </button>
    `;
    bar.addEventListener('click', handleActionBarClick);
    return bar;
}

function handleActionBarClick(e) {
    const btn = e.target.closest('.aab-btn');
    if (!btn) return;
    e.stopPropagation();
    const action = btn.dataset.action;
    const card = btn.closest('.agent-card');
    if (!card) return;
    const provider = card.dataset.provider || '';
    const providerName = getProviderName(provider);
    const response = card.querySelector('.agent-response')?.innerText || '';

    switch (action) {
        case 'interrogate':
            openInterrogation(providerName);
            break;
        case 'verify':
            executeVerify(response, providerName);
            break;
        case 'defend':
            openInterrogation(providerName);
            break;
        case 'visualize':
            window.visualizeSelection(response);
            break;
        case 'document':
            saveReport();
            break;
    }
}

// Deselect on ESC
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') deselectCard();
});

// --- THREAD MANAGEMENT UI ---
function updateThreadBadge() {
    let badge = document.getElementById('threadBadge');
    const wrapper = document.querySelector('.input-wrapper');
    if (!wrapper) return;

    if (!sessionState.activeThreadId) {
        if (badge) badge.remove();
        return;
    }

    if (!badge) {
        badge = document.createElement('div');
        badge.id = 'threadBadge';
        badge.style.cssText = 'display:flex;align-items:center;gap:8px;padding:5px 12px;margin-bottom:4px;background:rgba(0,229,255,0.08);border:1px solid rgba(0,229,255,0.25);border-radius:6px;font-size:11px;color:#00E5FF;letter-spacing:0.5px;';

        const icon = document.createElement('span');
        icon.textContent = '\u25C8';  // diamond
        icon.style.cssText = 'font-size:13px;opacity:0.7;';
        badge.appendChild(icon);

        const label = document.createElement('span');
        label.className = 'thread-label';
        label.style.cssText = 'flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;';
        badge.appendChild(label);

        const threadsBtn = document.createElement('button');
        threadsBtn.textContent = 'THREADS';
        threadsBtn.title = 'View analysis threads';
        threadsBtn.style.cssText = 'background:rgba(0,229,255,0.12);border:1px solid rgba(0,229,255,0.3);color:#00E5FF;padding:2px 8px;border-radius:4px;font-size:10px;cursor:pointer;letter-spacing:0.5px;font-family:inherit;';
        threadsBtn.addEventListener('click', () => toggleThreadPanel());
        badge.appendChild(threadsBtn);

        const newThreadBtn = document.createElement('button');
        newThreadBtn.textContent = 'NEW THREAD';
        newThreadBtn.title = 'Start a fresh analysis thread';
        newThreadBtn.style.cssText = 'background:rgba(0,255,157,0.12);border:1px solid rgba(0,255,157,0.3);color:#00FF9D;padding:2px 8px;border-radius:4px;font-size:10px;cursor:pointer;letter-spacing:0.5px;font-family:inherit;';
        newThreadBtn.addEventListener('click', () => {
            sessionState.activeThreadId = null;
            sessionState.threadHistory = [];
            updateThreadBadge();
            const cp = document.getElementById('pane-council');
            const ap = document.getElementById('pane-analysis');
            const ip = document.getElementById('pane-interrogation');
            if (cp) cp.innerHTML = '';
            if (ap) ap.innerHTML = '';
            if (ip) ip.innerHTML = '<div class="interrogation-empty-state" id="interrogationEmpty">No interrogation or verification results yet.</div>';
            logTelemetry("New thread started", "system");
        });
        badge.appendChild(newThreadBtn);

        wrapper.parentElement.insertBefore(badge, wrapper);
    }

    const label = badge.querySelector('.thread-label');
    const count = sessionState.threadHistory.length;
    const firstQuery = sessionState.threadHistory[0]?.query || 'Active Thread';
    const title = firstQuery.length > 60 ? firstQuery.substring(0, 57) + '...' : firstQuery;
    label.textContent = `${title}  \u2022  ${count} message${count !== 1 ? 's' : ''}`;
}

// --- THREAD PANEL (Slide-out) ---
async function toggleThreadPanel() {
    let panel = document.getElementById('threadPanel');
    if (panel) {
        panel.remove();
        return;
    }

    panel = document.createElement('div');
    panel.id = 'threadPanel';
    panel.style.cssText = `
        position:fixed;top:0;right:0;width:320px;height:100vh;
        background:#0D1117;border-left:1px solid rgba(0,229,255,0.2);
        z-index:9999;display:flex;flex-direction:column;
        box-shadow:-4px 0 20px rgba(0,0,0,0.5);
        animation:slideIn 0.2s ease-out;
    `;

    // Header
    const header = document.createElement('div');
    header.style.cssText = 'padding:16px 20px;border-bottom:1px solid rgba(0,229,255,0.15);display:flex;align-items:center;justify-content:space-between;';
    header.innerHTML = `
        <span style="color:#00E5FF;font-size:13px;letter-spacing:1px;font-weight:600;">ANALYSIS THREADS</span>
        <button id="closeThreadPanel" style="background:none;border:none;color:#8b949e;cursor:pointer;font-size:18px;padding:0 4px;">\u2715</button>
    `;
    panel.appendChild(header);

    // Thread list container
    const listContainer = document.createElement('div');
    listContainer.id = 'threadList';
    listContainer.style.cssText = 'flex:1;overflow-y:auto;padding:8px;';
    listContainer.innerHTML = '<div style="color:#8b949e;text-align:center;padding:20px;font-size:12px;">Loading threads...</div>';
    panel.appendChild(listContainer);

    document.body.appendChild(panel);

    // Close button
    document.getElementById('closeThreadPanel').addEventListener('click', () => panel.remove());

    // Load threads
    try {
        const resp = await authFetch('/api/threads');
        const threads = await resp.json();
        renderThreadList(threads);
    } catch (e) {
        listContainer.innerHTML = '<div style="color:#FF6B6B;padding:20px;font-size:12px;">Failed to load threads</div>';
    }
}

function renderThreadList(threads) {
    const container = document.getElementById('threadList');
    if (!container) return;

    if (!threads.length) {
        container.innerHTML = '<div style="color:#8b949e;text-align:center;padding:20px;font-size:12px;">No threads yet. Run a council query to create one.</div>';
        return;
    }

    container.innerHTML = '';
    for (const t of threads) {
        const isActive = t.thread_id === sessionState.activeThreadId;
        const item = document.createElement('div');
        item.style.cssText = `
            padding:10px 12px;margin-bottom:4px;border-radius:6px;cursor:pointer;
            background:${isActive ? 'rgba(0,229,255,0.1)' : 'rgba(255,255,255,0.03)'};
            border:1px solid ${isActive ? 'rgba(0,229,255,0.3)' : 'rgba(255,255,255,0.06)'};
            transition:background 0.15s;
        `;
        item.addEventListener('mouseenter', () => { if (!isActive) item.style.background = 'rgba(255,255,255,0.06)'; });
        item.addEventListener('mouseleave', () => { if (!isActive) item.style.background = 'rgba(255,255,255,0.03)'; });

        const timeAgo = getTimeAgo(t.last_activity || t.created_at);
        item.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:start;gap:8px;">
                <div style="flex:1;min-width:0;">
                    <div style="color:#e6edf3;font-size:12px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                        ${isActive ? '\u25C8 ' : ''}${escapeHtml(t.title)}
                    </div>
                    <div style="color:#8b949e;font-size:10px;margin-top:3px;">
                        ${t.message_count} message${t.message_count !== 1 ? 's' : ''} \u2022 ${timeAgo}
                    </div>
                </div>
                <button class="thread-delete-btn" data-thread-id="${t.thread_id}" title="Delete thread"
                    style="background:none;border:none;color:#8b949e;cursor:pointer;font-size:12px;padding:2px 4px;opacity:0.5;flex-shrink:0;"
                    onmouseenter="this.style.opacity='1';this.style.color='#FF6B6B'"
                    onmouseleave="this.style.opacity='0.5';this.style.color='#8b949e'">
                    \u2715
                </button>
            </div>
        `;

        // Click to load thread
        item.addEventListener('click', (e) => {
            if (e.target.closest('.thread-delete-btn')) return;
            loadThread(t.thread_id);
        });

        container.appendChild(item);
    }

    // Delete button handlers
    container.querySelectorAll('.thread-delete-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const tid = btn.dataset.threadId;
            if (!confirm('Delete this analysis thread?')) return;
            try {
                await authFetch(`/api/threads/${tid}`, { method: 'DELETE' });
                if (sessionState.activeThreadId === tid) {
                    sessionState.activeThreadId = null;
                    sessionState.threadHistory = [];
                    updateThreadBadge();
                }
                btn.closest('div[style]').remove();
                logTelemetry(`Thread deleted: ${tid.substring(0, 8)}`, "system");
            } catch (err) {
                console.error('Delete thread failed:', err);
            }
        });
    });
}

async function loadThread(threadId) {
    try {
        const resp = await authFetch(`/api/threads/${threadId}`);
        const thread = await resp.json();

        if (thread.error) {
            console.error('Thread load error:', thread.error);
            return;
        }

        // Set active thread
        sessionState.activeThreadId = threadId;
        sessionState.threadHistory = [];

        // Rebuild threadHistory from council messages
        for (const msg of thread.messages) {
            if (msg.role === 'council' && msg.metadata) {
                try {
                    const meta = typeof msg.metadata === 'string' ? JSON.parse(msg.metadata) : msg.metadata;
                    sessionState.threadHistory.push({
                        query: meta.query || '',
                        summary: meta.summary || '',
                        consensus_score: meta.consensus_score || null,
                        contested_topics: meta.contested_topics || [],
                        divergence_summary: meta.divergence_summary || ''
                    });
                } catch (e) { /* skip malformed */ }
            }
        }

        // Set the original query from last user message (for interrogation/verification)
        const lastUserMsg = [...thread.messages].reverse().find(m => m.role === 'user');
        if (lastUserMsg) {
            try {
                sessionState.originalQuery = typeof lastUserMsg.content === 'string' ?
                    (lastUserMsg.content.startsWith('"') ? JSON.parse(lastUserMsg.content) : lastUserMsg.content) : lastUserMsg.content;
            } catch (e) { sessionState.originalQuery = lastUserMsg.content || ''; }
        }

        updateThreadBadge();

        // Close panel
        const panel = document.getElementById('threadPanel');
        if (panel) panel.remove();

        logTelemetry(`Thread loaded: ${threadId.substring(0, 8)} — ${thread.title}`, "system");
    } catch (e) {
        console.error('Load thread failed:', e);
    }
}

function getTimeAgo(isoString) {
    if (!isoString) return 'unknown';
    const now = new Date();
    const then = new Date(isoString);
    const diffMs = now - then;
    const mins = Math.floor(diffMs / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
}


// CSS animation for thread panel
(function() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(320px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
    `;
    document.head.appendChild(style);
})();

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

    hideHighlightToolbar();

    // Show processing feedback
    logTelemetry("CHALLENGING SELECTION...", "process");
    showProcessingToast("Verifying claim...");

    // Build challenge query
    const query = `FACT CHECK THIS CLAIM: "${selection}". Verify accuracy, identify potential errors or hallucinations, and provide supporting or contradicting evidence.`;

    // Trigger the council to verify
    triggerCouncil(query);
};

window.openInterrogation = function (targetName, overrideResponse = null) {
    // Auto-close the card modal so user can see interrogation running
    closeCardModal();
    const resolvedTargetName = targetName || 'Selected Text';
    // Resolve provider key using shared map
    const providerKey = resolveProviderKey(resolvedTargetName);
    sessionState.targetCard = providerKey;

    // Get defender's role from the deck labels
    const defenderRole = providerKey
        ? (document.getElementById(`roleLabel-${providerKey}`)?.innerText.toLowerCase() || 'analyst')
        : 'analyst';

    // Get target response text — selected excerpt takes priority
    let targetResponse = (typeof overrideResponse === 'string' && overrideResponse.trim())
        ? overrideResponse.trim()
        : (providerKey ? sessionState.lastResponses[providerKey] : '');
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
    showInterrogationPicker(resolvedTargetName, defenderRole, targetResponse);
};

// ── ADVERSARIAL FACE-OFF: ROLE REGISTRY ──────────────────────────────────
const ATTACKER_CATEGORIES = {
    "DEFENSE & INTEL": [
        'defense_ops', 'cyber_ops', 'intel_analyst', 'defense_acq',
        'sigint', 'counterintel', 'cryptographer', 'zero_trust'
    ],
    "SECURITY & ENGINEERING": [
        'hacker', 'coding', 'ai_architect', 'network', 'telecom'
    ],
    "STRATEGY & ANALYSIS": [
        'strategist', 'analyst', 'architect', 'containment', 'takeover',
        'critic', 'visionary', 'optimizer'
    ],
    "BUSINESS & FINANCE": [
        'cfo', 'auditor', 'bizstrat', 'hedge_fund', 'tax',
        'negotiator', 'sales', 'economist', 'product'
    ],
    "SCIENCE & MEDICAL": [
        'physicist', 'biologist', 'chemist', 'medical', 'bioethicist', 'professor'
    ],
    "LEGAL & COMPLIANCE": [
        'jurist', 'compliance', 'integrity'
    ],
    "RESEARCH & VALIDATION": [
        'researcher', 'scout', 'historian', 'validator'
    ],
    "CREATIVE & COMMS": [
        'writer', 'innovator', 'marketing', 'social', 'creative', 'web_designer'
    ]
};

// Counter-role suggestions: each defender gets 3 attackers that challenge its blind spots
const ATTACKER_SUGGESTIONS = {
    // Defense & Intel
    'defense_ops':    ['counterintel', 'economist', 'compliance'],
    'cyber_ops':      ['hacker', 'counterintel', 'zero_trust'],
    'intel_analyst':  ['counterintel', 'sigint', 'critic'],
    'defense_acq':    ['auditor', 'compliance', 'economist'],
    'sigint':         ['counterintel', 'cryptographer', 'hacker'],
    'counterintel':   ['hacker', 'sigint', 'intel_analyst'],
    'cryptographer':  ['hacker', 'physicist', 'zero_trust'],
    'zero_trust':     ['hacker', 'network', 'cryptographer'],
    // Security & Engineering
    'hacker':         ['cryptographer', 'zero_trust', 'counterintel'],
    'coding':         ['hacker', 'ai_architect', 'architect'],
    'ai_architect':   ['critic', 'bioethicist', 'hacker'],
    'network':        ['hacker', 'zero_trust', 'telecom'],
    'telecom':        ['sigint', 'network', 'hacker'],
    // Strategy & Analysis
    'strategist':     ['critic', 'takeover', 'economist'],
    'analyst':        ['critic', 'validator', 'historian'],
    'architect':      ['critic', 'hacker', 'auditor'],
    'containment':    ['takeover', 'hacker', 'strategist'],
    'takeover':       ['containment', 'compliance', 'economist'],
    'critic':         ['innovator', 'visionary', 'architect'],
    'visionary':      ['critic', 'economist', 'historian'],
    'optimizer':      ['critic', 'architect', 'auditor'],
    // Business & Finance
    'cfo':            ['auditor', 'tax', 'hedge_fund'],
    'auditor':        ['hacker', 'cfo', 'compliance'],
    'bizstrat':       ['critic', 'economist', 'takeover'],
    'hedge_fund':     ['auditor', 'economist', 'compliance'],
    'tax':            ['auditor', 'compliance', 'jurist'],
    'negotiator':     ['critic', 'jurist', 'takeover'],
    'sales':          ['critic', 'auditor', 'analyst'],
    'economist':      ['critic', 'historian', 'physicist'],
    'product':        ['critic', 'analyst', 'sales'],
    // Science & Medical
    'physicist':      ['chemist', 'critic', 'economist'],
    'biologist':      ['bioethicist', 'chemist', 'critic'],
    'chemist':        ['physicist', 'biologist', 'critic'],
    'medical':        ['bioethicist', 'biologist', 'compliance'],
    'bioethicist':    ['medical', 'jurist', 'critic'],
    'professor':      ['critic', 'innovator', 'historian'],
    // Legal & Compliance
    'jurist':         ['compliance', 'bioethicist', 'critic'],
    'compliance':     ['hacker', 'jurist', 'auditor'],
    'integrity':      ['hacker', 'auditor', 'critic'],
    // Research & Validation
    'researcher':     ['critic', 'validator', 'historian'],
    'scout':          ['counterintel', 'analyst', 'validator'],
    'historian':      ['critic', 'innovator', 'economist'],
    'validator':      ['hacker', 'critic', 'innovator'],
    // Creative & Comms
    'writer':         ['critic', 'analyst', 'marketing'],
    'innovator':      ['critic', 'economist', 'historian'],
    'marketing':      ['critic', 'analyst', 'sales'],
    'social':         ['critic', 'analyst', 'marketing'],
    'creative':       ['critic', 'analyst', 'validator'],
    'web_designer':   ['critic', 'hacker', 'optimizer'],
};

function getAttackerSuggestions(defenderRole) {
    // Direct lookup
    const direct = ATTACKER_SUGGESTIONS[defenderRole];
    if (direct) return direct.filter(r => r !== defenderRole);

    // Workflow-aware fallback: suggest roles from the active preset that aren't the defender
    const workflow = sessionState?.missionContext?.workflow;
    if (workflow) {
        const workflowKey = Object.keys(PROTOCOL_CONFIGS).find(
            k => k.toUpperCase().replace(/\s+/g, '_') === workflow
        );
        if (workflowKey) {
            const candidates = Object.values(PROTOCOL_CONFIGS[workflowKey])
                .filter(r => r !== defenderRole);
            if (candidates.length >= 3) return candidates.slice(0, 3);
        }
    }

    // Ultimate fallback
    return ['critic', 'hacker', 'auditor'].filter(r => r !== defenderRole);
}

// ── ADVERSARIAL FACE-OFF PICKER ──────────────────────────────────────────
function showInterrogationPicker(targetName, defenderRole, targetResponse) {
    // Remove any existing picker
    document.getElementById('interrogation-picker')?.remove();

    const suggested = getAttackerSuggestions(defenderRole);
    const allRoles = Object.values(ATTACKER_CATEGORIES).flat();
    const remainingCount = allRoles.filter(r => !suggested.includes(r)).length;

    // Build categorized "ALL PERSONAS" HTML
    const categorizedHTML = Object.entries(ATTACKER_CATEGORIES).map(([category, roles]) => {
        const filteredRoles = roles.filter(r => !suggested.includes(r));
        if (filteredRoles.length === 0) return '';
        return `
            <div style="margin-top: 10px;">
                <div style="color: #555; font-size: 0.5rem; letter-spacing: 0.12em; margin-bottom: 4px;
                            border-bottom: 1px solid rgba(255,255,255,0.06); padding-bottom: 3px;">
                    ${category}
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 4px;">
                    ${filteredRoles.map(role => `
                        <button class="attacker-pick" data-role="${role}" style="
                            background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.15);
                            color: #888; padding: 4px 8px; border-radius: 3px; cursor: pointer;
                            font-family: inherit; font-size: 0.55rem; letter-spacing: 0.05em;
                            transition: all 0.15s;
                        ">${role.replace(/_/g, ' ').toUpperCase()}</button>
                    `).join('')}
                </div>
            </div>
        `;
    }).join('');

    const picker = document.createElement('div');
    picker.id = 'interrogation-picker';
    picker.style.cssText = `
        position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
        background: rgba(10, 10, 15, 0.97); border: 1px solid rgba(255, 68, 68, 0.6);
        border-radius: 6px; padding: 20px 24px; z-index: 10500; min-width: 340px; max-width: 480px;
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
        <div style="color: #AAA; font-size: 0.6rem; letter-spacing: 0.1em; margin-bottom: 8px;">RECOMMENDED ATTACKERS:</div>
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
            <summary style="color: #666; font-size: 0.55rem; cursor: pointer; letter-spacing: 0.1em;">ALL PERSONAS (${remainingCount} more)</summary>
            <div style="max-height: 50vh; overflow-y: auto; padding-right: 4px;">
                ${categorizedHTML}
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

    // Create verification card → INTERROGATION pane
    const interPane = document.getElementById('pane-interrogation');
    const emptyState = document.getElementById('interrogationEmpty');
    if (emptyState) emptyState.style.display = 'none';

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
    interPane.appendChild(verifyCard);
    incrementInterrogationBadge();
    verifyCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    try {
        const resp = await authFetch('/api/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                claim: claim,
                original_query: sessionState.originalQuery || '',
                thread_id: sessionState.activeThreadId || null,
                use_falcon: activeModes.falcon,
                falcon_level: document.getElementById('falcon-level-select')?.value || 'STANDARD',
                falcon_custom_terms: window._falconCustomTerms || []
            })
        });

        const result = await resp.json();

        if (!result.success) {
            logTelemetry(`Verification error: ${result.error}`, "error");
            verifyCard.querySelector('.agent-response').innerHTML = `<span style="color:#FF4444">Verification could not be completed. Please try again.</span>`;
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
        logTelemetry(`Verification network error: ${e.message}`, "error");
        verifyCard.querySelector('.agent-response').innerHTML = `<span style="color:#FF4444">Connection issue — unable to verify claim. Please retry.</span>`;
    }
};

// ── EXECUTE ADVERSARIAL INTERROGATION ────────────────────────────────────
async function executeInterrogation(attackerRole, defenderRole, targetResponse, targetName) {
    logTelemetry(`⚔️ ${attackerRole.toUpperCase()} vs ${defenderRole.toUpperCase()}`, "user");
    sentinelChat.appendMessage(`INITIATING FACE-OFF: ${attackerRole.toUpperCase()} vs ${defenderRole.toUpperCase()}`, 'user');

    // Create face-off card → INTERROGATION pane
    const interPane = document.getElementById('pane-interrogation');
    const emptyState = document.getElementById('interrogationEmpty');
    if (emptyState) emptyState.style.display = 'none';

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
    interPane.appendChild(faceoffCard);
    incrementInterrogationBadge();
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
                thread_id: sessionState.activeThreadId || null,
                use_falcon: activeModes.falcon,
                falcon_level: document.getElementById('falcon-level-select')?.value || 'STANDARD',
                falcon_custom_terms: window._falconCustomTerms || []
            }),
        });

        const result = await resp.json();

        if (!result.success) {
            clearInterval(hbInterval);
            logTelemetry(`Interrogation error: ${result.error}`, "error");
            faceoffCard.querySelector('.agent-response').innerHTML = `<span style="color:#FF4444">Cross-examination could not be completed. Please try again.</span>`;
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
        logTelemetry(`Interrogation network error: ${err.message}`, "error");
        faceoffCard.querySelector('.agent-response').innerHTML = `<span style="color:#FF4444">Connection issue — unable to complete cross-examination. Please retry.</span>`;
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
            logTelemetry(`Enhancement error: ${data.error}`, "error");
            showProcessingToast("Enhancement could not be completed. Please try again.");
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

// ── FALCON GHOST PREVIEW ─────────────────────────────────────────────
function openGhostModal(originalText, redactedHtml, stats) {
    const modal = document.getElementById('ghostModal');
    const origEl = document.getElementById('ghostOriginalText');
    const redEl = document.getElementById('ghostRedactedText');
    const statsEl = document.getElementById('ghostStats');
    if (!modal || !origEl || !redEl) return;

    origEl.textContent = originalText;
    redEl.innerHTML = redactedHtml;

    // Build stats bar
    if (statsEl && stats) {
        const risk = stats.exposure_risk || 'none';
        const riskClass = `ghost-risk-${risk}`;
        const riskLabel = risk === 'potential_miss' ? 'POTENTIAL MISS' : risk.toUpperCase() + ' RISK';
        const cats = (stats.categories_found || []).map(c =>
            `<span class="ghost-cat-chip">${c} <strong>${stats.counts_by_category[c] || 0}</strong></span>`
        ).join('');
        const docBadge = stats.documents_scanned ? `<span class="ghost-stat-docs scanning" id="ghost-doc-badge">${stats.documents_scanned} DOC${stats.documents_scanned !== 1 ? 'S' : ''} SCANNED</span>` : '';
        statsEl.innerHTML = `
            <div class="ghost-stats-row">
                <span class="ghost-stat-total">${stats.total_redactions} REDACTION${stats.total_redactions !== 1 ? 'S' : ''}</span>
                <span class="ghost-stat-risk ${riskClass}">${riskLabel}</span>
                ${docBadge}
                <span class="ghost-stat-time">${stats.execution_time_ms}ms</span>
            </div>
            <div class="ghost-cats-row">${cats}</div>`;
        // Pulse the doc badge briefly to confirm scan just completed, then settle
        if (stats.documents_scanned) {
            setTimeout(() => {
                document.getElementById('ghost-doc-badge')?.classList.remove('scanning');
            }, 3000);
        }
    }
    modal.classList.add('visible');
}

function closeGhostModal() {
    document.getElementById('ghostModal')?.classList.remove('visible');
}

function highlightPlaceholders(text) {
    return text.replace(/\[([A-Z_]+_[A-F0-9]+)\]/g,
        '<span class="ghost-placeholder">[$1]</span>');
}

window.ghostPreview = async function () {
    const input = document.getElementById('queryInput');
    const btn = document.getElementById('ghostPreviewBtn');
    if (!input || !btn) return;

    const draft = input.value.trim();
    if (!draft && !pendingFiles.length) {
        showProcessingToast("Enter a query or attach documents to preview Falcon redaction.");
        return;
    }

    btn.classList.add('ghost-loading');
    const originalIcon = btn.innerHTML;
    btn.innerHTML = `<div class="spinner-sm"></div>`;
    const fileNote = pendingFiles.length ? ` + ${pendingFiles.length} doc(s)` : '';
    logTelemetry(`FALCON GHOST PREVIEW — scanning${fileNote}...`, "process");

    try {
        const level = document.getElementById('falcon-level-select')?.value || 'STANDARD';
        const payload = {
            text: draft,
            level: level,
            custom_terms: window._falconCustomTerms || []
        };

        let response;
        if (pendingFiles.length > 0) {
            // Send files via FormData so backend can extract document text
            const formData = new FormData();
            formData.append('payload', JSON.stringify(payload));
            for (const file of pendingFiles) {
                formData.append('files', file);
            }
            response = await authFetch('/api/falcon/preview', { method: 'POST', body: formData });
        } else {
            response = await authFetch('/api/falcon/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }

        if (!response.ok) {
            const errText = await response.text();
            console.error(`Ghost Preview HTTP ${response.status}:`, errText);
            logTelemetry(`Ghost Preview error: HTTP ${response.status}`, "error");
            showProcessingToast(`Ghost Preview failed (${response.status}).`);
            return;
        }
        const data = await response.json();

        if (data.success) {
            const redactedHtml = highlightPlaceholders(
                data.redacted_text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            );
            const docMsg = data.documents_scanned ? ` (incl. ${data.documents_scanned} document(s))` : '';
            logTelemetry(`GHOST PREVIEW: ${data.total_redactions} items redacted [${data.exposure_risk}]${docMsg}`, "success");
            openGhostModal(draft, redactedHtml, data);
        } else {
            logTelemetry(`Ghost Preview error: ${data.error}`, "error");
            showProcessingToast("Ghost Preview failed.");
        }
    } catch (e) {
        console.error('Ghost Preview error:', e);
        showProcessingToast("Network error during Ghost Preview.");
    } finally {
        btn.classList.remove('ghost-loading');
        btn.innerHTML = originalIcon;
    }
};

// Bind Ghost Preview Button + Modal Controls
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('ghostPreviewBtn')?.addEventListener('click', window.ghostPreview);

    document.getElementById('ghostDismissBtn')?.addEventListener('click', closeGhostModal);

    // Execute from ghost modal — proceed to council
    document.getElementById('ghostExecuteBtn')?.addEventListener('click', () => {
        closeGhostModal();
        const query = document.getElementById('queryInput')?.value.trim();
        if (query) triggerCouncil(query);
    });

    // Quick Protect: add term and rescan
    const ghostProtectBtn = document.getElementById('ghostProtectBtn');
    const ghostProtectInput = document.getElementById('ghostProtectInput');

    function ghostProtectAndRescan() {
        const term = ghostProtectInput?.value.trim();
        if (!term) return;
        // Add to global custom terms (same list the Falcon panel uses)
        if (typeof addFalconTerm === 'function') {
            addFalconTerm(term);
        } else if (!window._falconCustomTerms.includes(term)) {
            window._falconCustomTerms.push(term);
        }
        ghostProtectInput.value = '';
        logTelemetry(`GHOST EYE: Protected "${term}" — rescanning...`, "warning");
        // Re-run the preview with updated terms
        window.ghostPreview();
    }

    ghostProtectBtn?.addEventListener('click', ghostProtectAndRescan);
    ghostProtectInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') { e.preventDefault(); ghostProtectAndRescan(); }
    });

    // Click overlay to close
    document.getElementById('ghostModal')?.addEventListener('click', (e) => {
        if (e.target.id === 'ghostModal') closeGhostModal();
    });
});

window.visualizeSelection = function (fallbackText) {
    const selection = window.getSelection().toString();
    const textToProcess = selection || fallbackText;

    if (!textToProcess) {
        showProcessingToast("Highlight some data first!");
        return;
    }

    hideHighlightToolbar();

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
    const container = document.getElementById('pane-council') || document.querySelector(".results-content");
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
    displayContent = displayContent
        .replace(/\[DECISION_CANDIDATE\]([\s\S]*?)\[\/DECISION_CANDIDATE\]/g, '<span class="intel-tag tag-decision" title="DECISION CANDIDATE">$1</span>')
        .replace(/\[RISK_VECTOR\]([\s\S]*?)\[\/RISK_VECTOR\]/g, '<span class="intel-tag tag-risk" title="RISK VECTOR">$1</span>')
        .replace(/\[METRIC_ANCHOR\]([\s\S]*?)\[\/METRIC_ANCHOR\]/g, '<span class="intel-tag tag-metric" title="KEY METRIC">$1</span>')
        .replace(/\[TRUTH_BOMB\]([\s\S]*?)\[\/TRUTH_BOMB\]/g, '<span class="intel-tag tag-truth" title="VERIFIED FACT">$1</span>')
        .replace(/\[\/?(DECISION_CANDIDATE|RISK_VECTOR|METRIC_ANCHOR|TRUTH_BOMB)\]/g, "");

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

function renderSkeletonCards(providers) {
    const councilPane = document.getElementById('pane-council');
    if (!councilPane) return;
    councilPane.innerHTML = '';

    const grid = document.createElement('div');
    grid.className = 'results-grid skeleton-grid';

    providers.forEach(provider => {
        const role = document.getElementById(`roleLabel-${provider}`)?.innerText || provider.toUpperCase();
        const card = document.createElement('div');
        card.className = `agent-card ${provider} skeleton-card`;
        card.innerHTML = `
            <div class="precision-header">
                <div class="ph-left">
                    <div class="ph-model-name">${role}</div>
                    <div class="ph-role-label">${getProviderName(provider)} | analyzing...</div>
                </div>
                <div class="ph-right">
                    <div class="metric-pill" style="color:#FFB020; animation: pulse 1.5s infinite;">PROCESSING</div>
                </div>
            </div>
            <div class="agent-response" style="padding:16px;">
                <div class="skeleton-line" style="width:90%; height:10px; background:rgba(255,255,255,0.04); border-radius:3px; margin-bottom:8px; animation: shimmer 1.5s infinite;"></div>
                <div class="skeleton-line" style="width:75%; height:10px; background:rgba(255,255,255,0.03); border-radius:3px; margin-bottom:8px; animation: shimmer 1.5s infinite 0.2s;"></div>
                <div class="skeleton-line" style="width:60%; height:10px; background:rgba(255,255,255,0.02); border-radius:3px; animation: shimmer 1.5s infinite 0.4s;"></div>
            </div>
        `;
        grid.appendChild(card);
    });

    councilPane.appendChild(grid);

    // Make dock visible and switch to council tab
    document.querySelector('.results-container')?.classList.add('visible');
    switchDockTab('council');
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
    const activeProviders = ["openai", "anthropic", "google", "perplexity", "mistral", "local"].filter(p =>
        AIHealth.isAvailable(p) && !document.querySelector(`.deck-card.${p}`)?.classList.contains('silenced')
    );
    activeProviders.forEach(p => AIHealth.setResponding(p, true));

    // Show skeleton loading cards in council pane
    if (!isSubTask) {
        renderSkeletonCards(activeProviders);
    }

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
    if (activeModes.falcon) logTelemetry(`FALCON PROTOCOL ACTIVE [${document.getElementById('falcon-level-select')?.value || 'STANDARD'}]: Secure preprocessing enabled`, "warning");

    const payload = {
        question: query,
        council_mode: true,
        council_roles: roleConfig,
        active_models: ["openai", "anthropic", "google", "perplexity", "mistral", "local"].filter(p => AIHealth.isAvailable(p) && !document.querySelector(`.deck-card.${p}`)?.classList.contains('silenced')),
        use_v2: true,
        is_red_team: isRedTeam,
        use_serp: useSerpAPI,
        use_falcon: activeModes.falcon,
        falcon_level: document.getElementById('falcon-level-select')?.value || 'STANDARD',
        falcon_custom_terms: window._falconCustomTerms || [],
        workflow: sessionState.missionContext?.workflow || "RESEARCH",
        thread_id: sessionState.activeThreadId || null
    };

    if (sessionState.activeThreadId) {
        logTelemetry(`THREAD MODE: Continuing thread ${sessionState.activeThreadId.substring(0, 8)}`, "process");
    }

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
    
    // RENDER EXECUTION METRICS
    if (data.execution_metrics) {
        renderExecutionDashboard(data.execution_metrics);
    }

    incrementQueryCount();

    // Capture thread_id from server response (auto-created on first query)
    if (data.thread_id) {
        sessionState.activeThreadId = data.thread_id;
        logTelemetry(`Thread active: ${data.thread_id.substring(0, 8)}`, "system");
    }

    // Accumulate session context for local follow-up display
    const synthesis = data.synthesis || {};
    const divergence = data.divergence || {};
    sessionState.threadHistory.push({
        query: query,
        summary: synthesis.meta?.summary || '',
        consensus_score: divergence.consensus_score || null,
        contested_topics: (divergence.contested_topics || []).map(t => t.topic || t),
        divergence_summary: divergence.divergence_summary || ''
    });
    updateThreadBadge();

    resetUI();
}

// ── DOCK TAB SWITCHING ─────────────────────────────────────
let activeDockTab = 'council';
let interrogationBadgeCount = 0;

function initDockTabs() {
    document.querySelectorAll('.dock-tab').forEach(tab => {
        tab.addEventListener('click', () => switchDockTab(tab.dataset.dockTab));
    });
}

function switchDockTab(tabName) {
    activeDockTab = tabName;
    hideHighlightToolbar();
    document.querySelectorAll('.dock-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.dockTab === tabName);
    });
    document.querySelectorAll('.dock-pane').forEach(p => {
        p.classList.toggle('active', p.id === `pane-${tabName}`);
    });
    if (tabName === 'interrogation') {
        interrogationBadgeCount = 0;
        const badge = document.getElementById('interrogationBadge');
        if (badge) badge.style.display = 'none';
    }
}

function incrementInterrogationBadge() {
    if (activeDockTab === 'interrogation') return;
    interrogationBadgeCount++;
    const badge = document.getElementById('interrogationBadge');
    if (badge) {
        badge.textContent = interrogationBadgeCount;
        badge.style.display = 'inline-block';
    }
}

// ── EXECUTIVE SUMMARY CARD ───────────────────────────────────────────────
function buildExecutiveSummary(data, roleName, avgConfidence, totalTime) {
    const card = document.createElement('div');
    card.className = 'consensus-card exec-summary-card';
    card.style.cssText = 'border-color: rgba(0,229,255,0.3); margin-bottom: 16px;';

    // Determine data sources
    const synthesis = data.synthesis || {};
    const meta = synthesis.meta || {};
    const structured = synthesis.structured_data || {};
    const divergence = data.divergence || {};
    const results = data.results || {};

    // Count responding agents
    const respondingProviders = Object.entries(results)
        .filter(([k, v]) => k !== 'red_team' && v && v.success)
        .map(([k]) => getProviderName(k).toUpperCase());
    const agentCount = respondingProviders.length;

    // Truth score: prefer composite, fallback to average
    let truthScore = meta.composite_truth_score;
    if (truthScore === undefined || truthScore === null) truthScore = Math.round(avgConfidence);
    else if (truthScore <= 1) truthScore = Math.round(truthScore * 100);
    const truthColor = truthScore > 80 ? '#00FF9D' : truthScore > 50 ? '#FFB020' : '#FF4444';

    // Summary text: prefer synthesis, fallback to consensus
    const summaryText = meta.summary || data.consensus || 'Council analysis complete.';

    // Workflow
    const workflow = meta.workflow || roleName || 'COUNCIL';

    // Divergence indicator
    const divScore = divergence.divergence_score || 0;
    const hasVariance = divergence.protocol_variance || false;

    // Action items count
    const actionCount = structured.action_items?.length || 0;
    const riskCount = structured.risks?.length || 0;

    // Build header metrics
    let metricsHtml = `
        <div style="display:flex; gap:16px; flex-wrap:wrap; margin-bottom:12px;">
            <div style="text-align:center;">
                <div style="color:#555; font-size:0.5rem; letter-spacing:0.1em;">TRUTH SCORE</div>
                <div style="color:${truthColor}; font-size:1.2rem; font-weight:bold;">${truthScore}<span style="font-size:0.6rem; color:#555">/100</span></div>
            </div>
            <div style="text-align:center;">
                <div style="color:#555; font-size:0.5rem; letter-spacing:0.1em;">AGENTS</div>
                <div style="color:#00E5FF; font-size:1.2rem; font-weight:bold;">${agentCount}</div>
            </div>
            <div style="text-align:center;">
                <div style="color:#555; font-size:0.5rem; letter-spacing:0.1em;">LATENCY</div>
                <div style="color:#AAA; font-size:1.2rem; font-weight:bold;">${totalTime.toFixed(1)}<span style="font-size:0.6rem; color:#555">s</span></div>
            </div>
            ${divScore > 0 ? `<div style="text-align:center;">
                <div style="color:#555; font-size:0.5rem; letter-spacing:0.1em;">DIVERGENCE</div>
                <div style="color:${hasVariance ? '#FF4444' : '#FFB020'}; font-size:1.2rem; font-weight:bold;">${divScore}<span style="font-size:0.6rem; color:#555">%</span></div>
            </div>` : ''}
            ${actionCount > 0 ? `<div style="text-align:center;">
                <div style="color:#555; font-size:0.5rem; letter-spacing:0.1em;">ACTIONS</div>
                <div style="color:#FFB020; font-size:1.2rem; font-weight:bold;">${actionCount}</div>
            </div>` : ''}
            ${riskCount > 0 ? `<div style="text-align:center;">
                <div style="color:#555; font-size:0.5rem; letter-spacing:0.1em;">RISKS</div>
                <div style="color:#FF4444; font-size:1.2rem; font-weight:bold;">${riskCount}</div>
            </div>` : ''}
        </div>
    `;

    // Build action items preview (top 3)
    let actionsHtml = '';
    if (structured.action_items?.length) {
        const topActions = structured.action_items.slice(0, 3);
        actionsHtml = `<div style="margin-top:10px; border-top:1px solid rgba(255,255,255,0.06); padding-top:8px;">
            <div style="color:#555; font-size:0.5rem; letter-spacing:0.1em; margin-bottom:6px;">PRIORITY ACTIONS</div>
            ${topActions.map(item => {
                const pc = item.priority === 'high' ? '#FF4444' : item.priority === 'med' ? '#FFB020' : '#00FF9D';
                return `<div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                    <span style="background:${pc}20; color:${pc}; border:1px solid ${pc}40; padding:1px 6px; border-radius:2px; font-size:0.5rem; letter-spacing:0.08em;">${(item.priority || 'MED').toUpperCase()}</span>
                    <span style="color:#AAA; font-size:0.6rem;">${item.task || ''}</span>
                </div>`;
            }).join('')}
        </div>`;
    }

    // Build risks preview (top 2)
    let risksHtml = '';
    if (structured.risks?.length) {
        const topRisks = structured.risks.slice(0, 2);
        risksHtml = `<div style="margin-top:10px; border-top:1px solid rgba(255,255,255,0.06); padding-top:8px;">
            <div style="color:#555; font-size:0.5rem; letter-spacing:0.1em; margin-bottom:6px;">KEY RISKS</div>
            ${topRisks.map(r => `<div style="display:flex; align-items:baseline; gap:8px; margin-bottom:4px;">
                <span style="color:#FF4444; font-size:0.55rem;">&#x26A0;</span>
                <span style="color:#AAA; font-size:0.6rem;">${r.risk || ''}</span>
                ${r.severity ? `<span style="color:#FF8888; font-size:0.5rem;">[${r.severity.toUpperCase()}]</span>` : ''}
            </div>`).join('')}
        </div>`;
    }

    card.innerHTML = `
        <div class="consensus-title" style="color:#00E5FF;">
            <span style="font-size:14px;">&#x1F4CB;</span> EXECUTIVE SUMMARY · ${workflow.toUpperCase()}
            <div class="tool-action" onclick="event.stopPropagation(); copyTextToClipboard(this.closest('.consensus-card').querySelector('.consensus-body').innerText, 'Executive summary copied')" title="Copy" style="display:inline-block;margin-left:10px;cursor:pointer;">&#x1F4CB;</div>
        </div>
        <div class="consensus-body">
            ${metricsHtml}
            <div style="color:#CCC; font-size:0.65rem; line-height:1.6;">${formatText(summaryText)}</div>
            <div style="color:#555; font-size:0.5rem; margin-top:8px; letter-spacing:0.08em;">
                COUNCIL: ${respondingProviders.join(' · ')}
            </div>
            ${actionsHtml}
            ${risksHtml}
        </div>
    `;

    return card;
}

function renderResults(data, roleName) {
    // Store for export functionality
    lastCouncilData = { ...data, roleName };

    const placeholderMap = data.falcon?.placeholder_map || {};

    // Hide processing toast
    const toast = document.getElementById('processing-toast');
    if (toast) toast.style.display = 'none';

    const councilPane = document.getElementById('pane-council');
    const analysisPane = document.getElementById('pane-analysis');
    const interPane = document.getElementById('pane-interrogation');
    const councilGrid = document.createElement("div"); councilGrid.className = "results-grid";
    const analysisGrid = document.createElement("div"); analysisGrid.className = "results-grid";

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
    const consensusText = data.consensus || "No consensus reached.";
    consensusCard.innerHTML = `<div class="consensus-title"><span style="font-size:16px">🏛️</span> COUNCIL DECISION: ${roleName.toUpperCase()}<div class="tool-action" onclick="event.stopPropagation(); copyTextToClipboard(this.closest('.consensus-card').querySelector('.consensus-body').innerText, 'Council decision copied')" title="Copy" style="display:inline-block;margin-left:10px;cursor:pointer;">📋</div></div><div class="consensus-body">${formatText(consensusText)}</div>`;
    analysisGrid.appendChild(consensusCard);

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
        card.dataset.cardId = `card-${provider}-${Date.now()}`;

        // --- NEW: CLAIM HIGHLIGHTING ---
        const rawResponse = res.response;
        const verifiedClaims = res.verified_claims || [];
        const truthScore = res.truth_meter !== undefined ? res.truth_meter : 85;

        const displayContent = highlightClaims(formatText(rawResponse), verifiedClaims);
        const cost = res.cost || 0.0091;
        const time = res.time || 12.34;
        const citations = res.citations || [];

        // Build citations footer if sources exist
        let citationsHtml = '';
        if (citations.length > 0) {
            citationsHtml = `
                <div class="citations-footer" style="border-top:1px solid rgba(255,255,255,0.06); padding:8px 16px; background:rgba(0,229,255,0.02);">
                    <div style="color:#555; font-size:0.5rem; letter-spacing:0.1em; margin-bottom:4px;">SOURCES (${citations.length})</div>
                    ${citations.map((url, i) => {
                        const domain = (() => { try { return new URL(url).hostname.replace('www.',''); } catch(e) { return url; } })();
                        return `<div style="margin-bottom:2px;">
                            <a href="${url}" target="_blank" rel="noopener" style="color:#00DCFF; font-size:0.55rem; text-decoration:none; opacity:0.8; transition:opacity 0.15s;"
                               onmouseenter="this.style.opacity='1';this.style.textDecoration='underline'" onmouseleave="this.style.opacity='0.8';this.style.textDecoration='none'">
                                <span style="color:#555;">[${i+1}]</span> ${domain}
                            </a>
                        </div>`;
                    }).join('')}
                </div>`;
        }

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
                    <div class="metric-pill">$${cost.toFixed(4)}</div>
                    <div class="metric-pill time">${time}s</div>
                    ${citations.length > 0 ? `<div class="metric-pill" style="color:#00DCFF; border-color:rgba(0,229,255,0.3);">${citations.length} sources</div>` : ''}
                    <div class="tool-action" onclick="event.stopPropagation(); this.classList.add('success'); setTimeout(()=>this.classList.remove('success'), 1000); saveReport()" title="Save">💾</div>
                    <div class="tool-action" onclick="event.stopPropagation(); this.classList.add('success'); setTimeout(()=>this.classList.remove('success'), 1000); copyTextToClipboard(decodeURIComponent('${encodeURIComponent(rawResponse)}'), '${getProviderName(provider)} output copied')" title="Copy">📋</div>
                </div>
            </div>
            <div class="agent-response">${displayContent}</div>
            ${citationsHtml}
        `;

        // Single click = select card + show action bar
        card.addEventListener('click', (e) => {
            if (e.target.closest('button') || e.target.closest('.tool-action') || e.target.closest('.analysis-action-bar')) return;
            selectCard(card);
        });
        // Double click = open full-screen modal
        card.addEventListener('dblclick', (e) => {
            if (e.target.closest('button') || e.target.closest('.tool-action') || e.target.closest('.analysis-action-bar')) return;
            openCardModal({
                name: getProviderName(provider),
                provider: provider,
                meta: `<div class="agent-meta"><span>${getProviderName(provider)}</span><span>${res.model || provider}</span></div>`,
                content: res.response,
                model: res.model || provider
            });
        });

        // Store Response for Context
        sessionState.lastResponses[provider] = res.response;

        councilGrid.appendChild(card);
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
                provider: 'red_team',
                meta: `<div class="agent-meta"><span style="color:#FF4444">RED TEAM</span><span>EXPLOIT</span></div>`,
                content: res.response,
                model: "CRITICAL"
            });
        });

        councilGrid.appendChild(card);
    }

    // FALCON REDACTION SUMMARY CARD
    if (data.falcon && data.falcon.enabled) {
        const fc = data.falcon;
        const falconCard = document.createElement("div");
        falconCard.className = "agent-card falcon-card";

        const levelColor = fc.level === 'BLACK' ? '#FF4444'
                         : fc.level === 'STANDARD' ? '#FFB020'
                         : '#00FF9D';

        const riskColor = fc.exposure_risk === 'critical' ? '#FF4444'
                        : fc.exposure_risk === 'high' ? '#FF6B6B'
                        : fc.exposure_risk === 'medium' ? '#FFB020'
                        : '#00FF9D';

        const countsHtml = Object.entries(fc.counts || {})
            .map(([cat, n]) => `<span class="falcon-cat">${cat}: ${n}</span>`)
            .join('');

        falconCard.innerHTML = `
            <div class="precision-header" style="border-bottom:1px solid ${levelColor}40;">
                <div class="ph-left">
                    <div class="ph-model-name" style="color:${levelColor}">&#x1F985; FALCON PROTOCOL</div>
                    <div class="ph-role-label" style="color:${levelColor}99">SECURE GOVERNANCE | LEVEL: ${fc.level}</div>
                </div>
                <div class="ph-right" style="flex-direction:row;align-items:center;gap:8px;">
                    <div class="metric-pill" style="color:${levelColor};border-color:${levelColor}40;">${fc.redacted_entity_count} REDACTED</div>
                    ${fc.high_risk_items_count > 0 ? `<div class="metric-pill" style="color:#FF4444;border-color:rgba(255,68,68,0.3);">${fc.high_risk_items_count} HIGH-RISK</div>` : ''}
                    <div class="metric-pill" style="color:${riskColor};border-color:${riskColor}40;">RISK: ${fc.exposure_risk.toUpperCase()}</div>
                    <div class="tool-action" onclick="event.stopPropagation(); copyTextToClipboard(this.closest('.agent-card').querySelector('.agent-response').innerText, 'Falcon Protocol copied')" title="Copy">📋</div>
                </div>
            </div>
            <div class="agent-response" style="padding:16px;">
                <p style="color:#8b949e;font-size:12px;margin-bottom:10px;">
                    Sensitive entities were stripped from the query before reaching any AI provider.
                    Placeholder tokens maintain structural integrity for reasoning without exposing protected data.
                </p>
                <div class="falcon-counts" style="display:flex;gap:8px;flex-wrap:wrap;">
                    ${countsHtml}
                </div>
            </div>
        `;
        analysisGrid.insertBefore(falconCard, analysisGrid.firstChild);
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
                <div class="tool-action" onclick="event.stopPropagation(); copyTextToClipboard(this.closest('.agent-card').querySelector('.exec-brief').innerText, 'Executive Brief copied')" title="Copy" style="display:inline-block;margin-left:8px;cursor:pointer;">📋</div>
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
        analysisGrid.appendChild(briefCard);
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
                <div class="tool-action" onclick="event.stopPropagation(); copyTextToClipboard(this.closest('.agent-card').innerText, 'Divergence analysis copied')" title="Copy" style="display:inline-block;margin-left:10px;cursor:pointer;">📋</div>
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
        analysisGrid.appendChild(divCard);
    }

    // Clear panes and populate
    councilPane.innerHTML = "";
    analysisPane.innerHTML = "";
    interPane.innerHTML = '<div class="interrogation-empty-state">No interrogation or verification results yet.</div>';

    // EXPORT COMMAND CENTER (Phase 6)
    renderExportToolbar(councilPane, data);

    // EXECUTIVE SUMMARY CARD — top of Council tab
    const execSummaryCard = buildExecutiveSummary(data, roleName, avgConfidence, totalTime);
    if (execSummaryCard) councilPane.appendChild(execSummaryCard);

    councilPane.appendChild(councilGrid);
    analysisPane.appendChild(analysisGrid);

    document.querySelector(".results-container").classList.add("visible");
    switchDockTab('council');
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

// ============================================================
// UX REFACTOR: HIGHLIGHT TOOLBAR (text selection)
// ============================================================
let activeActionContext = {
    type: 'highlight',
    provider: null,
    text: null,
    element: null
};

/**
 * Handle text selection to show the HighlightToolbar.
 */
function handleTextSelection(e) {
    // If clicking on a toolbar button, don't hide or reset
    if (e.target.closest('.highlight-toolbar') || e.target.closest('.analysis-action-bar')) return;

    const selection = window.getSelection();
    const text = selection.toString().trim();
    
    if (text && text.length > 3) {
        if (!selection.rangeCount) return;
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        const anchorEl = selection.anchorNode?.nodeType === 1 ? selection.anchorNode : selection.anchorNode?.parentElement;
        const focusEl = selection.focusNode?.nodeType === 1 ? selection.focusNode : selection.focusNode?.parentElement;
        const agentCard = anchorEl?.closest?.('.agent-card') || focusEl?.closest?.('.agent-card');
        
        if (!agentCard) return; // Only show for text inside agent cards
        
        showHighlightToolbar(rect, text, agentCard.dataset.provider);
    } else {
        // Use a small delay to allow clicking buttons
        setTimeout(() => {
            if (!window.getSelection().toString().trim()) {
                hideHighlightToolbar();
            }
        }, 150);
    }
}

function showHighlightToolbar(rect, text, provider) {
    let toolbar = document.getElementById('highlight-toolbar');
    if (!toolbar) {
        toolbar = document.createElement('div');
        toolbar.id = 'highlight-toolbar';
        toolbar.className = 'highlight-toolbar';
        toolbar.innerHTML = `
            <button class="ht-btn interrogate" title="Interrogate Selection">🔎 INTERROGATE</button>
            <button class="ht-btn verify" title="Verify Selection">⚖️ VERIFY</button>
            <button class="ht-btn visualize" title="Visualize Selection">📊 VIZ</button>
            <button class="ht-btn document" title="Document Selection">📄 DOC</button>
        `;
        document.body.appendChild(toolbar);
        
        toolbar.querySelector('.interrogate').onclick = (e) => { e.stopPropagation(); runHighlightAction('interrogate'); };
        toolbar.querySelector('.verify').onclick = (e) => { e.stopPropagation(); runHighlightAction('verify'); };
        toolbar.querySelector('.visualize').onclick = (e) => { e.stopPropagation(); runHighlightAction('visualize'); };
        toolbar.querySelector('.document').onclick = (e) => { e.stopPropagation(); runHighlightAction('document'); };
    }
    
    toolbar.style.display = 'flex';
    const toolbarWidth = toolbar.offsetWidth || 280;
    const toolbarHeight = toolbar.offsetHeight || 40;
    const desiredLeft = rect.left + (rect.width / 2) - (toolbarWidth / 2);
    const desiredTop = rect.top - toolbarHeight - 10;
    const clampedLeft = Math.max(8, Math.min(desiredLeft, window.innerWidth - toolbarWidth - 8));
    const fallbackTop = rect.bottom + 10;
    const clampedTop = desiredTop < 8 ? Math.min(fallbackTop, window.innerHeight - toolbarHeight - 8) : desiredTop;

    toolbar.style.left = `${clampedLeft}px`;
    toolbar.style.top = `${clampedTop}px`;
    
    activeActionContext = {
        type: 'highlight',
        provider: provider,
        text: text,
        element: null
    };
    sessionState.selectedText = text;
    sessionState.highlightToolbarVisible = true;
}

function hideHighlightToolbar() {
    const toolbar = document.getElementById('highlight-toolbar');
    if (toolbar) toolbar.style.display = 'none';
    sessionState.selectedText = "";
    sessionState.highlightToolbarVisible = false;
}

/**
 * Run actions from the highlight toolbar.
 */
function runHighlightAction(action) {
    const { provider, text } = activeActionContext;
    if (!text) return;
    
    switch(action) {
        case 'interrogate':
            openInterrogation(getProviderName(provider), text);
            break;
        case 'verify':
            executeVerify(text, getProviderName(provider));
            break;
        case 'visualize':
            const query = `VISUALIZE SELECTION: "${text}". Create a Mermaid JS chart.`;
            triggerCouncil(query);
            break;
        case 'document':
            saveReport();
            break;
    }
    
    window.getSelection().removeAllRanges();
    hideHighlightToolbar();
}

function setupInterrogation() {
    // Replaces the old mouseup logic
    document.addEventListener('mouseup', handleTextSelection);

    // Initial listener for external dock buttons if they still exist
    const dockBtn = document.getElementById('btn-dock');
    if (dockBtn) {
        dockBtn.addEventListener('click', () => {
             const selection = window.getSelection().toString().trim();
             if (selection) {
                 ResearchDock.add(selection, 'selection');
                 showProcessingToast("Snippet docked!");
                 window.getSelection().removeAllRanges();
             }
        });
    }
}
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
    logTelemetry("Korum OS Initialized", "system");

    positionNodes();
    setupActionBindings();
    sentinelChat.init();
    setupInterrogation();
    initDockTabs();
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
function showErrorCard(msg) {
    logTelemetry(`System error: ${msg}`, "error");
    const safeMsg = "The council encountered an issue processing your query. Please try again or adjust your input.";
    const container = document.getElementById('pane-council') || document.querySelector(".results-content");
    container.innerHTML = `<div class="consensus-card" style="border-color: red;"><div class="consensus-title" style="color:red;">SYSTEM ERROR</div><div class="consensus-body">${safeMsg}</div></div>`;
    document.querySelector(".results-container").classList.add("visible");
    switchDockTab('council');
}
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

        // Show Recall + New Session buttons if we have results
        const content = document.getElementById('pane-council');
        if (content && content.children.length > 0) {
            document.getElementById('recallAnalysisBtn').style.display = 'block';
            document.getElementById('resetSessionBtn').style.display = 'block';
        }
    }, 500);
}
function resetUI() {
    const btn = document.querySelector('.trigger-scan');
    const field = document.querySelector('.glass-textarea');
    if (btn) btn.innerText = "Convene Council";
    if (field) field.disabled = false;
    updateSystemStatus("READY");
    // Clean up processing animations
    document.body.classList.remove("activated");
    const globe = document.querySelector(".globe");
    if (globe) globe.classList.remove("processing");
    const activeCard = document.getElementById("activeAgentCard");
    if (activeCard) activeCard.classList.remove("visible");
}
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

    // Telemetry stays internal — no console leak
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
            // Copy clean text from rendered modal content (strips HTML tags)
            const modalContent = document.getElementById('modalContent');
            const cleanText = modalContent ? modalContent.innerText : currentModalData.content;
            copyTextToClipboard(cleanText, "Response copied to clipboard");
        }
    });

    document.getElementById('modalInterrogateBtn')?.addEventListener('click', () => {
        if (currentModalData) {
            const providerName = currentModalData.name || getProviderName(currentModalData.provider);
            openInterrogation(providerName);
        }
    });

    document.getElementById('modalVerifyBtn')?.addEventListener('click', () => {
        if (currentModalData) {
            const providerName = currentModalData.name || getProviderName(currentModalData.provider);
            executeVerify(currentModalData.content, providerName);
        }
    });

    document.getElementById('modalVisualizeBtn')?.addEventListener('click', () => {
        if (currentModalData) {
            window.visualizeSelection(currentModalData.content);
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
        logTelemetry(`Social export error: ${error.message}`, "error");
        showProcessingToast("Export could not be completed. Please try again.");
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
        logTelemetry(`Export divergence: ${!!intelligenceObj.divergence_analysis}`, "process");
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
        logTelemetry(`Export error: ${error.message}`, "error");
        showProcessingToast("Export could not be completed. Please try again.");
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
        showProcessingToast("Clipboard unavailable. Please select and copy text manually.");
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
                logTelemetry(`Operation error: ${err.message}`, "error");
                showProcessingToast("Operation could not be completed. Please try again.");
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
                            const warRoomTab = document.querySelector('.nav-links a[data-role="War Room"]');
                            warRoomTab?.click();
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
                list.innerHTML = `<div class="library-empty">Unable to load audit log. Please check permissions and try again.</div>`;
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

// --- EXECUTION DASHBOARD RENDERER ---
function renderExecutionDashboard(metrics) {
    logTelemetry("Rendering Execution Dashboard", "system");

    // 1. Update Cost Matrix
    const runCostEl = document.getElementById('dash-run-cost');
    const sessionCostEl = document.getElementById('dash-session-cost');
    if (runCostEl) runCostEl.textContent = `$${(metrics.run_cost || 0).toFixed(4)}`;
    if (sessionCostEl) sessionCostEl.textContent = `$${(metrics.session_total_cost || 0).toFixed(4)}`;

    // 2. Update Execution Telemetry
    const responseTimeEl = document.getElementById('stat-latency');
    const workflowNameEl = document.getElementById('stat-workflow');
    const modelsUsedEl = document.getElementById('stat-models-count');

    if (responseTimeEl) responseTimeEl.textContent = `${((metrics.latency_ms || metrics.total_latency_ms || 0) / 1000).toFixed(2)}s`;
    if (workflowNameEl) workflowNameEl.textContent = (metrics.workflow_name || metrics.workflow || "RESEARCH").toUpperCase();
    if (modelsUsedEl) {
        const models = metrics.models_used || [];
        modelsUsedEl.textContent = models.length || "0";
    }

    // 3. Render Contribution Bars
    const contributionGrid = document.getElementById('contribution-bars');
    if (contributionGrid && metrics.ai_cost_breakdown) {
        contributionGrid.innerHTML = '';
        
        // Combine costs and contribution scores
        const providers = Object.keys(metrics.ai_cost_breakdown);
        providers.forEach(p => {
            const cost = metrics.ai_cost_breakdown[p] || 0;
            const score = metrics.contribution_scores ? (metrics.contribution_scores[p] || 0) : 0;
            
            // Map to mythical label or fallback to uppercase
            const PROVIDER_MYTHICAL_LABELS = {
                "openai": "Odin / OpenAI",
                "anthropic": "Tyr / Claude",
                "google": "Heimdall / Gemini",
                "perplexity": "Huginn / Perplexity",
                "mistral": "Mimir / Mistral",
                "local": "Oracle / Local AI"
            };
            const displayName = PROVIDER_MYTHICAL_LABELS[p] || p.toUpperCase();
            
            const row = document.createElement('div');
            row.className = 'contribution-row';
            row.innerHTML = `
                <div class="contribution-header">
                    <span class="provider-label">${displayName}</span>
                    <span class="provider-cost">$${cost.toFixed(4)}</span>
                </div>
                <div class="contribution-bar-container">
                    <div class="contribution-bar-fill" style="width: 0%;" data-target-width="${score}%"></div>
                    <span class="participation-pct">${Math.round(score)}%</span>
                </div>
            `;
            contributionGrid.appendChild(row);
        });

        // Trigger animations
        setTimeout(() => {
            contributionGrid.querySelectorAll('.contribution-bar-fill').forEach(bar => {
                bar.style.width = bar.dataset.targetWidth;
            });
        }, 100);
    }
}

// --- TACTICAL BILLING LEDGER ---
const BillingLedger = {
    modal: null,
    btn: null,
    closeBtn: null,

    init() {
        this.modal = document.getElementById('billingModalOverlay');
        this.btn = document.getElementById('billingNavBtn');
        this.closeBtn = document.getElementById('billingCloseBtn');

        if (this.btn) {
            this.btn.addEventListener('click', () => this.open());
        }
        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.close());
        }
        if (this.modal) {
            this.modal.addEventListener('click', (e) => {
                if (e.target === this.modal) this.close();
            });
        }
    },

    async open() {
        if (!this.modal) return;
        this.modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        await this.fetchStats();
    },

    close() {
        if (!this.modal) return;
        this.modal.style.display = 'none';
        document.body.style.overflow = '';
    },

    async fetchStats() {
        try {
            const res = await fetch('/api/usage/stats');
            const data = await res.json();
            if (data.error) throw new Error(data.error);

            this.render(data);
        } catch (e) {
            console.error('[BILLING] Fetch failed:', e);
        }
    },

    render(data) {
        // 1. Total Spend
        const totalDisp = document.getElementById('totalSpendDisplay');
        if (totalDisp) totalDisp.textContent = `$${data.total_spend.toFixed(4)}`;

        // 2. Daily Chart
        const dailyContainer = document.getElementById('dailyChartContainer');
        if (dailyContainer) {
            dailyContainer.innerHTML = '';
            const maxDaily = Math.max(...data.daily_stats.map(s => s.cost), 0.01);
            
            data.daily_stats.forEach(s => {
                const pct = (s.cost / maxDaily) * 100;
                const dateLabel = s.date.split('-').slice(1).join('/'); // MM/DD
                
                const wrapper = document.createElement('div');
                wrapper.className = 'billing-bar-wrapper';
                wrapper.innerHTML = `
                    <div class="bar-value">$${s.cost.toFixed(2)}</div>
                    <div class="billing-bar" style="height: ${pct}%"></div>
                    <div class="bar-label">${dateLabel}</div>
                `;
                dailyContainer.appendChild(wrapper);
            });
        }

        // 3. Provider Breakdown
        const providerContainer = document.getElementById('providerChartContainer');
        if (providerContainer) {
            providerContainer.innerHTML = '';
            const providers = Object.entries(data.provider_breakdown);
            const maxProv = Math.max(...providers.map(p => p[1]), 0.01);

            const PROVIDER_MYTHICAL_SHORT = {
                "openai": "Odin",
                "anthropic": "Tyr",
                "google": "Heimdall",
                "perplexity": "Huginn",
                "mistral": "Mimir",
                "local": "Oracle"
            };

            providers.forEach(([name, cost]) => {
                const pct = (cost / maxProv) * 100;
                const displayName = PROVIDER_MYTHICAL_SHORT[name] || name.toUpperCase();
                
                const wrapper = document.createElement('div');
                wrapper.className = 'billing-bar-wrapper';
                wrapper.innerHTML = `
                    <div class="bar-value">$${cost.toFixed(2)}</div>
                    <div class="billing-bar" style="height: ${pct}%"></div>
                    <div class="bar-label">${displayName}</div>
                `;
                providerContainer.appendChild(wrapper);
            });
        }

        // 4. Footer timestamp
        const lastUpd = document.getElementById('billingLastUpdate');
        if (lastUpd) lastUpd.textContent = `LAST SYNC: ${new Date().toLocaleTimeString()}`;
    }
};

// Initialize after DOM load
document.addEventListener('DOMContentLoaded', () => {
    BillingLedger.init();
});

// End of KorumOS Sentinel Logic
