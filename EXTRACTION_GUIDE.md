# KorumOS Extraction Guide

## Structure Created

Your standalone KorumOS project is now at: `C:\Users\carlo\Projects\KorumOS\`

### Files Already Created:
✅ `README.md` - Project documentation  
✅ `index.html` - Main interface (standalone, no Flask template tags)

### Files You Need to Copy Manually:

Due to workspace permissions, please manually copy these files from the TriAI project:

#### JavaScript (create `js/` folder):
```
FROM: C:\Users\carlo\OneDrive\Documents\Obsidian_Franknet\FrankNet\FrankNet\tri_ai_compare\static\korum.js
TO:   C:\Users\carlo\Projects\KorumOS\js\korum.js
```

#### CSS Files (create `css/` folder):
Copy all these files from `tri_ai_compare/static/` to `KorumOS/css/`:
- `korum.css`
- `korum_suggestions.css`
- `korum_modal.css`
- `korum_gloss.css`
- `korum_green.css`
- `korum_input.css`
- `korum_lightning.css`
- `korum_nodes.css`
- `korum_shiny.css`
- `korum_workflow.css`

#### Optional Documentation (create `docs/` folder):
Copy from `tri_ai_compare/KORUM-OS/` to `KorumOS/docs/`:
- `CHANGELOG.md`
- Any other docs you want

## Backend Requirements

KorumOS currently depends on the TriAI backend. You have two options:

### Option 1: Keep Using TriAI Backend (Easiest)
- Run the TriAI Flask app: `python app.py`
- The frontend will call `/api/ask` and `/api/v2/reasoning_chain`

### Option 2: Create Minimal Standalone Backend (Future)
You'll need to create a lightweight Flask app that implements:
- `/api/ask` - For V1 Council Mode
- `/api/v2/reasoning_chain` - For V2 Functional Pipeline

I can help you create this minimal backend later if you want full independence from TriAI.

## Next Steps

1. **Copy the files** listed above
2. **Open `index.html`** in a browser to test the frontend
3. **Run the TriAI backend** (for now) to enable API calls
4. **Add to Git** (if desired): `git init` in the `KorumOS` folder

## PowerShell Commands to Copy Files

Run these from PowerShell to automate the copying:

```powershell
# Create directories
New-Item -ItemType Directory -Path "C:\Users\carlo\Projects\KorumOS\js" -Force
New-Item -ItemType Directory -Path "C:\Users\carlo\Projects\KorumOS\css" -Force
New-Item -ItemType Directory -Path "C:\Users\carlo\Projects\KorumOS\docs" -Force

# Copy JavaScript
Copy-Item "C:\Users\carlo\OneDrive\Documents\Obsidian_Franknet\FrankNet\FrankNet\tri_ai_compare\static\korum.js" "C:\Users\carlo\Projects\KorumOS\js\korum.js"

# Copy all CSS files
Copy-Item "C:\Users\carlo\OneDrive\Documents\Obsidian_Franknet\FrankNet\FrankNet\tri_ai_compare\static\korum*.css" "C:\Users\carlo\Projects\KorumOS\css\"

# Copy documentation
Copy-Item "C:\Users\carlo\OneDrive\Documents\Obsidian_Franknet\FrankNet\FrankNet\tri_ai_compare\KORUM-OS\*" "C:\Users\carlo\Projects\KorumOS\docs\" -Recurse
```

---

**Status**: Frontend structure complete. Manual file copying required due to workspace restrictions.
**Location**: `C:\Users\carlo\Projects\KorumOS\`
