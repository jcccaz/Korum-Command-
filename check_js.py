
import sys

with open(r'c:\Users\carlo\Projects\KorumOS\js\korum.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if 'resetSessionBtn' in line:
        print(f"{i+1}: {repr(line)}")
