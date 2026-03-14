
// KORUM V2: INTERACTIVE EDITOR EXTENSION
// Overrides the simplified modal logic with a full interactive editor

let currentPreviewData = null; // Global State for the Editor

// OVERRIDE: Open Modal with Editor
window.openArtifactModal = function (type, data) {
    if (typeof logTelemetry === 'function') logTelemetry(`Editor launching: ${type}`, "system");
    currentPreviewData = JSON.parse(JSON.stringify(data)); // Deep Copy
    currentPreviewData.type = type; // Store type
    renderPreviewEditor();

    const modal = document.getElementById('cardModal');
    if (modal) modal.classList.add('visible');
};

function renderPreviewEditor() {
    const data = currentPreviewData;
    if (!data) return;

    const modalTitle = document.getElementById('modalTitle');
    const modalMeta = document.getElementById('modalMeta');
    const modalContent = document.getElementById('modalContent');

    if (modalTitle) modalTitle.innerText = `EDITOR: ${data.type.toUpperCase()}`;
    if (modalMeta) modalMeta.innerHTML = `<div style="color:#00FF9D">${data.title || "Untitled"}</div>`;

    let html = `<div class="artifact-preview" style="font-family: 'Inter', sans-serif;">`;

    // Header Stats
    html += `<div style="margin-bottom:20px; color:#aaa; font-size:12px; display:flex; justify-content:space-between;">
        <span>${data.estimatedDuration || ''} • ${data.slides ? data.slides.length : 0} Slides</span>
        <span style="color:#FFB020; cursor:pointer;" onclick="alert('Analysis Mode coming soon')">✨ AI Analyze</span>
    </div>`;

    if (data.type === 'presentation' && data.slides) {
        html += `<div class="slides-grid" style="display:grid; gap:15px; max-height:60vh; overflow-y:auto; padding-right:10px;">`;

        data.slides.forEach((slide, idx) => {
            // Escape quotes for input value
            const safeTitle = (slide.title || "").replace(/"/g, '&quot;');

            html += `
                <div class="slide-card" id="slide-${idx}" style="background:rgba(255,255,255,0.05); padding:15px; border-radius:8px; border:1px solid rgba(255,255,255,0.1); position:relative; transition:all 0.2s;">
                    <div style="font-size:10px; color:#00FF9D; margin-bottom:5px; display:flex; justify-content:space-between;">
                        <span>SLIDE ${idx + 1}</span>
                        <span style="cursor:pointer; color:#FF4444;" onclick="deleteSlide(${idx})">🗑️</span>
                    </div>
                    
                    <!-- Editable Title Input -->
                    <input type="text" value="${safeTitle}" 
                        onchange="updateSlideTitle(${idx}, this.value)"
                        style="background:transparent; border:none; border-bottom:1px solid #444; color:#FFF; width:100%; font-size:14px; font-weight:700; margin-bottom:10px; padding:4px 0; font-family:'Inter';"
                        placeholder="Slide Title"
                    />

                    <ul style="padding-left:20px; margin:0; font-size:12px; color:#ddd;">
                        ${slide.content.map(c => `<li>${c}</li>`).join('')}
                    </ul>
                    
                    ${slide.chartData ? `<div style="margin-top:10px; font-size:10px; color:#FFB020;">📊 ${slide.chartData.type.toUpperCase()} Chart Included</div>` : ''}
                </div>
            `;
        });

        html += `</div>`;
    } else {
        html += `<pre style="color:#888;">Preview logic for ${data.type} coming soon.\n${JSON.stringify(data, null, 2)}</pre>`;
    }

    // Footer Actions
    html += `
        <div style="margin-top:20px; display:flex; justify-content:flex-end; gap:10px; border-top:1px solid #333; padding-top:15px;">
            <button class="btn-primary" style="background:transparent; border:1px solid #555;" onclick="closeCardModal()">CANCEL</button>
            <button class="btn-primary" style="background:#00FF9D; color:#000; font-weight:700;" onclick="confirmArtifactGeneration()">CONFIRM & CREATE</button>
        </div>
    `;

    html += `</div>`;
    if (modalContent) modalContent.innerHTML = html;
}

// --- Editor Helpers ---
window.updateSlideTitle = function (idx, newTitle) {
    if (currentPreviewData && currentPreviewData.slides[idx]) {
        currentPreviewData.slides[idx].title = newTitle;
        // logTelemetry is in korum.js, might not be accessible if scoped. Assuming global.
        if (typeof logTelemetry === 'function') logTelemetry(`Updated Slide ${idx + 1} Title`, "user");
    }
};

window.deleteSlide = function (idx) {
    if (confirm("Delete this slide?")) {
        currentPreviewData.slides.splice(idx, 1);
        renderPreviewEditor();
        if (typeof logTelemetry === 'function') logTelemetry("Deleted Slide", "user");
    }
};


window.confirmArtifactGeneration = function () {
    if (typeof logTelemetry === 'function') logTelemetry("Finalizing Artifact...", "process");

    // Create floating status
    const statusDiv = document.createElement('div');
    statusDiv.id = 'downloadStatus';
    statusDiv.style.cssText = 'position:fixed; bottom:20px; right:20px; background:#333; color:#fff; padding:10px 20px; border-radius:5px; z-index:10001; font-family:"JetBrains Mono", monospace; font-size:12px; border:1px solid #555;';
    statusDiv.innerText = "BUILDING ARTIFACT...";
    document.body.appendChild(statusDiv);

    authFetch('/api/generate_artifact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            type: currentPreviewData.type,
            preview: currentPreviewData
        })
    })
        .then(response => {
            if (!response.ok) throw new Error("Build Failed");
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            // Clean filename logic
            const safeTitle = (currentPreviewData.title || "artifact").replace(/[^a-z0-9]/gi, '_');
            a.download = `${safeTitle}.pptx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            statusDiv.innerText = "DOWNLOAD COMPLETE";
            statusDiv.style.background = "#00FF9D";
            statusDiv.style.color = "#000";
            setTimeout(() => {
                if (document.body.contains(statusDiv)) document.body.removeChild(statusDiv);
            }, 3000);

            closeCardModal();
        })
        .catch(err => {
            console.error(err);
            statusDiv.innerText = "BUILD FAILED";
            statusDiv.style.background = "#FF4444";
            setTimeout(() => {
                if (document.body.contains(statusDiv)) document.body.removeChild(statusDiv);
            }, 3000);
        });
};
