/* KORUM-OS Logic - Fully Integrated (Telemetry, Interrogation, Charts) */

// === GLOBAL STATE FOR EXPORTS ===
let lastCouncilData = null;
let lastQueryText = '';

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
        const resp = await fetch('/api/reports/save', {
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
    if (!list) return;
    list.innerHTML = '<div class="library-empty">Loading...</div>';

    try {
        const resp = await fetch('/api/reports/list');
        const data = await resp.json();
        if (!data.success || !data.reports.length) {
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
        list.innerHTML = '<div class="library-empty">Failed to load reports.</div>';
    }
}

async function recallReport(id) {
    try {
        const resp = await fetch(`/api/reports/${id}`);
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
        await fetch(`/api/reports/${id}`, { method: 'DELETE' });
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
        const resp = await fetch('/api/health/check');
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
            const response = await fetch('/api/summarize_snippets', {
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
            await fetch('/api/dock/save', {
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
            const response = await fetch('/api/dock/load');
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
    "Tech Council": { openai: "ai_architect", anthropic: "network", google: "telecom", perplexity: "scout", mistral: "hacker" }
};

// Available Roles for Manual Cycling
const AVAILABLE_ROLES = {
    openai: ["STRATEGIST", "ANALYST", "WRITER", "ARCHITECT", "VISIONARY", "JURIST", "MEDICAL", "CFO", "PHYSICIST", "BIZSTRAT", "AI_ARCHITECT", "NETWORK", "HEDGE_FUND"],
    anthropic: ["CONTAINMENT", "RESEARCHER", "INNOVATOR", "INTEGRITY", "ARCHITECT", "COMPLIANCE", "BIOETHICIST", "AUDITOR", "BIOLOGIST", "PRODUCT", "NETWORK", "TELECOM", "HEDGE_FUND"],
    google: ["TAKEOVER", "HISTORIAN", "MARKETING", "HACKER", "CRITIC", "ECONOMIST", "CHEMIST", "RESEARCHER", "NETWORK", "TELECOM", "HEDGE_FUND"],
    perplexity: ["SCOUT", "SOCIAL", "OPTIMIZER", "RESEARCHER"],
    mistral: ["ANALYST", "STRATEGIST", "CODING", "CREATIVE", "VALIDATOR", "NEGOTIATOR", "TAX", "PROFESSOR", "CFO", "WEB_DESIGNER", "HACKER", "HEDGE_FUND"],
    local: ["ORACLE", "GUARDIAN", "OFFLINE"]
};

let activeSelection = "";
let customRolesActive = false;
let actionBindingsInitialized = false;

// --- AGENT DECK LOGIC ---
function cycleRole(provider, event) {
    if (event) event.stopPropagation();

    // Toggle Logic: If clicking card background or avatar, toggle silenced status
    const isLabelClick = event && (event.target.id === `roleLabel-${provider}` || event.target.classList.contains('deck-role'));

    if (!isLabelClick) {
        const card = document.querySelector(`.deck-card.${provider}`);
        const isSilenced = card?.classList.contains('silenced');

        if (isSilenced) {
            card.classList.remove('silenced');
            logTelemetry(`${provider.toUpperCase()} ACTIVATED`, "success");
        } else {
            card?.classList.add('silenced');
            logTelemetry(`${provider.toUpperCase()} SILENCED`, "system");
        }
        return;
    }

    // Don't cycle if silenced
    const card = document.querySelector(`.deck-card.${provider}`);
    if (card?.classList.contains('silenced')) return;

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
    "Tech Council": ["technology", "infrastructure", "cloud", "devops", "network", "api", "database", "server", "deploy", "saas", "platform", "software", "hardware", "ai", "machine learning", "automation", "integration", "microservice", "kubernetes", "docker", "cyber", "firewall", "telecom", "fiber", "wireless", "5g", "routing", "bandwidth", "latency", "vpn", "encryption", "dns", "switch", "router", "cisco", "aws", "azure"],
    "Legal Review": ["legal", "law", "regulation", "compliance", "contract", "liability", "patent", "trademark", "lawsuit", "attorney"],
    "Medical Council": ["medical", "health", "clinical", "patient", "diagnosis", "treatment", "pharmaceutical", "disease", "therapy", "doctor"],
    "Finance Desk": ["finance", "investment", "revenue", "profit", "accounting", "tax", "budget", "portfolio", "stock", "dividend", "roi", "hedge fund", "arbitrage", "equity"],
    "Science Panel": ["science", "physics", "chemistry", "biology", "experiment", "hypothesis", "quantum", "molecular", "genetic", "laboratory"],
    "Startup Launch": ["startup", "launch", "business plan", "mvp", "funding", "venture", "pitch", "scalable", "bootstrap", "market fit"],
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
    document.getElementById('intakeCancelBtn')?.addEventListener('click', closeIntakeModal);
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
        if (agentCard && !target.closest('button') && !target.closest('.tool-action')) {
            const data = agentCard.dataset;
            openCardModal({
                name: data.name,
                meta: data.meta,
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

    const response = await fetch('/api/v2/reasoning_chain', {
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
    // Map display name back to provider key if possible
    const nameToKey = {
        "Strategic Core": "openai",
        "Architect": "anthropic",
        "Critic": "google",
        "Intel": "perplexity",
        "GPT-4o": "openai",
        "Claude": "anthropic",
        "Gemini": "google",
        "Perplexity": "perplexity"
    };

    // Clean name (remove emojis if any)
    const cleanName = targetName.replace(/[^a-zA-Z0-9\s-]/g, '').trim();
    const exactMatch = nameToKey[cleanName];
    const partialKey = Object.keys(nameToKey).find(k => cleanName.includes(k));
    sessionState.targetCard = exactMatch || (partialKey ? nameToKey[partialKey] : null);

    const consoleInput = document.getElementById("consoleInput");
    const consoleTarget = document.getElementById("consoleTarget");

    if (consoleTarget) {
        consoleTarget.innerText = `TARGET: ${targetName.toUpperCase()}`;
        consoleTarget.style.color = "#FF4444";
    }

    if (consoleInput) {
        consoleInput.value = "";
        consoleInput.placeholder = `Challenge ${targetName}'s response...`;
        consoleInput.focus();
    }

    // MIRROR ACTION TO COMMS
    sentinelChat.appendMessage(`LOCKING TARGET FOR INTERROGATION: ${targetName.toUpperCase()}`, 'user');
    sentinelChat.appendMessage(`Neural link locked on ${targetName}. Ready for tactical query.`, 'sentinel');

    logTelemetry(`Interrogation Lock: ${targetName}`, "user");
};

// --- PROMPT REFINEMENT (Enhance) ---
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
        const response = await fetch('/api/enhance_prompt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ draft: draft })
        });

        const data = await response.json();

        if (data.success) {
            // Typewriter effect for new text
            input.value = "";
            input.style.opacity = '1';
            let i = 0;
            const enhanced = data.enhanced_text;

            const typeInterval = setInterval(() => {
                input.value += enhanced.charAt(i);
                input.scrollTop = input.scrollHeight; // Auto-scroll
                i++;
                if (i >= enhanced.length) {
                    clearInterval(typeInterval);
                    logTelemetry(`Directive Optimized (${data.model})`, "success");
                    showProcessingToast("Prompt Enhanced.");
                }
            }, 10);
        } else {
            showProcessingToast("Enhancement Failed: " + (data.error || "Unknown"));
            input.style.opacity = '1';
        }
    } catch (e) {
        console.error(e);
        showProcessingToast("Network Error during Enhancement.");
        input.style.opacity = '1';
    } finally {
        btn.classList.remove('enhancing');
        btn.innerHTML = originalIcon;
    }
};

// Bind Enhancement Button
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('enhanceBtn')?.addEventListener('click', window.enhancePrompt);
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
    console.log(`[CORE] Executing: ${roleName} | V2: ${useV2} | Red Team: ${isRedTeam} | Live Data: ${useSerpAPI}`);

    const payload = {
        question: query,
        council_mode: true,
        council_roles: roleConfig,
        active_models: ["openai", "anthropic", "google", "perplexity", "mistral", "local"].filter(p => AIHealth.isAvailable(p)),
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
        response = await fetch('/api/ask', { method: 'POST', body: formData });
        pendingFiles = [];
        renderFilePreview();
    } else {
        response = await fetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
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

    console.log("DEBUG: Full response data:", data);
    console.log("DEBUG: Individual results:", data.results);
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
            // USE SELECTIVE CONTEXT
            const query = `INTERROGATE SELECTION: "${activeSelection}". 
            Context: Address ONLY this specific point from the response. Detect inaccuracies, missing nuance, or logical flaws.`;

            tooltip.style.display = 'none';

            // MIRROR TO GLOBAL COMMS (No longer overwriting queryInput)
            sentinelChat.appendMessage(`TARGETED CHALLENGE: "${activeSelection.slice(0, 50)}..."`, 'user');
            sentinelChat.appendMessage("Allocating Council resources for fact-check...", 'sentinel thinking');

            triggerCouncil(query);
            // reset selection
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
        const status = e.target.dataset.status;
        const providerName = e.target.closest('.agent-card')?.querySelector('.ph-model-name')?.innerText || 'Target';

        // Auto-trigger interrogation on the console
        const consoleInput = document.getElementById("consoleInput");
        if (consoleInput) {
            // First, lock the target
            openInterrogation(providerName);

            // Then, fill the challenge
            consoleInput.value = `FACT CHECK THIS: "${claimText}" (Labeled as ${status})`;
            consoleInput.focus();

            // UI Feedback
            sentinelChat.appendMessage(`Targeting violation: "${claimText}"`, 'user');
        }
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
        input.value = '';
        input.disabled = true;

        try {
            // Sentinel "Thinking" indicator
            const thinkingId = this.appendMessage("Analyzing...", 'sentinel thinking');

            const response = await fetch('/api/sentinel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query })
            });

            const data = await response.json();

            // Remove thinking indicator
            const thinkingEl = document.getElementById(thinkingId);
            if (thinkingEl) thinkingEl.remove();

            if (data.success) {
                this.appendMessage(data.response, 'sentinel');
                // Optional: Speak the response if voice enabled? (Later)
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
    // Clean internal structuring tags before formatting
    const cleanText = text.replace(/\[\/?(DECISION_CANDIDATE|RISK_VECTOR|METRIC_ANCHOR|TRUTH_BOMB)\]/g, "");

    return cleanText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/### (.*?)\n/g, '<h4 style="color:#FFF; margin:10px 0;">$1</h4>')
        .replace(/- (.*?)\n/g, '• $1<br>')
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
    fetch('/api/v2/progress')
        .then(res => res.json())
        .then(data => {
            if (data.status === 'processing') {
                // Continue polling
                setTimeout(pollV2Progress, 1000);
            } else if (data.status === 'complete') {
                updateSystemStatus("SYNTHESIZING");

                // Fetch final result
                fetch('/api/v2/result')
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
        pdf: 'Board Brief', docx: 'Executive Memo', xlsx: 'Intelligence Workbook',
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
        const payload = {
            intelligence_object: lastCouncilData.synthesis,
            format: format
        };

        const response = await fetch('/api/deploy_intelligence', {
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
        fetch('/api/generate_preview', {
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
    container.innerHTML = `<div class="action-panel-header">NEXT STEPS</div>`;
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
