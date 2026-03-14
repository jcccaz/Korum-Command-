from falcon import falcon_preprocess, falcon_rehydrate

test_text = """
Hello, my name is John Doe and I work at Acme Corp. 
You can reach me at john.doe@acme.com or 555-0199.
Our project 'Operation Aurora' is located in Seattle, WA.
My account number is ACCT-12345678.
"""

print("--- RAW TEXT ---")
print(test_text)

print("\n--- STANDARD REDACTION ---")
res_std = falcon_preprocess(test_text, level="STANDARD")
redacted = res_std.redacted_text
print(redacted)
print(res_std.metadata)

print("\n--- SERVER-SIDE RE-HYDRATION TEST ---")
rehydrated = falcon_rehydrate(redacted, res_std.placeholder_map)
print(rehydrated)

if rehydrated.strip() == test_text.strip():
    print("SUCCESS: Rehydration restored original text perfectly.")
else:
    print("FAILURE: Rehydration mismatch.")
    # Show differences if any
    import difflib
    diff = list(difflib.ndiff(test_text.splitlines(), rehydrated.splitlines()))
    print("\n".join(diff))

print("\n--- BLACK REDACTION + REHYDRATION ---")
res_black = falcon_preprocess(test_text, level="BLACK")
rehydrated_black = falcon_rehydrate(res_black.redacted_text, res_black.placeholder_map)
if rehydrated_black.strip() == test_text.strip():
    print("SUCCESS: BLACK mode rehydration OK.")

print("\n--- CUSTOM TERMS REDACTION (Project Aurora) ---")
res_custom = falcon_preprocess("Let's talk about Project Aurora at Qanapi.", level="LIGHT")
print(res_custom.redacted_text)
rehydrated_custom = falcon_rehydrate(res_custom.redacted_text, res_custom.placeholder_map)
print(f"Rehydrated: {rehydrated_custom}")
