
import sys

file_path = r'c:\Users\carlo\Projects\KorumOS\js\korum.js'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Clear ResearchDock in resetSessionBtn
old_text_1 = """        lastQueryText = '';
        initializeMissionSurface();"""
new_text_1 = """        lastQueryText = '';
        if (typeof ResearchDock !== 'undefined' && ResearchDock.clear) ResearchDock.clear();
        initializeMissionSurface();"""

# 2. Clear ResearchDock in triggerCouncil
old_text_2 = """    // Store original query for display
    sessionState.originalQuery = query;"""
new_text_2 = """    // Store original query for display
    sessionState.originalQuery = query;

    // Clear previous Artifact Dock state
    if (typeof ResearchDock !== 'undefined' && ResearchDock.clear) {
        ResearchDock.clear();
    }"""

if old_text_1 in content and old_text_2 in content:
    content = content.replace(old_text_1, new_text_1)
    content = content.replace(old_text_2, new_text_2)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Successfully patched js/korum.js")
else:
    if old_text_1 not in content:
        print("Failed: old_text_1 not found")
    if old_text_2 not in content:
        print("Failed: old_text_2 not found")
