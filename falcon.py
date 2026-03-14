"""
KorumOS Falcon Protocol — Secure Preprocessing & Redaction Engine
=============================================================

Data minimization layer that strips sensitive entities from user queries
and uploaded document text BEFORE content reaches any external AI provider.

IMPORTANT: This module provides exposure reduction, NOT perfect anonymization.
Some meaning may still be inferable from surrounding context. Falcon Protocol
should be framed as data minimization and secure preprocessing — never as
guaranteed de-identification.

Architecture:
    Pass A — Pattern-based (regex): emails, phones, SSNs, IPs, account numbers
    Pass B — Entity-based (heuristic NER): person names, orgs, locations
    Pass C — Custom dictionary: org-specific protected terms (extensible hook)

Zero external dependencies. Pure Python stdlib.
"""

import re
import hashlib
import json
import os
from enum import Enum
from typing import Dict, List, Tuple, Optional, Set


# ---------------------------------------------------------------------------
# ORG-SPECIFIC CONFIGURATION (future-ready)
# ---------------------------------------------------------------------------
# Load from falcon_config.json if it exists, otherwise use empty defaults.
# Admins can create this file to inject org-specific protected terms
# without modifying code.
#
# Expected structure:
# {
#   "protected_terms": ["Project Aurora", "Operation Blackbird"],
#   "protected_hostnames": ["dc01.internal", "vault.corp.local"],
#   "protected_project_names": ["TITAN", "MERCURY"],
#   "protected_customer_names": ["Acme Defense", "NorthStar Federal"]
# }

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "falcon_config.json")
_ORG_CONFIG: Dict[str, List[str]] = {}

def _load_org_config() -> Dict[str, List[str]]:
    """Load org-specific config from falcon_config.json if available."""
    global _ORG_CONFIG
    if _ORG_CONFIG:
        return _ORG_CONFIG
    if os.path.exists(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, 'r') as f:
                _ORG_CONFIG = json.load(f)
            print(f"[FALCON] Loaded org config: {sum(len(v) for v in _ORG_CONFIG.values())} protected terms")
        except Exception as e:
            print(f"[FALCON] Config load error: {e}")
            _ORG_CONFIG = {}
    return _ORG_CONFIG

def _get_org_custom_terms() -> List[str]:
    """Aggregate all org-specific terms into a flat list for Pass C."""
    cfg = _load_org_config()
    terms = []
    for key in ("protected_terms", "protected_hostnames",
                "protected_project_names", "protected_customer_names"):
        terms.extend(cfg.get(key, []))
    return terms


# ---------------------------------------------------------------------------
# FALCON LEVELS
# ---------------------------------------------------------------------------

class FalconLevel(Enum):
    LIGHT = "LIGHT"         # Regex patterns only (structured identifiers)
    STANDARD = "STANDARD"   # Regex + heuristic NER (names, orgs, locations)
    BLACK = "BLACK"         # Maximum redaction + dates, CC numbers, hostnames
                            # BLACK preserves sentence structure and generic nouns
                            # to maintain AI reasoning capability


# ---------------------------------------------------------------------------
# PASS A: REGEX PATTERN REGISTRY
# ---------------------------------------------------------------------------

REGEX_PATTERNS: Dict[str, re.Pattern] = {
    "EMAIL":    re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b'),
    "PHONE":    re.compile(r'(?<!\d)(?:\+?1[\-.\s]?)?(?:\(?\d{3}\)?[\-.\s]?)?\d{3}[\-.\s]?\d{4}(?!\d)'),
    "SSN":      re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    "IP_ADDR":  re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
    "ACCT_NUM": re.compile(r'\b(?:account|acct|a/c|customer\s*#|case\s*#|ticket\s*#|contract\s*#|id\s*#)[\s#:\-]*\d{4,}\b', re.IGNORECASE),
    "CC_NUM":   re.compile(r'\b(?:\d{4}[\-\s]?){3}\d{4}\b'),
    "DATE":     re.compile(r'\b(?:\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4})\b'),
    "HOSTNAME": re.compile(r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+(?:internal|local|corp|intranet|lan|priv)\b', re.IGNORECASE),
    "PASSPORT": re.compile(r'\b[A-Z]{1,2}\d{6,8}\b'),
    "SWIFT":    re.compile(r'\b[A-Z]{6}[A-Z2-9][A-NP-Z0-9](?:[A-Z0-9]{3})?\b'),
}

# Which levels include which regex patterns
LEVEL_PATTERNS = {
    FalconLevel.LIGHT:    {"EMAIL", "PHONE", "SSN", "IP_ADDR", "ACCT_NUM"},
    FalconLevel.STANDARD: {"EMAIL", "PHONE", "SSN", "IP_ADDR", "ACCT_NUM", "CC_NUM", "PASSPORT"},
    FalconLevel.BLACK:    {"EMAIL", "PHONE", "SSN", "IP_ADDR", "ACCT_NUM", "CC_NUM", "DATE", "HOSTNAME", "PASSPORT", "SWIFT"},
}


# ---------------------------------------------------------------------------
# PASS B: HEURISTIC NER DATA (no ML dependencies)
# ---------------------------------------------------------------------------

# Common English words to EXCLUDE from person-name detection
# NOTE: Expand this set as false positives are discovered in production.
COMMON_WORDS: Set[str] = {
    "The", "This", "That", "These", "Those", "What", "When", "Where", "Which",
    "Who", "How", "And", "But", "For", "Not", "You", "All", "Can", "Had",
    "Her", "Was", "One", "Our", "Out", "Are", "Has", "His", "Its", "May",
    "New", "Now", "Old", "See", "Way", "Day", "Did", "Get", "Let", "Say",
    "She", "Too", "Use", "Will", "With", "Just", "Also", "Each", "Even",
    "From", "Good", "Have", "Here", "High", "Into", "Keep", "Last",
    "Long", "Make", "Many", "Most", "Much", "Must", "Name", "Next", "Only",
    "Over", "Such", "Take", "Than", "Them", "Then", "Very", "Well", "Back",
    "Been", "Both", "Come", "Could", "Down", "First", "Great", "Some", "Still",
    "Should", "Would", "After", "Again", "Being", "Below", "Between", "Every",
    "Under", "While", "About", "Above", "Before", "During", "Never", "Other",
    "Right", "Small", "Three", "Through", "Today", "Without", "According",
    "However", "Important", "Because", "Different", "Another", "Following",
    # Common tech/business/KORUM terms that appear capitalized
    "Council", "Research", "Analysis", "Report", "System", "Protocol",
    "Security", "Intelligence", "Strategy", "Operations", "Mission",
    "Falcon", "Mode", "Standard", "Light", "Black", "Phase", "Level",
    "Intake", "Strategic", "Counterintelligence", "Defense", "Standards",
    "Truth", "Score", "Verification", "Interrogation", "Synthesis",
    "Executive", "Summary", "Brief", "Document", "Section", "Table",
    "Red", "Team", "Live", "Data", "Query", "Prompt", "Thread",
    "Quantum", "Compliance", "Framework", "Architecture", "Infrastructure",
    # Month / day names
    "January", "February", "March", "April", "June", "July", "August",
    "September", "October", "November", "December",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
    # BLACK mode structural preservation: keep generic nouns readable
    "Risk", "Threat", "Impact", "Plan", "Action", "Review", "Audit",
    "Policy", "Network", "Server", "Client", "Database", "Service",
    "Endpoint", "Firewall", "Router", "Switch", "Gateway", "Proxy",
    "Cloud", "Hybrid", "Platform", "Application", "Software", "Hardware",
    "Project", "Program", "Portfolio", "Budget", "Cost", "Revenue",
    "Customer", "Vendor", "Partner", "Supplier", "Contract", "Agreement",
    "Incident", "Response", "Recovery", "Backup", "Failover", "Migration",
    "Encryption", "Authentication", "Authorization", "Certificate", "Token",
    "Federal", "Government", "Military", "Commercial", "Enterprise",
    "North", "South", "East", "West", "Central", "Regional", "National",
    "Department", "Division", "Branch", "Unit", "Office", "Center",
    "Director", "Manager", "Officer", "Administrator", "Analyst", "Engineer",
    "President", "Chief", "Senior", "Junior", "Lead", "Head", "Vice",
}

# Organization suffix patterns
# Matches 1-5 capitalized words followed by a corporate suffix.
# Uses word-boundary anchoring and limits to capitalized tokens only.
ORG_SUFFIXES = re.compile(
    r'\b((?:[A-Z][A-Za-z&]+\s+){0,4}(?:Inc|Corp|Corporation|LLC|Ltd|Co|Company|Group|Foundation|'
    r'Association|Partners|Holdings|Enterprises|Technologies|Solutions|Services|'
    r'International|Global|Systems|Consulting|Capital|Ventures|Labs|Networks|'
    r'Communications|Telecom|Industries|Healthcare|Financial|Bank|Insurance)\.?)\b'
)

# US state abbreviations for location detection
US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC",
}

# City, ST pattern
LOCATION_PATTERN = re.compile(
    r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*),\s*(' + '|'.join(US_STATES) + r')\b'
)

# Known country names (top ~50 by global relevance)
COUNTRIES = {
    "United States", "United Kingdom", "Canada", "Australia", "Germany", "France",
    "Japan", "China", "India", "Brazil", "Mexico", "Russia", "South Korea",
    "Italy", "Spain", "Netherlands", "Switzerland", "Sweden", "Norway", "Denmark",
    "Israel", "Saudi Arabia", "Singapore", "Taiwan", "Ireland", "Belgium",
    "Austria", "Poland", "Turkey", "Egypt", "South Africa", "Nigeria", "Argentina",
    "Colombia", "Chile", "Indonesia", "Philippines", "Thailand", "Vietnam",
    "Pakistan", "Iran", "Iraq", "Ukraine", "Finland", "New Zealand", "Portugal",
    "Czech Republic", "Romania", "Hungary",
}


# ---------------------------------------------------------------------------
# RESULT CLASS
# ---------------------------------------------------------------------------

class FalconResult:
    """Immutable result of a Falcon preprocessing pass."""

    def __init__(self, redacted_text: str, placeholder_map: Dict[str, str],
                 metadata: Dict):
        self.redacted_text = redacted_text
        self.placeholder_map = placeholder_map  # {placeholder: original} — NEVER SERIALIZE
        self.metadata = metadata

    def __repr__(self):
        return f"<FalconResult level={self.metadata.get('level')} redactions={self.metadata.get('total_redactions')}>"


# ---------------------------------------------------------------------------
# PLACEHOLDER GENERATION
# ---------------------------------------------------------------------------

def _stable_placeholder(category: str, original: str, salt: str,
                        _cache: dict = {}) -> str:
    """
    Generate a deterministic placeholder for a given original value.

    Same (category, original, salt) always produces the same placeholder
    within a single run. The per-request salt prevents cross-request correlation.

    Normalizes whitespace so "Acme Corp" and "Acme  Corp" map to the same
    placeholder. Uses a mutable default arg as a simple call-scoped cache —
    callers must clear _cache between requests by passing a fresh dict.
    """
    # Normalize: strip + collapse whitespace for stable hashing
    normalized = " ".join(original.split())
    key = f"{salt}:{category}:{normalized}"
    if key in _cache:
        return _cache[key]

    digest = hashlib.sha256(key.encode()).hexdigest()[:6].upper()
    placeholder = f"[{category}_{digest}]"
    _cache[key] = placeholder
    return placeholder


# ---------------------------------------------------------------------------
# PASS B: HEURISTIC ENTITY DETECTORS
# ---------------------------------------------------------------------------

def _detect_person_names(text: str) -> List[Tuple[int, int, str]]:
    """
    Heuristic person name detection.
    Finds sequences of 2-4 capitalized words that are NOT in the common
    words exclusion list. Requires a preceding lowercase letter, period,
    or sentence boundary to reduce false positives on section headers.

    NOTE: This is a heuristic. False positives will occur. Expand
    COMMON_WORDS as needed to reduce noise in your domain.
    """
    # Look for 2-4 capitalized words preceded by lowercase/punct
    pattern = re.compile(r'(?<=[a-z.?!,;:]\s)([A-Z][a-z]{1,20}(?:\s[A-Z][a-z]{1,20}){1,3})')
    matches = []
    for m in pattern.finditer(text):
        words = m.group().split()
        # Skip if ALL words are in common exclusion set
        if all(w in COMMON_WORDS for w in words):
            continue
        # Require at least one non-common word
        if any(w not in COMMON_WORDS for w in words):
            matches.append((m.start(), m.end(), m.group()))
    return matches


def _detect_org_names(text: str) -> List[Tuple[int, int, str]]:
    """Detect organization names by corporate suffix patterns."""
    matches = []
    for m in ORG_SUFFIXES.finditer(text):
        name = m.group().strip()
        if len(name) > 3:  # Skip very short matches
            matches.append((m.start(), m.end(), name))
    return matches


def _detect_locations(text: str) -> List[Tuple[int, int, str]]:
    """Detect locations: 'City, ST' patterns and known country names."""
    matches = []
    for m in LOCATION_PATTERN.finditer(text):
        matches.append((m.start(), m.end(), m.group()))
    for country in COUNTRIES:
        for m in re.finditer(re.escape(country), text):
            matches.append((m.start(), m.end(), m.group()))
    return matches


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------

def falcon_preprocess(text: str, level: str = "STANDARD",
                      custom_terms: Optional[List[str]] = None,
                      debug: bool = False) -> FalconResult:
    """
    Run the full Falcon redaction pipeline on input text.

    Args:
        text:         Raw query text (may include appended document content).
        level:        One of "LIGHT", "STANDARD", "BLACK".
        custom_terms: Optional list of additional terms to redact.
                      Hook for future org-specific dictionaries.

    Returns:
        FalconResult with redacted_text, placeholder_map, and metadata.

    Security:
        The placeholder_map in the returned FalconResult must NEVER be
        serialized to JSON responses, logs, or any external system.
        It exists only for potential authorized reconstruction.
    """
    import time
    start_time = time.time()
    try:
        falcon_level = FalconLevel[level.upper()]
    except KeyError:
        falcon_level = FalconLevel.STANDARD

    # Per-request salt: deterministic within this call, different across calls
    salt = hashlib.sha256(f"{id(text)}:{len(text)}:{hash(text)}".encode()).hexdigest()[:12]
    placeholder_cache: Dict[str, str] = {}  # fresh cache per request

    # Merge org-specific custom terms with any caller-provided terms
    all_custom_terms = list(custom_terms or [])
    org_terms = _get_org_custom_terms()
    if org_terms:
        all_custom_terms.extend(org_terms)
    custom_terms = all_custom_terms if all_custom_terms else None

    # Collect all detections as (start, end, original_text, category)
    detections: List[Tuple[int, int, str, str]] = []

    # -----------------------------------------------------------------------
    # PASS A: Regex patterns
    # -----------------------------------------------------------------------
    active_patterns = LEVEL_PATTERNS[falcon_level]
    for category, pattern in REGEX_PATTERNS.items():
        if category in active_patterns:
            for m in pattern.finditer(text):
                detections.append((m.start(), m.end(), m.group(), category))

    # -----------------------------------------------------------------------
    # PASS B: Heuristic NER (STANDARD and BLACK only)
    # -----------------------------------------------------------------------
    if falcon_level in (FalconLevel.STANDARD, FalconLevel.BLACK):
        for start, end, matched in _detect_person_names(text):
            detections.append((start, end, matched, "PERSON"))
        for start, end, matched in _detect_org_names(text):
            detections.append((start, end, matched, "ORG"))
        for start, end, matched in _detect_locations(text):
            detections.append((start, end, matched, "LOCATION"))

    # -----------------------------------------------------------------------
    # PASS C: Custom dictionary (all levels)
    # Automatically include terms from falcon_config.json if it exists.
    # -----------------------------------------------------------------------
    all_custom_terms = _get_org_custom_terms()
    if custom_terms:
        all_custom_terms.extend(custom_terms)
        
    if all_custom_terms:
        # Use set to unique and sort by length descending to match longest first
        unique_terms = sorted(list(set(all_custom_terms)), key=len, reverse=True)
        for term in unique_terms:
            if len(term) < 2:
                continue
            escaped = re.escape(term)
            for m in re.finditer(escaped, text, re.IGNORECASE):
                detections.append((m.start(), m.end(), m.group(), "CUSTOM"))

    # -----------------------------------------------------------------------
    # DEDUPLICATION: Resolve overlapping spans (longer match wins)
    # Priority: ORG > CUSTOM > LOCATION > PERSON (ORG suffix match is more
    # specific than heuristic PERSON, so it wins ties of equal length)
    # -----------------------------------------------------------------------
    _CAT_PRIORITY = {"ORG": 0, "CUSTOM": 1, "LOCATION": 2, "PERSON": 3}
    detections.sort(key=lambda d: (-len(d[2]), _CAT_PRIORITY.get(d[3], 5), d[0]))
    used_ranges: List[Tuple[int, int]] = []
    filtered: List[Tuple[int, int, str, str]] = []

    for start, end, original, category in detections:
        # Check for overlap with any already-accepted span
        overlaps = any(start < ue and end > us for us, ue in used_ranges)
        if not overlaps:
            filtered.append((start, end, original, category))
            used_ranges.append((start, end))

    # Sort by position descending for safe in-place replacement
    filtered.sort(key=lambda d: d[0], reverse=True)

    # -----------------------------------------------------------------------
    # REPLACEMENT
    # -----------------------------------------------------------------------
    placeholder_map: Dict[str, str] = {}
    counts: Dict[str, int] = {}
    redacted = text

    for start, end, original, category in filtered:
        placeholder = _stable_placeholder(category, original, salt, placeholder_cache)
        placeholder_map[placeholder] = original
        counts[category] = counts.get(category, 0) + 1
        redacted = redacted[:start] + placeholder + redacted[end:]

    # -----------------------------------------------------------------------
    # METADATA (safe to serialize — contains NO original values)
    # -----------------------------------------------------------------------
    high_risk_categories = {"SSN", "CC_NUM", "ACCT_NUM"}
    high_risk_count = sum(counts.get(c, 0) for c in high_risk_categories)

    execution_time_ms = (time.time() - start_time) * 1000
    
    metadata = {
        "level": falcon_level.value,
        "total_redactions": len(filtered),
        "counts_by_category": counts,
        "high_risk_items_count": high_risk_count,
        "categories_found": list(counts.keys()),
        "custom_terms_loaded": len(all_custom_terms) if all_custom_terms else 0,
        "execution_time_ms": round(execution_time_ms, 2),
        "exposure_risk": _assess_exposure_risk(len(filtered), high_risk_count),
    }

    if debug:
        print(f"[FALCON DEBUG] Level: {level} | Redacted: {len(filtered)} | Risk: {metadata['exposure_risk']} | Latency: {metadata['execution_time_ms']}ms")

    return FalconResult(redacted, placeholder_map, metadata)


def falcon_rehydrate(text: str, placeholder_map: Dict[str, str]) -> str:
    """
    Restore original values to a redacted text using the placeholder_map.
    This should ONLY be called on the server for authorized user display
    just before sending to the client.

    NOTE: The placeholder_map MUST be the one generated during the corresponding
    falcon_preprocess call.
    """
    if not text or not placeholder_map:
        return text

    # Sort placeholders by length descending to prevent partial replacement
    # (though stable hashes should make collisions rare)
    sorted_phs = sorted(placeholder_map.keys(), key=len, reverse=True)
    
    rehydrated = text
    for ph in sorted_phs:
        original = placeholder_map[ph]
        # Use simple replace (placeholders are unique enough)
        rehydrated = rehydrated.replace(ph, original)
    
    return rehydrated


def _assess_exposure_risk(total_redactions: int, high_risk_count: int) -> str:
    """
    Simple heuristic risk assessment based on what was found.
    NOTE: This is an approximate indicator, not a security guarantee.
    """
    if high_risk_count >= 5:
        return "critical"
    elif high_risk_count >= 2:
        return "high"
    elif total_redactions >= 10:
        return "medium"
    elif total_redactions > 0:
        return "low"
    return "none"


# ---------------------------------------------------------------------------
# DEBUG MODE: Safe diagnostic output (never exposes raw text or map values)
# ---------------------------------------------------------------------------

def falcon_debug_report(result: FalconResult) -> str:
    """
    Developer-safe debug summary. Reports ONLY:
    - total entities redacted
    - categories found with counts
    - exposure risk level
    - placeholder count (not values)

    NEVER outputs raw text or placeholder map values.
    Safe to print to console or include in non-sensitive logs.
    """
    m = result.metadata
    lines = [
        f"[FALCON DEBUG] Level: {m['level']}",
        f"[FALCON DEBUG] Total Redactions: {m['total_redactions']}",
        f"[FALCON DEBUG] High-Risk Items: {m['high_risk_items_count']}",
        f"[FALCON DEBUG] Exposure Risk: {m['exposure_risk']}",
        f"[FALCON DEBUG] Categories: {m['counts_by_category']}",
        f"[FALCON DEBUG] Placeholder Map Size: {len(result.placeholder_map)} entries",
        f"[FALCON DEBUG] Custom Terms Loaded: {m['custom_terms_loaded']}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# INTERNAL TEST SUITE
# ---------------------------------------------------------------------------

def _run_self_tests() -> bool:
    """
    Internal test suite for Falcon Protocol. Run with:
        python falcon.py

    Tests placeholder stability, overlap resolution, category isolation,
    and sample inputs across telecom, legal, personal, and security domains.

    Returns True if all tests pass.
    """
    passed = 0
    failed = 0

    def _assert(condition, name):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS: {name}")
        else:
            failed += 1
            print(f"  FAIL: {name}")

    # ------------------------------------------------------------------
    # TEST 1: Placeholder stability — same entity, same placeholder
    # ------------------------------------------------------------------
    print("\n--- Test 1: Placeholder Stability ---")
    text = "Contact John Smith at john@example.com. John Smith is the lead. Email john@example.com again."
    result = falcon_preprocess(text, level="STANDARD")

    # Count unique placeholders for "john@example.com" — should be exactly 1
    email_placeholders = [p for p in result.placeholder_map if p.startswith("[EMAIL_")]
    _assert(len(email_placeholders) == 1,
            "Same email maps to one placeholder")

    # Verify both occurrences got replaced with the SAME placeholder
    email_ph = email_placeholders[0] if email_placeholders else ""
    _assert(result.redacted_text.count(email_ph) == 2,
            f"Email placeholder appears exactly 2 times")

    # ------------------------------------------------------------------
    # TEST 2: Overlap resolution — longer match wins
    # ------------------------------------------------------------------
    print("\n--- Test 2: Overlap Resolution ---")
    text = "the report from Acme Technologies Inc was reviewed."
    result = falcon_preprocess(text, level="STANDARD")
    # "Acme Technologies Inc" should be one ORG, not broken into parts
    org_placeholders = [p for p in result.placeholder_map if p.startswith("[ORG_")]
    _assert(len(org_placeholders) >= 1,
            "Org detected as a single entity")
    # Should NOT also detect "Acme" separately as a person
    person_in_org = any(
        result.placeholder_map[p] in ("Acme", "Acme Technologies")
        for p in result.placeholder_map if p.startswith("[PERSON_")
    )
    _assert(not person_in_org,
            "Longer ORG match prevents partial PERSON match")

    # ------------------------------------------------------------------
    # TEST 3: Category isolation — different categories don't collide
    # ------------------------------------------------------------------
    print("\n--- Test 3: Category Isolation ---")
    text = "the analyst Jane Doe emailed jane.doe@corp.com from 10.0.0.1 about case# 12345."
    result = falcon_preprocess(text, level="STANDARD")
    categories = set(p.split("_")[0].strip("[") for p in result.placeholder_map)
    _assert("EMAIL" in categories, "EMAIL category detected")
    _assert("IP" in categories or "IP_ADDR" in str(result.placeholder_map),
            "IP category detected")
    _assert("ACCT" in categories or "ACCT_NUM" in str(result.placeholder_map),
            "ACCT_NUM category detected")
    # Verify no two different-category entities share a placeholder
    all_phs = list(result.placeholder_map.keys())
    _assert(len(all_phs) == len(set(all_phs)),
            "No placeholder collision across categories")

    # ------------------------------------------------------------------
    # TEST 4: Level differentiation
    # ------------------------------------------------------------------
    print("\n--- Test 4: Level Differentiation ---")
    text = "on 03/15/2026 the analyst called 555-123-4567 from 192.168.1.1"
    r_light = falcon_preprocess(text, level="LIGHT")
    r_standard = falcon_preprocess(text, level="STANDARD")
    r_black = falcon_preprocess(text, level="BLACK")

    _assert(r_light.metadata['total_redactions'] <= r_standard.metadata['total_redactions'],
            "STANDARD redacts >= LIGHT")
    _assert(r_standard.metadata['total_redactions'] <= r_black.metadata['total_redactions'],
            "BLACK redacts >= STANDARD")
    # BLACK should catch the date, LIGHT should not
    _assert("DATE" not in r_light.metadata['counts_by_category'],
            "LIGHT does not redact dates")
    _assert("DATE" in r_black.metadata['counts_by_category'],
            "BLACK redacts dates")

    # ------------------------------------------------------------------
    # TEST 5: Sample — Telecom / infrastructure text
    # ------------------------------------------------------------------
    print("\n--- Test 5: Telecom / Infrastructure ---")
    text = (
        "the outage at Baltimore POP affected Verizon Communications customers. "
        "Contact Sarah Martinez at sarah.martinez@verizon.com or 443-555-0199. "
        "The core router at dc01.internal.corp lost connectivity to 10.42.88.1. "
        "Ticket# 8829341 was opened for account# 770023891."
    )
    result = falcon_preprocess(text, level="STANDARD")
    _assert(result.metadata['total_redactions'] >= 5,
            f"Telecom text: {result.metadata['total_redactions']} redactions (expected >= 5)")
    _assert("EMAIL" in result.metadata['categories_found'],
            "Telecom: EMAIL detected")
    _assert("PHONE" in result.metadata['categories_found'],
            "Telecom: PHONE detected")
    _assert("IP_ADDR" in result.metadata['categories_found'],
            "Telecom: IP detected")

    # ------------------------------------------------------------------
    # TEST 6: Sample — Legal / business text
    # ------------------------------------------------------------------
    print("\n--- Test 6: Legal / Business ---")
    text = (
        "the agreement between NorthStar Holdings LLC and Meridian Capital Partners "
        "was signed by James Thornton on behalf of NorthStar Holdings LLC. "
        "Contact legal@northstar.com for contract# 9928-A."
    )
    result = falcon_preprocess(text, level="STANDARD")
    _assert("ORG" in result.metadata['categories_found'],
            "Legal: ORG detected")
    _assert("EMAIL" in result.metadata['categories_found'],
            "Legal: EMAIL detected")
    # Check that the same org gets same placeholder both times
    org_phs = [p for p in result.placeholder_map if p.startswith("[ORG_")]
    if org_phs:
        first_org_ph = org_phs[0]
        _assert(result.redacted_text.count(first_org_ph) >= 2,
                "Same ORG entity gets same placeholder across occurrences")

    # ------------------------------------------------------------------
    # TEST 7: Sample — Personal text
    # ------------------------------------------------------------------
    print("\n--- Test 7: Personal Text ---")
    text = (
        "please forward to Michael Chen at michael.chen@gmail.com. "
        "He lives in Austin, TX and his SSN is 412-55-7890. "
        "His phone is (512) 555-0142."
    )
    result = falcon_preprocess(text, level="STANDARD")
    _assert("SSN" in result.metadata['categories_found'],
            "Personal: SSN detected")
    _assert("LOCATION" in result.metadata['categories_found'],
            "Personal: LOCATION detected")
    _assert(result.metadata['high_risk_items_count'] >= 1,
            "Personal: high-risk items flagged")
    _assert(result.metadata['exposure_risk'] in ("high", "critical", "medium", "low"),
            f"Personal: exposure_risk={result.metadata['exposure_risk']}")

    # ------------------------------------------------------------------
    # TEST 8: Sample — Security incident text
    # ------------------------------------------------------------------
    print("\n--- Test 8: Security Incident ---")
    text = (
        "the threat actor exfiltrated data from 192.168.50.12 targeting "
        "Emily Rodriguez's credentials. The C2 server at 45.33.12.88 "
        "was linked to account# 44291003. The incident was reported to "
        "the FBI and CISA by Raytheon Technologies."
    )
    result = falcon_preprocess(text, level="BLACK")
    _assert(result.metadata['total_redactions'] >= 4,
            f"Security: {result.metadata['total_redactions']} redactions (expected >= 4)")
    _assert("IP_ADDR" in result.metadata['categories_found'],
            "Security: IP addresses detected")

    # ------------------------------------------------------------------
    # TEST 9: BLACK mode structural readability
    # ------------------------------------------------------------------
    print("\n--- Test 9: BLACK Mode Readability ---")
    text = (
        "the risk assessment shows that the network firewall at 10.0.0.1 "
        "needs an upgrade. Contact the IT department for more information."
    )
    result = falcon_preprocess(text, level="BLACK")
    # Generic nouns like "risk", "network", "firewall", "department" should NOT be redacted
    for word in ["risk", "network", "firewall", "department", "upgrade", "information"]:
        _assert(word in result.redacted_text.lower(),
                f"BLACK preserves structural word: '{word}'")

    # ------------------------------------------------------------------
    # TEST 10: Custom terms
    # ------------------------------------------------------------------
    print("\n--- Test 10: Custom Terms ---")
    text = "the Project Aurora deployment in the TITAN environment was approved."
    result = falcon_preprocess(text, level="LIGHT",
                               custom_terms=["Project Aurora", "TITAN"])
    _assert("CUSTOM" in result.metadata['categories_found'],
            "Custom terms detected")
    _assert(result.metadata['total_redactions'] >= 2,
            f"Custom: {result.metadata['total_redactions']} redactions (expected >= 2)")
    _assert("Project Aurora" not in result.redacted_text,
            "Custom term 'Project Aurora' was redacted")
    _assert("TITAN" not in result.redacted_text,
            "Custom term 'TITAN' was redacted")

    # ------------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------------
    total = passed + failed
    print(f"\n{'='*50}")
    print(f"Falcon Protocol Self-Test: {passed}/{total} passed, {failed} failed")
    print(f"{'='*50}")
    return failed == 0


if __name__ == "__main__":
    _run_self_tests()
