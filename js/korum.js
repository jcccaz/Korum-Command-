/* KORUM-OS Logic - Fully Integrated (Telemetry, Interrogation, Charts) */

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
                output += `*Source: ${s.source} | ${s.timestamp.toLocaleTimeString()}*\n\n`;
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

        // Add CSV Export button to toolbar if not present
        const toolbar = container.querySelector('.dock-toolbar');
        if (toolbar && !toolbar.querySelector('.btn-csv-export')) {
            const csvBtn = document.createElement('button');
            csvBtn.className = 'dock-action btn-csv-export';
            csvBtn.title = 'Export Tabular Data as CSV';
            csvBtn.innerHTML = '📊 Export CSV';
            csvBtn.onclick = () => this.exportAll('csv');
            toolbar.appendChild(csvBtn);
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

    // Save to localStorage
    save() {
        try {
            localStorage.setItem('korum-dock', JSON.stringify(this.snippets));
        } catch (e) {
            console.warn('Could not save dock to localStorage', e);
        }
    },

    // Load from localStorage
    load() {
        try {
            const saved = localStorage.getItem('korum-dock');
            if (saved) {
                this.snippets = JSON.parse(saved).map(s => ({
                    ...s,
                    timestamp: new Date(s.timestamp)
                }));
            }
        } catch (e) {
            console.warn('Could not load dock from localStorage', e);
        }
    },

    // Initialize dock
    init() {
        this.load();
        this.render();
        logTelemetry("Research Dock: ONLINE", "success");
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
    document.querySelector(`.comms-tab[data-mode="${mode}"]`)?.classList.add('active');

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

        card.title = status.lastError
            ? `${provider.toUpperCase()}: ${status.lastError}`
            : `${provider.toUpperCase()} - Online`;
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
    "War Room": { openai: "strategist", anthropic: "containment", google: "takeover", perplexity: "scout" },
    "Deep Research": { openai: "analyst", anthropic: "researcher", google: "historian", perplexity: "scout" },
    "Creative Council": { openai: "writer", anthropic: "innovator", google: "marketing", perplexity: "social" },
    "Code Audit": { openai: "architect", anthropic: "integrity", google: "hacker", perplexity: "optimizer" },
    "System Core": { openai: "visionary", anthropic: "architect", google: "critic", perplexity: "researcher" }
};

// Available Roles for Manual Cycling
const AVAILABLE_ROLES = {
    openai: ["STRATEGIST", "ANALYST", "WRITER", "ARCHITECT", "VISIONARY"],
    anthropic: ["CONTAINMENT", "RESEARCHER", "INNOVATOR", "INTEGRITY", "ARCHITECT"],
    google: ["TAKEOVER", "HISTORIAN", "MARKETING", "HACKER", "CRITIC"],
    perplexity: ["SCOUT", "SOCIAL", "OPTIMIZER", "RESEARCHER"],
    mistral: ["ANALYST", "STRATEGIST", "CODING", "CREATIVE"],
    local: ["ORACLE", "GUARDIAN", "OFFLINE"]
};

let activeSelection = "";
let customRolesActive = false;

// --- AGENT DECK LOGIC ---
function cycleRole(provider) {
    const card = document.querySelector(`.deck-card.${provider}`);

    // If card is OFFLINE, clicking resets circuit breaker
    if (card && card.classList.contains('status-offline')) {
        AIHealth.status[provider] = { state: 'healthy', lastCheck: null, failures: 0, lastError: null };
        AIHealth.updateCardUI(provider);
        logTelemetry(`${provider.toUpperCase()}: Circuit breaker RESET`, "success");
        return;
    }

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
const activeModes = { v2: true, red: false };

function toggleMode(mode) {
    const btn = document.getElementById(`btn-mode-${mode}`);
    if (!btn) return;

    activeModes[mode] = !activeModes[mode];

    if (activeModes[mode]) {
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
    setupInteractions();
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

function setupInteractions() {
    document.querySelectorAll('.node').forEach(node => node.addEventListener('click', () => node.classList.toggle('selected')));
    const navLinks = document.querySelectorAll('.nav-links a');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            // UPDATE DECK
            const role = link.dataset.role;
            const config = PROTOCOL_CONFIGS[role];
            if (config) {
                document.getElementById('roleLabel-openai').innerText = config.openai.toUpperCase();
                document.getElementById('roleLabel-anthropic').innerText = config.anthropic.toUpperCase();
                document.getElementById('roleLabel-google').innerText = config.google.toUpperCase();
                document.getElementById('roleLabel-perplexity').innerText = config.perplexity.toUpperCase();
                customRolesActive = false;
            }

            logTelemetry(`Protocol Switched: ${role.toUpperCase()}`, "process");
            // updateSystemStatus removed as we killed the text
        });
    });

    // SMART SUGGESTION SYSTEM
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
                suggestedRoles = PROTOCOL_CONFIGS[suggestedWorkflow];

                document.getElementById('detectedCategory').textContent = suggestedWorkflow;
                document.getElementById('suggestedWorkflow').textContent = suggestedWorkflow;
                suggestionBox.classList.remove('hidden');

                // Pre-populate dropdowns
                if (suggestedRoles) {
                    document.getElementById('roleSelectOpenAI').value = suggestedRoles.openai;
                    document.getElementById('roleSelectAnthropic').value = suggestedRoles.anthropic;
                    document.getElementById('roleSelectGoogle').value = suggestedRoles.google;
                    document.getElementById('roleSelectPerplexity').value = suggestedRoles.perplexity;
                }

                logTelemetry(`Query Analyzed: ${suggestedWorkflow}`, "process");
            }, 800);
        } else {
            suggestionBox.classList.add('hidden');
            roleCustomization.classList.add('hidden');
        }
    });

    // Use Suggested Button
    document.getElementById('useSuggestedBtn')?.addEventListener('click', () => {
        const suggestedWorkflow = document.getElementById('suggestedWorkflow').textContent;
        const targetTab = document.querySelector(`.nav-links a[data-role="${suggestedWorkflow}"]`);
        if (targetTab) {
            targetTab.click();
        }
        suggestionBox.classList.add('hidden');
        roleCustomization.classList.add('hidden');
        customRolesActive = false;
        logTelemetry(`Applied Suggested Config: ${suggestedWorkflow}`, "system");
    });

    // Customize Roles Button
    document.getElementById('customizeBtn')?.addEventListener('click', () => {
        roleCustomization.classList.toggle('hidden');
        customRolesActive = !customRolesActive;
        logTelemetry("Custom Role Editor Opened", "system");
    });

    // Dismiss Suggestion
    document.getElementById('dismissSuggestionBtn')?.addEventListener('click', () => {
        suggestionBox.classList.add('hidden');
        roleCustomization.classList.add('hidden');
    });

    // Clear Button
    document.getElementById('clearInputBtn')?.addEventListener('click', () => {
        document.getElementById('queryInput').value = '';
        logTelemetry("Input Cleared", "system");
    });

    // Rotate Roles Button
    document.getElementById('rotateRolesBtn')?.addEventListener('click', (e) => {
        const btn = e.target;
        btn.style.transition = "transform 0.5s ease";
        btn.style.transform = "rotate(360deg)";
        setTimeout(() => btn.style.transform = "none", 500);

        rotateRoles();
        logTelemetry("Council Roles Rotated", "process");
    });

    document.querySelector('.trigger-scan')?.addEventListener('click', async (e) => {
        const queryField = document.getElementById('queryInput');
        const query = queryField.value.trim();
        if (!query) { alert("Protocol Violation: Query Required."); return; }

        // Reset session state for new query
        sessionState.originalQuery = query;
        sessionState.lastResponses = {};
        sessionState.targetCard = null;

        triggerCouncil(query);
    });

    document.querySelector('.close-results')?.addEventListener('click', closeResults);

    // RECALL BUTTON LOGIC
    const recallBtn = document.getElementById('recallAnalysisBtn');
    if (recallBtn) {
        recallBtn.addEventListener('click', () => {
            document.querySelector(".results-container").classList.add("visible");
            recallBtn.style.display = 'none';
        });
    }

    // Wire up Command Console
    const consoleInput = document.getElementById("consoleInput");
    const consoleSubmit = document.getElementById("consoleSubmitBtn");

    if (consoleInput && consoleSubmit) {
        const sendCmd = () => {
            const cmd = consoleInput.value.trim();
            if (cmd) {
                // Build Contextual Query
                let contextualQuery = cmd;

                if (sessionState.originalQuery) {
                    const targetResponse = sessionState.targetCard
                        ? sessionState.lastResponses[sessionState.targetCard] || "N/A"
                        : Object.values(sessionState.lastResponses).join("\n---\n").substring(0, 2000);

                    contextualQuery = `
ORIGINAL TOPIC: ${sessionState.originalQuery}

CONTEXT (THE RESPONSE BEING CHALLENGED):
${targetResponse.substring(0, 1500)}...

USER CHALLENGE:
${cmd}

INSTRUCTIONS: Address the challenge directly. Do NOT lose the context of the ORIGINAL TOPIC.
                    `.trim();
                }

                logTelemetry(`Interrogation: ${cmd}`, "user");

                // Show Loader
                const container = document.querySelector(".results-content");
                if (container) {
                    const loader = document.createElement("div");
                    loader.id = "interrogation-loader";
                    loader.innerHTML = `<div style="text-align:center; padding:40px; color:#00FF9D;"><div style="font-size:24px; animation: pulse 1s infinite;">⚡</div><div style="margin-top:10px; font-family:'JetBrains Mono',monospace;">INTERROGATING TARGET... CONTEXT LOCKED</div></div>`;
                    container.prepend(loader);
                }

                triggerCouncil(contextualQuery);
                consoleInput.value = "";
            }
        };
        consoleSubmit.addEventListener('click', sendCmd);
        consoleInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendCmd(); });
    }
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

function updateSystemStatus(text) { const el = document.getElementById('system-status-val'); if (el) el.innerText = text.toUpperCase(); }

async function triggerCouncil(query) {
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

    if (isV2) {
        // V2 Functional Pipeline
        updateSystemStatus("EXECUTING CHAIN");
        try {
            await executeReasoningChain(query);
        } catch (error) {
            console.error(error); showErrorCard(error.message); logTelemetry(`ERROR: ${error.message}`, "system"); resetUI();
        }
    } else {
        // V1 Council Mode
        try {
            await executeCouncil(query, activeRoleName);
        } catch (error) {
            console.error(error); showErrorCard(error.message); logTelemetry(`ERROR: ${error.message}`, "system"); resetUI();
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
        hacker_mode: hackerMode
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

        // Use centralized formatter
        const rawContent = typeof content === 'object' ? JSON.stringify(content, null, 2) : content;
        const formattedRaw = formatV2Content(content, phase);

        // Find corresponding results entry for truth data
        const modelToProvider = { 'claude': 'anthropic', 'gpt': 'openai', 'gemini': 'google', 'mistral': 'mistral', 'oracle': 'local' };
        const providerKey = Object.keys(modelToProvider).find(k => model.toLowerCase().includes(k));
        const res = result.results ? result.results[modelToProvider[providerKey]] : null;
        const verifiedClaims = res?.verified_claims || [];
        const truthScore = res?.truth_meter !== undefined ? res.truth_meter : (metricData?.score || 85);

        const displayContent = highlightClaims(formattedRaw, verifiedClaims);

        // Metrics Defaults
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
                    <button class="interrogate-btn" onclick="event.stopPropagation(); openInterrogation('${title}')">
                        🔍 INTERROGATE
                    </button>
                    <div class="metric-pill">$${cost.toFixed(4)}</div>
                    <div class="metric-pill time">${time}s</div>
                    <div class="tool-action" onclick="event.stopPropagation();" title="Save">💾</div>
                    <div class="tool-action" onclick="event.stopPropagation(); window.visualizeSelection()" title="Chart">📊</div>
                    <div class="tool-action" onclick="event.stopPropagation(); copyToClipboard('${displayContent.replace(/<[^>]*>/g, '')}')" title="Copy">📋</div>
                </div>
            </div>
            <div class="agent-response">${displayContent}</div>
        `;

        // Click to expand matches card content format
        card.addEventListener('click', () => {
            openCardModal({
                name: title,
                meta: `<div class="agent-meta"><span>${phase}</span><span>${model}</span></div>`,
                content: displayContent // Pre-formatted HTML
            });
        });

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

    // Show Command Console
    const console = document.getElementById("commandConsole");
    if (console) console.style.display = "block";

    logTelemetry("Pipeline Execution Complete.", "system");
}

// --- SESSION STATE (Context Tracking) ---
let sessionState = {
    originalQuery: "",
    lastResponses: {},  // { openai: "...", anthropic: "...", ... }
    targetCard: null    // Which card is being interrogated
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
    sessionState.targetCard = nameToKey[cleanName] || Object.keys(nameToKey).find(k => cleanName.includes(k)) ? nameToKey[Object.keys(nameToKey).find(k => cleanName.includes(k))] : null;

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

window.visualizeSelection = function () {
    const selection = window.getSelection().toString();
    if (!selection) return;

    document.getElementById('interrogation-tooltip').style.display = 'none';

    // Show processing feedback
    logTelemetry("VISUALIZING SELECTION...", "process");
    showProcessingToast("Generating visualization...");

    // Build the query for table/chart generation
    const query = `Convert this data into a formatted table or chart. If it's tabular data, create a clean markdown table. If it's numerical, suggest a chart type. DATA: "${selection}"`;

    // Trigger the council to process it
    triggerCouncil(query);
};

// Processing Toast for user feedback
function showProcessingToast(message) {
    let toast = document.getElementById('processing-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'processing-toast';
        toast.style.cssText = `
            position: fixed;
            bottom: 80px;
            right: 20px;
            background: rgba(0,0,0,0.9);
            border: 1px solid #00FF9D;
            color: #00FF9D;
            padding: 12px 20px;
            border-radius: 8px;
            font-family: var(--font-mono);
            font-size: 12px;
            z-index: 9999;
            display: flex;
            align-items: center;
            gap: 10px;
            box-shadow: 0 4px 20px rgba(0,255,157,0.2);
        `;
        document.body.appendChild(toast);
    }
    toast.innerHTML = `<span style="animation: pulse 1s infinite;">⚡</span> ${message}`;
    toast.style.display = 'flex';

    // Auto-hide after 5 seconds
    setTimeout(() => { toast.style.display = 'none'; }, 5000);
}

function formatV2Content(content, phase) {
    let displayContent = "";

    // SPECIAL RENDERING FOR PHASE 1 (JSON)
    if (phase === "CONSTRAINT ANALYSIS" && typeof content === 'object') {
        displayContent += `<div style="margin-bottom:10px;"><strong style="color:#00FF9D">CORE GOAL:</strong><br>${content.core_goal || "N/A"}</div>`;

        if (content.explicit_constraints?.length) {
            displayContent += `<strong style="color:#FFB020">EXPLICIT CONSTRAINTS:</strong><ul style="margin-top:5px; padding-left:20px; color:#ddd;">`;
            content.explicit_constraints.forEach(c => displayContent += `<li>${c}</li>`);
            displayContent += `</ul>`;
        }

        if (content.implied_constraints?.length) {
            displayContent += `<br><strong style="color:#00BFFF">IMPLIED CONSTRAINTS:</strong><ul style="margin-top:5px; padding-left:20px; color:#ddd;">`;
            content.implied_constraints.forEach(c => displayContent += `<li>${c}</li>`);
            displayContent += `</ul>`;
        }
    } else {
        // Standard Text Formatting for Phases 2-4
        displayContent = formatV2Text(typeof content === 'object' ? JSON.stringify(content, null, 2) : content);
    }
    return displayContent;
}

function formatV2Text(text) {
    if (!text) return "";
    return text
        .replace(/^## (.*?)$/gm, '<h3 style="color:#00FF9D; margin-top:15px; border-bottom:1px solid #333; padding-bottom:5px;">$1</h3>') // H2 -> H3 Styled
        .replace(/^### (.*?)$/gm, '<h4 style="color:#FFB020; margin-top:10px;">$1</h4>') // H3 -> H4 Styled
        .replace(/\*\*(.*?)\*\*/g, '<strong style="color:#FFF;">$1</strong>') // Bold -> White Strong
        .replace(/^- (.*?)$/gm, '• $1<br>') // List items
        .replace(/\n\d\. (.*?)$/gm, '<div style="margin-left:10px; margin-bottom:4px;"><strong>$1</strong></div>'); // Numbered lists (fixed regex)
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
    console.log(`[CORE] Executing: ${roleName} | V2: ${useV2} | Red Team: ${isRedTeam}`);

    const payload = {
        question: query,
        council_mode: true,
        council_roles: roleConfig,
        active_models: ["openai", "anthropic", "google", "perplexity", "mistral", "local"],
        use_v2: true, // FORCED V2 FOR TESTING
        is_red_team: isRedTeam     // Red Team Logic
    };

    const response = await fetch('/api/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    if (!response.ok) throw new Error(`HTTP Error ${response.status}`);
    const data = await response.json();
    renderResults(data, roleName);
    resetUI();
}

function renderResults(data, roleName) {
    // Hide processing toast
    const toast = document.getElementById('processing-toast');
    if (toast) toast.style.display = 'none';

    console.log("DEBUG: Full response data:", data);
    console.log("DEBUG: Individual results:", data.results);
    const container = document.querySelector(".results-content");
    const grid = document.createElement("div"); grid.className = "results-grid";

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
            return; // Don't render failed cards
        }

        // Capture for Context
        if (sessionState && sessionState.lastResponses) {
            sessionState.lastResponses[provider] = res.response;
        }

        // Create card
        const card = document.createElement("div"); card.className = `agent-card ${provider}`;

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
                    <div class="tool-action" onclick="event.stopPropagation();" title="Save">💾</div>
                    <div class="tool-action" onclick="event.stopPropagation(); window.visualizeSelection()" title="Chart">📊</div>
                    <div class="tool-action" onclick="event.stopPropagation(); copyToClipboard(decodeURIComponent('${encodeURIComponent(displayContent)}'))" title="Copy">📋</div>
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

            // MIRROR TO GLOBAL COMMS
            sentinelChat.appendMessage(query, 'user');
            sentinelChat.appendMessage("Redirecting Council for targeted interrogation...", 'sentinel thinking');

            // UI Feedback
            const queryInput = document.getElementById('queryInput');
            if (queryInput) {
                queryInput.value = query;
                queryInput.classList.add('flash-active');
                setTimeout(() => queryInput.classList.remove('flash-active'), 500);
            }

            triggerCouncil(query);
            // reset selection to avoid ghost query on next generic trigger
            window.getSelection().removeAllRanges();
            activeSelection = "";
        }
    });

    document.getElementById('btn-visualize-select').addEventListener('click', () => {
        if (activeSelection) {
            const query = `VISUALIZE SELECTION: "${activeSelection}". 
            Create a Mermaid JS chart (flowchart or pie) specifically based on this data.`;
            tooltip.style.display = 'none';

            const queryInput = document.getElementById('queryInput');
            if (queryInput) queryInput.value = query;

            triggerCouncil(query);
            window.getSelection().removeAllRanges();
            activeSelection = "";
        }
    });
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
function updateSystemStatus(status) {
    const el = document.getElementById('system-status-text');
    if (el) el.innerText = status;
}

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

    init: function () {
        const input = document.getElementById('sentinelInput');
        const sendBtn = document.getElementById('sentinelSendBtn');

        if (input && sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.sendMessage();
            });
        }
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

        // Auto-scroll to bottom
        const container = document.getElementById('sentinelChat');
        container.scrollTop = container.scrollHeight;

        return id;
    }
};

// Main initialization - consolidates all onload logic
window.onload = function () {
    console.log("Korum OS Initialized...");

    positionNodes();
    setupInteractions();
    sentinelChat.init();
    setupInterrogation();
    pushHeartbeat();
    setInterval(pushHeartbeat, 5000);

    // Initialize AI Health Monitoring
    AIHealth.init();

    // Initialize Research Dock
    ResearchDock.init();

    logTelemetry("System Boot Sequence Complete", "system");
}

// UTILS
function getProviderName(key) { const names = { openai: "Strategic Core", anthropic: "Architect", google: "Critic", perplexity: "Intel", mistral: "Analyst", local: "Oracle" }; return names[key] || key; }
function formatText(text) {
    if (!text) return "";
    return text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/### (.*?)\n/g, '<h4 style="color:#FFF; margin:10px 0;">$1</h4>')
        .replace(/- (.*?)\n/g, '• $1<br>')
        .replace(/```mermaid([\s\S]*?)```/g, '<div class="mermaid">$1</div>'); // Map to mermaid class for render
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

        // Keep only last 12 lines
        while (telemetryLog.children.length > 12) {
            telemetryLog.removeChild(telemetryLog.firstChild);
        }
    }

    // 2. Update Micro Tracker (Left Panel - Legacy Support)
    // This ensures functionalities like the Agent Status Card still work
    const tracker = document.getElementById('tracker-status');
    const trackerMsg = document.getElementById('tracker-msg');
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

// --- EXPORT TOOLBAR (Rendered in GLOBAL COMMS card) ---
function renderExportToolbar(_container, _data) {
    const sentinelCard = document.querySelector('.sentinel-card');
    if (!sentinelCard) return;

    let toolbar = sentinelCard.querySelector('.export-command-center');
    if (!toolbar) {
        toolbar = document.createElement("div");
        toolbar.className = "export-command-center";
        toolbar.style.cssText = "margin-top:auto; padding:12px; background:rgba(0,0,0,0.4); border-radius:8px; border:1px solid rgba(255,255,255,0.1);";
        toolbar.innerHTML = `
            <div class="ecc-label" style="margin-bottom:10px; font-size:11px; color:#FFB020; letter-spacing:1px;">EXPORT RESULTS</div>
            <div class="ecc-controls" style="display:flex; flex-direction:column; gap:8px;">
                <select id="exportSocial" onchange="handleSocialExport(this.value)" style="font-size:12px; padding:8px 10px; background:rgba(0,0,0,0.5); border:1px solid rgba(255,255,255,0.2); color:#fff; border-radius:4px;">
                    <option value="" disabled selected>Share to Social...</option>
                    <option value="linkedin">LinkedIn Post</option>
                    <option value="twitter">X / Twitter Thread</option>
                    <option value="threads">Threads</option>
                    <option value="reddit">Reddit Post</option>
                    <option value="medium">Medium Article</option>
                </select>
                <select id="exportDoc" onchange="handleDocExport(this.value)" style="font-size:12px; padding:8px 10px; background:rgba(0,0,0,0.5); border:1px solid rgba(255,255,255,0.2); color:#fff; border-radius:4px;">
                    <option value="" disabled selected>Export Document...</option>
                    <option value="pdf">PDF Report</option>
                    <option value="docx">Word Document</option>
                    <option value="obsidian">Obsidian Note</option>
                    <option value="notion">Notion Page</option>
                    <option value="email">Email Draft</option>
                </select>
                <select id="exportPresent" onchange="handlePresentExport(this.value)" style="font-size:12px; padding:8px 10px; background:rgba(0,0,0,0.5); border:1px solid rgba(255,255,255,0.2); color:#fff; border-radius:4px;">
                    <option value="" disabled selected>Create Presentation...</option>
                    <option value="slides">Google Slides</option>
                    <option value="pptx">PowerPoint</option>
                    <option value="reveal">Reveal.js</option>
                </select>
            </div>
        `;
        // Insert at the bottom of sentinel card, after the input area
        sentinelCard.appendChild(toolbar);
    }
}

function handleSocialExport(platform) {
    if (!platform) return;
    logTelemetry(`Preparing ${platform.toUpperCase()} Export...`, "process");
}

function handleDocExport(format) {
    if (!format) return;
    logTelemetry(`Converting to ${format.toUpperCase()}...`, "process");
}

function handlePresentExport(format) {
    if (!format) return;
    const names = { slides: "Google Slides", pptx: "PowerPoint", reveal: "Reveal.js" };
    logTelemetry(`Generating ${names[format] || format} Presentation...`, "process");
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

    let highlighted = html;
    // Sort claims by length descending to avoid nested replacement issues
    const sortedClaims = [...claims].sort((a, b) => b.claim.length - a.claim.length);

    sortedClaims.forEach(c => {
        const claimText = c.claim;
        const status = c.status.toLowerCase();
        const score = c.score;
        const type = c.type;

        // Find the claim in the text
        const escapedClaim = claimText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(escapedClaim, 'g');

        const replacement = `<span class="claim ${status}" data-status="${status.toUpperCase()} (${score}%)" data-type="${type}" title="VERIFICATION: ${status.toUpperCase()}">${claimText}</span>`;

        highlighted = highlighted.replace(regex, replacement);
    });

    return highlighted;
}
