import json
import hashlib

def canonical_json(data):
    """
    Returns a deterministic JSON string for hashing.
    - Strict alphabetical key ordering (recursive via sort_keys).
    - No indentation, no trailing whitespace.
    - Compact separators: comma, colon, no spaces (RFC 8785 / JCS style).
    - UTF-8 encoding.
    """
    if not isinstance(data, dict):
        raise ValueError("Data for canonicalization must be a dictionary.")

    return json.dumps(data, sort_keys=True, separators=(',', ':'))

def compute_payload_hash(payload):
    """
    Computes a SHA-256 hash over a canonical JSON payload.
    """
    # Work on a copy — never mutate the caller's dict
    data = dict(payload)
    if 'schema_version' not in data:
        data['schema_version'] = "1.0"

    canon = canonical_json(data)
    return hashlib.sha256(canon.encode('utf-8')).hexdigest()

if __name__ == "__main__":
    # Test cases to prove determinism
    data_1 = {"z": 1, "a": 2, "m": [3, 2, 1], "nested": {"y": "last", "x": "first"}}
    data_2 = {"a": 2, "m": [3, 2, 1], "nested": {"x": "first", "y": "last"}, "z": 1}
    
    hash_1 = compute_payload_hash(data_1)
    hash_2 = compute_payload_hash(data_2)
    
    print(f"Data 1 Hash: {hash_1}")
    print(f"Data 2 Hash: {hash_2}")
    
    if hash_1 == hash_2:
        print("✅ SUCCESS: Hashing is deterministic.")
    else:
        print("❌ FAILURE: Hashing is non-deterministic.")
