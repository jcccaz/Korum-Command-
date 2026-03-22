import json
from exporters import _extract_parts, _packet_backed_risks_mode, _filter_sections

# Load the dump
with open(r"c:\\Users\\carlo\\Downloads\\KORUM-OS_DUMP_20260321_142916.json", "r", encoding="utf-8") as f:
    dump = json.load(f)

print("Keys in dump:", dump.keys())
print("Has decision packet?", bool(dump.get("decision_packet")))

meta, sections, structured, interrogations, verifications = _extract_parts(dump)

pb_mode = _packet_backed_risks_mode(dump, sections)
print(f"packet_backed_risks_mode: {pb_mode}")
print(f"Has critical_challenges? {bool(sections.get('critical_challenges'))}")
print(f"Has risks? {bool(sections.get('risks'))}")

section_items_pre = [(k, v) for k,v in sections.items()]
filtered = _filter_sections(section_items_pre, dump, sections)

print("\nSections AFTER filter:")
for k, v in filtered:
    print(k)

