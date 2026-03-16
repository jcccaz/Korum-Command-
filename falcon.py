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
    # Partial SSN: masked forms like XXX-44-9021 or ***-44-9021
    "SSN_PARTIAL": re.compile(
        r'\b(?:[Xx*]{3}|\d{3})[\-\s](?:[Xx*]{2}|\d{2})[\-\s]\d{4}\b'
        r'|\b\d{3}[\-\s](?:[Xx*]{2}|\d{2})[\-\s](?:[Xx*]{4}|\d{4})\b'
    ),
    "IP_ADDR":  re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
    "ACCT_NUM": re.compile(r'\b(?:account|acct|a/c|customer\s*#|case\s*#|ticket\s*#|contract\s*#|id\s*#|officer|office|facility|site|bldg|building|room|suite|unit|badge|agent|operative|asset)[\s#:\-]*\d{3,}\b', re.IGNORECASE),
    "CC_NUM":   re.compile(r'\b(?:\d{4}[\-\s]?){3}\d{4}\b'),
    "DATE":     re.compile(r'\b(?:\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4})\b'),
    "DATE_WRITTEN": re.compile(
        r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)'
        r'\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{2,4}\b', re.IGNORECASE
    ),
    "STREET_ADDR": re.compile(
        r'\b\d{1,6}\s+[A-Za-z][A-Za-z0-9\-]+(?:\s+[A-Za-z][A-Za-z0-9\-]+){0,3}'
        r'\s+(?:St|Street|Ave|Avenue|Blvd|Boulevard|Dr|Drive|Rd|Road|Ln|Lane|Way|Ct|Court'
        r'|Pl|Place|Pkwy|Parkway|Cir|Circle|Hwy|Highway|Ter|Terrace|Loop|Run|Path|Trail)\.?\b',
        re.IGNORECASE
    ),
    "HOSTNAME": re.compile(r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+(?:internal|local|corp|intranet|lan|priv)\b', re.IGNORECASE),
    "PASSPORT": re.compile(r'\b[A-Z]{1,2}\d{6,8}\b'),
    "SWIFT":    re.compile(r'\b[A-Z]{6}[A-Z2-9][A-NP-Z0-9](?:[A-Z0-9]{3})?\b'),
    "ALNUM_TAG": re.compile(
        r'\b(?:'
        r'(?:[A-Z][a-z]{2,}(?:-[A-Z][a-z]{2,})?)\s+(?:\d{1,6}[A-Za-z]{1,3}|\d{2,6}|\d{1,3}-[A-Za-z0-9]{1,4})'
        r'|'
        r'(?:\d{1,6}[A-Za-z]{1,3}|\d{2,6}|\d{1,3}-[A-Za-z0-9]{1,4})\s+(?:[A-Z][a-z]{2,}(?:-[A-Z][a-z]{2,})?)'
        r')\b'
    ),
    # Dollar / currency amounts: $1,200.00 / USD 4,500 / €2.5M / £300K
    "CURRENCY_AMOUNT": re.compile(
        r'(?:'
        r'[$€£¥₹₩₽]\s*\d{1,3}(?:[,.]\d{3})*(?:\.\d{1,2})?(?:\s*[MmBbKk])?'
        r'|\b(?:USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY|INR)\s+\d{1,3}(?:[,.]\d{3})*(?:\.\d{1,2})?(?:\s*[MmBbKk])?'
        r'|\d{1,3}(?:[,.]\d{3})*(?:\.\d{1,2})?\s*(?:dollars?|euros?|pounds?|yen)'
        r')\b',
        re.IGNORECASE
    ),
    # IBAN: up to 34 alphanumeric chars starting with 2-letter country code
    "IBAN": re.compile(
        r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]?){0,16}\b'
    ),
    # Titled / prefixed full names: Dr. Klaus von Braun, J. Vance, Mr. Smith
    # Catches: Title + Name, Initial.Lastname, multi-part names with particles
    "TITLED_NAME": re.compile(
        r'\b(?:Dr|Mr|Mrs|Ms|Prof|Gen|Col|Capt|Lt|Sgt|Cpl|Adm|Gov|Sen|Rep|Amb|Atty|Rev|Fr|Sr|Br|Mx)\.?\s+'
        r'[A-Z][a-z]{1,20}'
        r'(?:\s+(?:van|von|de|del|della|di|da|le|la|du|des|den|af|av|of|bin|binti|al|el|ibn)?)?'
        r'(?:\s+[A-Z][a-z]{1,20}){0,3}\b',
        re.IGNORECASE
    ),
    # Bare initial + lastname: J. Vance  /  R.J. Thornton  /  J.K. Simmons
    "INITIAL_NAME": re.compile(
        r'\b[A-Z]\.(?:[A-Z]\.)?\s+[A-Z][a-z]{2,20}\b'
    ),
}

# Which levels include which regex patterns
LEVEL_PATTERNS = {
    FalconLevel.LIGHT:    {"EMAIL", "PHONE", "SSN", "SSN_PARTIAL", "IP_ADDR", "ACCT_NUM",
                           "CURRENCY_AMOUNT", "IBAN", "TITLED_NAME", "INITIAL_NAME"},
    FalconLevel.STANDARD: {"EMAIL", "PHONE", "SSN", "SSN_PARTIAL", "IP_ADDR", "ACCT_NUM",
                           "CC_NUM", "PASSPORT", "STREET_ADDR", "DATE", "DATE_WRITTEN",
                           "ALNUM_TAG", "CURRENCY_AMOUNT", "IBAN", "TITLED_NAME", "INITIAL_NAME"},
    FalconLevel.BLACK:    {"EMAIL", "PHONE", "SSN", "SSN_PARTIAL", "IP_ADDR", "ACCT_NUM",
                           "CC_NUM", "DATE", "DATE_WRITTEN", "STREET_ADDR", "HOSTNAME",
                           "PASSPORT", "SWIFT", "ALNUM_TAG", "CURRENCY_AMOUNT", "IBAN",
                           "TITLED_NAME", "INITIAL_NAME"},
}


# ---------------------------------------------------------------------------
# PASS B: HEURISTIC NER DATA (no ML dependencies)
# ---------------------------------------------------------------------------

# Common English words to EXCLUDE from person-name detection
# ── SOURCE: Loaded dynamically at import time from:
#    1. Hardcoded English stopwords (no external dependencies)
#    2. falcon_dictionary.json "general" section (Korum-OS specific terms)
#    3. Active workflow domain section (legal/medical/finance/defense/etc.)
# ── Add domain terms to falcon_dictionary.json, not here.

_DICTIONARY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "falcon_dictionary.json")
_LOADED_DICTIONARY: Dict[str, List[str]] = {}

def _load_dictionary() -> Dict[str, List[str]]:
    """Load falcon_dictionary.json. Cached after first load."""
    global _LOADED_DICTIONARY
    if _LOADED_DICTIONARY:
        return _LOADED_DICTIONARY
    if os.path.exists(_DICTIONARY_PATH):
        try:
            with open(_DICTIONARY_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            _LOADED_DICTIONARY = {k: v for k, v in data.items() if k != '_meta'}
            print(f"[FALCON] Loaded dictionary: {sum(len(v) for v in _LOADED_DICTIONARY.values())} domain stopwords")
        except Exception as e:
            print(f"[FALCON] Dictionary load error: {e}")
            _LOADED_DICTIONARY = {}
    return _LOADED_DICTIONARY


_ENGLISH_STOPWORDS = {
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
    "Please", "Note", "Meeting", "Hello", "Dear", "Regards", "Contact",
    "January", "February", "March", "April", "June", "July", "August",
    "September", "October", "November", "December",
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
}

def _build_common_words(workflow: Optional[str] = None) -> Set[str]:
    """
    Build the COMMON_WORDS exclusion set for a given workflow domain.
    Sources (merged):
      1. Hardcoded English stopwords (title-cased, no dependencies)
      2. falcon_dictionary.json "general" section — always included
      3. falcon_dictionary.json domain section — loaded based on workflow
    """
    words: Set[str] = set(_ENGLISH_STOPWORDS)

    # Source 2+3: falcon_dictionary.json
    dictionary = _load_dictionary()
    for section in ('general',):
        words.update(dictionary.get(section, []))

    # Workflow-to-domain mapping
    WORKFLOW_DOMAIN_MAP = {
        'LEGAL':            'legal',
        'MEDICAL':          'medical',
        'FINANCE':          'finance',
        'WAR_ROOM':         'defense',
        'DEFENSE':          'defense',
        'QUANTUM_SECURITY': 'defense',
        'RESEARCH':         'research',
        'SCIENCE':          'research',
        'STARTUP':          'business',
        'CREATIVE':         'business',
        'MARKETING':        'business',
        'INTEL':            'defense',
        'CYBER':            'defense',
    }
    if workflow:
        domain = WORKFLOW_DOMAIN_MAP.get(workflow.upper())
        if domain and domain in dictionary:
            words.update(dictionary[domain])
            print(f"[FALCON] Loaded domain stopwords: {domain} ({len(dictionary[domain])} words)")

    return words


# Module-level COMMON_WORDS — loaded once at import with no workflow context.
# Pass workflow= to falcon_preprocess to get domain-aware filtering.
def _init_common_words() -> Set[str]:
    """Initialize module-level common words set at import time."""
    return _build_common_words(workflow=None)

COMMON_WORDS: Set[str] = _init_common_words()


# Organization suffix patterns
# Matches 1-5 capitalized words followed by a corporate suffix.
# Uses word-boundary anchoring and limits to capitalized tokens only.
ORG_SUFFIXES = re.compile(
    r'\b((?:[A-Z][A-Za-z&\-]+\s+){0,4}(?:Inc|Corp|Corporation|LLC|Ltd|Co|Company|Group|Foundation|'
    r'Association|Partners|Holdings|Enterprises|Technologies|Solutions|Services|'
    r'International|Global|Systems|Consulting|Capital|Ventures|Labs|Networks|'
    r'Communications|Telecom|Industries|Healthcare|Financial|Bank|Insurance|'
    r'Biotech|Biotechnologies|Biosciences|Biotics|Biologics|Pharma|Pharmaceuticals|'
    r'Therapeutics|Genomics|Diagnostics|Medical|Sciences|Research|Analytics|'
    r'Dynamics|Aerospace|Defense|Defence|Security|Energy|Logistics|Media|'
    r'Digital|Software|Studio|Studios|Agency|Institute|University|Trust|Fund|'
    r'Infrastructure|Engineering|Architects|Architecture|Laboratories|Laboratory|'
    r'Clinic|Hospital|Academy|Alliance|Authority|Bureau|Commission|Council|'
    r'Federation|Ministry|Network|Platform|Protocol|Reservoir|Exchange)\.?)\b'
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

# Country names — curated set covering all countries likely to appear in contracts.
# No external dependencies. Add to this set as needed.
COUNTRIES: Set[str] = {
    # North America
    "United States", "Canada", "Mexico",
    # Europe
    "United Kingdom", "Germany", "France", "Italy", "Spain", "Netherlands",
    "Switzerland", "Sweden", "Norway", "Denmark", "Finland", "Ireland",
    "Belgium", "Austria", "Poland", "Portugal", "Greece", "Czech Republic",
    "Romania", "Hungary", "Croatia", "Slovakia", "Slovenia", "Bulgaria",
    "Lithuania", "Latvia", "Estonia", "Luxembourg", "Malta", "Cyprus",
    "Iceland", "Serbia", "Bosnia", "Montenegro", "Albania", "Moldova",
    "North Macedonia", "Ukraine", "Belarus",
    # Asia & Pacific
    "Japan", "China", "India", "South Korea", "Taiwan", "Singapore",
    "Hong Kong", "Thailand", "Vietnam", "Indonesia", "Philippines",
    "Malaysia", "Pakistan", "Bangladesh", "Sri Lanka", "Myanmar",
    "Cambodia", "Laos", "Mongolia", "Nepal", "Australia", "New Zealand",
    # Middle East & Africa
    "Israel", "Saudi Arabia", "United Arab Emirates", "Qatar", "Kuwait",
    "Bahrain", "Oman", "Jordan", "Lebanon", "Iraq", "Iran", "Turkey",
    "Egypt", "South Africa", "Nigeria", "Kenya", "Ethiopia", "Ghana",
    "Tanzania", "Morocco", "Tunisia", "Algeria", "Libya",
    # Americas
    "Brazil", "Argentina", "Colombia", "Chile", "Peru", "Venezuela",
    "Ecuador", "Bolivia", "Paraguay", "Uruguay", "Costa Rica", "Panama",
    "Guatemala", "Honduras", "El Salvador", "Nicaragua", "Cuba",
    "Dominican Republic", "Puerto Rico", "Jamaica", "Trinidad",
    # Russia & Central Asia
    "Russia", "Kazakhstan", "Uzbekistan", "Georgia", "Armenia", "Azerbaijan",
}

# Major world cities — curated set of ~200 cities commonly found in contracts,
# legal docs, and business correspondence. No external dependencies.
MAJOR_CITIES: Set[str] = {
    # US major cities
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia",
    "San Antonio", "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville",
    "San Francisco", "Seattle", "Denver", "Boston", "Atlanta", "Miami",
    "Minneapolis", "Tampa", "Orlando", "St. Louis", "Pittsburgh", "Cincinnati",
    "Cleveland", "Nashville", "Charlotte", "Indianapolis", "Columbus",
    "Milwaukee", "Kansas City", "Las Vegas", "Portland", "Sacramento",
    "Salt Lake City", "Raleigh", "Richmond", "Hartford", "Buffalo",
    "Honolulu", "Anchorage", "Detroit", "Baltimore", "Washington",
    # Canada
    "Toronto", "Montreal", "Vancouver", "Ottawa", "Calgary", "Edmonton",
    # Europe
    "London", "Paris", "Berlin", "Munich", "Frankfurt", "Hamburg",
    "Madrid", "Barcelona", "Rome", "Milan", "Amsterdam", "Rotterdam",
    "Brussels", "Vienna", "Zurich", "Geneva", "Basel", "Bern",
    "Stockholm", "Oslo", "Copenhagen", "Helsinki", "Dublin", "Edinburgh",
    "Lisbon", "Prague", "Warsaw", "Budapest", "Bucharest", "Athens",
    "Belgrade", "Zagreb", "Bratislava", "Ljubljana", "Tallinn", "Riga",
    "Vilnius", "Luxembourg", "Monaco", "Reykjavik", "Kyiv",
    # Asia & Pacific
    "Tokyo", "Osaka", "Beijing", "Shanghai", "Shenzhen", "Guangzhou",
    "Hong Kong", "Seoul", "Busan", "Taipei", "Singapore", "Bangkok",
    "Jakarta", "Kuala Lumpur", "Manila", "Hanoi", "Ho Chi Minh City",
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata",
    "Sydney", "Melbourne", "Brisbane", "Perth", "Auckland", "Wellington",
    # Middle East & Africa
    "Dubai", "Abu Dhabi", "Doha", "Riyadh", "Jeddah", "Kuwait City",
    "Tel Aviv", "Jerusalem", "Amman", "Beirut", "Istanbul", "Ankara",
    "Cairo", "Casablanca", "Lagos", "Nairobi", "Johannesburg", "Cape Town",
    "Addis Ababa", "Accra", "Dar es Salaam",
    # Americas
    "Mexico City", "Guadalajara", "Monterrey", "Bogota", "Medellin",
    "Lima", "Santiago", "Buenos Aires", "Sao Paulo", "Rio de Janeiro",
    "Brasilia", "Panama City", "San Juan", "Havana", "Kingston",
    # Russia & Central Asia
    "Moscow", "St. Petersburg", "Almaty", "Tbilisi", "Baku", "Yerevan",
    # Contract-specific locations
    "Reston", "Arlington", "McLean", "Tysons", "Bethesda", "Langley",
}


# ---------------------------------------------------------------------------
# RESULT CLASS
# ---------------------------------------------------------------------------

class FalconResult:
    """Immutable result of a Falcon preprocessing pass."""

    def __init__(self, redacted_text: str, placeholder_map: Dict[str, str],
                 metadata: Dict, ghost_map: Optional[List[Dict]] = None):
        self.redacted_text = redacted_text
        self.placeholder_map = placeholder_map  # {placeholder: original} — NEVER SERIALIZE
        self.metadata = metadata
        # Ghost Map: safe-to-serialize token inventory (no original values)
        # [{token, entity_type, sequence, source_pass, char_offset}]
        self.ghost_map: List[Dict] = ghost_map or []

    def __repr__(self):
        return f"<FalconResult level={self.metadata.get('level')} redactions={self.metadata.get('total_redactions')} ghost_entries={len(self.ghost_map)}>"


# ---------------------------------------------------------------------------
# MISSION VAULT — Deterministic Pseudonymization (Phase 2)
# ---------------------------------------------------------------------------

class VaultManager:
    """DB-backed + in-memory cached vault for mission-scoped deterministic pseudonyms.
    Same entity across multiple requests in the same mission always gets the same
    pseudonym (e.g. PERSON_01). Raw PII is NEVER stored — only SHA-256 hashes."""

    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self._by_text = {}      # (category, normalized_upper) -> pseudonym
        self._by_hash = {}      # (category, entity_hash) -> pseudonym
        self._counters = {}     # category -> max_sequence_num
        self._dirty = []        # new entries to persist
        self._load_from_db()

    def _load_from_db(self):
        from models import MissionVault
        from db import db
        entries = MissionVault.query.filter_by(mission_id=self.mission_id).all()
        for e in entries:
            self._by_hash[(e.category, e.entity_hash)] = e.pseudonym
            current_max = self._counters.get(e.category, 0)
            self._counters[e.category] = max(current_max, e.sequence_num)

    def get_or_create(self, category: str, original: str) -> str:
        """Return a deterministic pseudonym like [PERSON_01] for the given entity."""
        normalized = " ".join(original.split()).upper()
        key_text = (category, normalized)

        # L2: in-memory cache hit (same request, same entity)
        if key_text in self._by_text:
            return self._by_text[key_text]

        # L1: DB hash lookup (cross-request consistency)
        entity_hash = hashlib.sha256(normalized.encode()).hexdigest()
        key_hash = (category, entity_hash)
        if key_hash in self._by_hash:
            pseudonym = self._by_hash[key_hash]
            self._by_text[key_text] = pseudonym
            return pseudonym

        # New entity: assign next sequence number
        seq = self._counters.get(category, 0) + 1
        self._counters[category] = seq
        pseudonym = f"[{category}_{seq:02d}]"

        self._by_text[key_text] = pseudonym
        self._by_hash[key_hash] = pseudonym
        self._dirty.append((category, entity_hash, pseudonym, seq))
        return pseudonym

    def flush(self):
        """Persist new vault entries to DB. Call after council execution."""
        if not self._dirty:
            return
        from models import MissionVault
        from db import db
        for category, entity_hash, pseudonym, seq in self._dirty:
            entry = MissionVault(
                mission_id=self.mission_id,
                category=category,
                entity_hash=entity_hash,
                pseudonym=pseudonym,
                sequence_num=seq,
            )
            db.session.add(entry)
        try:
            db.session.commit()
            print(f"[VAULT] Persisted {len(self._dirty)} new pseudonyms for mission {self.mission_id[:8]}")
        except Exception as e:
            db.session.rollback()
            print(f"[VAULT] Flush error: {e}")
        self._dirty.clear()


# ---------------------------------------------------------------------------
# PLACEHOLDER GENERATION (Legacy hash-based — used for Ghost Preview / V1)
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
    underscore, or sentence boundary to reduce false positives on section headers.

    NOTE: This is a heuristic. False positives will occur. Expand
    COMMON_WORDS as needed to reduce noise in your domain.
    """
    name_pat = r'[A-Z][a-z]{1,20}(?:\s[A-Z][a-z]{1,20}){1,3}'
    patterns = [
        # Standard: preceded by lowercase/punct + space
        re.compile(r'(?<=[a-z.?!,;:_]\s)(' + name_pat + r')'),
        # Signature-line: preceded by underscore(s) directly (no space)
        re.compile(r'(?<=_)(' + name_pat + r')'),
    ]
    matches = []
    seen_spans = set()
    for pattern in patterns:
        for m in pattern.finditer(text):
            span = (m.start(), m.end())
            if span in seen_spans:
                continue
            seen_spans.add(span)
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
    """Detect locations: 'City, ST' patterns, 'City, Country' patterns, standalone cities, and country names."""
    matches = []
    # US-style: "Seattle, WA"
    for m in LOCATION_PATTERN.finditer(text):
        matches.append((m.start(), m.end(), m.group()))
    # International: "Reykjavik, Iceland" / "São Paulo, Brazil"
    for country in COUNTRIES:
        pattern = re.compile(
            r'\b([A-Z][a-zA-Zà-öø-ÿÀ-ÖØ-Ý]+(?:\s[A-Z][a-zA-Zà-öø-ÿÀ-ÖØ-Ý]+)*),\s*'
            + re.escape(country) + r'\b'
        )
        for m in pattern.finditer(text):
            matches.append((m.start(), m.end(), m.group()))
    # Standalone country names
    for country in COUNTRIES:
        for m in re.finditer(re.escape(country), text):
            matches.append((m.start(), m.end(), m.group()))
    # Standalone major cities (globally significant, identifiable without context)
    for city in MAJOR_CITIES:
        for m in re.finditer(r'\b' + re.escape(city) + r'\b', text):
            matches.append((m.start(), m.end(), m.group()))
    return matches


def _detect_proper_noun_phrases(text: str) -> List[Tuple[int, int, str]]:
    """
    Heuristic proper-noun detector for STANDARD/BLACK:
    Flags capitalized words (1-4 tokens) that are NOT at sentence start
    and NOT in the COMMON_WORDS stop-word list.

    Catches standalone proper nouns like "Reykjavik", "Vance", "Thorne"
    as well as multi-word forms like "Blue-Vein", "North Ridge".
    """
    # Custom boundary: treat underscores as separators (unlike \b which counts _ as word char)
    pattern = re.compile(
        r'(?:^|(?<=[^A-Za-z0-9]))([A-Z][a-z]{2,}(?:-[A-Z][a-z]{2,})?(?:\s+[A-Z][a-z]{2,}(?:-[A-Z][a-z]{2,})?){0,3})(?=[^A-Za-z]|$)'
    )
    matches = []
    for m in pattern.finditer(text):
        phrase = m.group(1)
        start, end = m.start(1), m.end(1)
        tokens = phrase.split()
        if not tokens:
            continue

        # Skip sentence-initial phrases — these are likely regular words.
        i = start - 1
        while i >= 0 and text[i].isspace():
            i -= 1
        if i < 0 or text[i] in ".!?\n\r":
            continue

        # Skip if ALL tokens are common/stop words.
        if all(t in COMMON_WORDS for t in tokens):
            continue

        # For single-word matches: skip if it's in COMMON_WORDS.
        # Otherwise treat it as a proper noun candidate (e.g. Reykjavik, Vance).
        if len(tokens) == 1:
            if tokens[0] in COMMON_WORDS:
                continue

        # For two-word matches: skip if lead word is common (e.g. "The Report")
        if len(tokens) == 2 and tokens[0] in COMMON_WORDS:
            continue

        matches.append((start, end, phrase))
    return matches


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------

def falcon_preprocess(text: str, level: str = "STANDARD",
                      custom_terms: Optional[List[str]] = None,
                      salt: Optional[str] = None,
                      placeholder_cache: Optional[Dict[str, str]] = None,
                      mission_vault: Optional['VaultManager'] = None,
                      workflow: Optional[str] = None,
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

    # Build workflow-aware COMMON_WORDS for this specific call
    # This ensures domain stopwords (legal, medical, etc.) are active
    if workflow:
        import sys as _sys
        _module = _sys.modules[__name__]
        _active_common_words = _build_common_words(workflow=workflow)
        # Temporarily shadow the module-level COMMON_WORDS for this call
        _orig_common_words = _module.COMMON_WORDS
        _module.COMMON_WORDS = _active_common_words
    else:
        _orig_common_words = None

    # Per-request salt: deterministic within this call, different across calls
    if salt is None:
        salt = hashlib.sha256(f"{id(text)}:{len(text)}:{hash(text)}".encode()).hexdigest()[:12]
    
    if placeholder_cache is None:
        placeholder_cache = {}  # fresh cache per request

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
        person_hits = _detect_person_names(text)
        if debug:
            print(f"[FALCON PASS B] Person detections: {person_hits}")
        for start, end, matched in person_hits:
            detections.append((start, end, matched, "PERSON"))
        org_hits = _detect_org_names(text)
        if debug:
            print(f"[FALCON PASS B] Org detections: {org_hits}")
        for start, end, matched in org_hits:
            detections.append((start, end, matched, "ORG"))
        loc_hits = _detect_locations(text)
        if debug:
            print(f"[FALCON PASS B] Location detections: {loc_hits}")
        for start, end, matched in loc_hits:
            detections.append((start, end, matched, "LOCATION"))
        proper_hits = _detect_proper_noun_phrases(text)
        if debug:
            print(f"[FALCON PASS B] Proper noun detections: {proper_hits}")
        for start, end, matched in proper_hits:
            detections.append((start, end, matched, "PROPER_NOUN"))

    # -----------------------------------------------------------------------
    # PASS C: Custom dictionary (all levels)
    # custom_terms already includes org config terms (merged above).
    # -----------------------------------------------------------------------
    if debug:
        print(f"[FALCON PASS C] custom_terms ({len(custom_terms) if custom_terms else 0}): {custom_terms}")

    if custom_terms:
        # Use set to unique and sort by length descending to match longest first
        unique_terms = sorted(list(set(custom_terms)), key=len, reverse=True)
        for term in unique_terms:
            if len(term) < 2:
                continue
            escaped = re.escape(term)
            found = list(re.finditer(escaped, text, re.IGNORECASE))
            if found and debug:
                print(f"[FALCON PASS C] MATCH '{term}': {len(found)} hits")
            for m in found:
                detections.append((m.start(), m.end(), m.group(), "CUSTOM"))

    # -----------------------------------------------------------------------
    # DEDUPLICATION: Resolve overlapping spans (longer match wins)
    # Priority: ORG > CUSTOM > LOCATION > PERSON (ORG suffix match is more
    # specific than heuristic PERSON, so it wins ties of equal length)
    # -----------------------------------------------------------------------
    _CAT_PRIORITY = {"ORG": 0, "CUSTOM": 1, "ALNUM_TAG": 2, "LOCATION": 3, "PROPER_NOUN": 4, "PERSON": 5}
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
    if debug:
        print(f"[FALCON] Pre-dedup detections: {len(detections)} | Post-dedup: {len(filtered)}")
        print(f"[FALCON] Final detections: {[(orig, cat) for _, _, orig, cat in filtered]}")

    # -----------------------------------------------------------------------
    # REPLACEMENT
    # -----------------------------------------------------------------------
    placeholder_map: Dict[str, str] = {}
    counts: Dict[str, int] = {}
    ghost_map: List[Dict] = []     # Ghost Map — safe token inventory
    redacted = text

    # Category normalizer: TITLED_NAME and INITIAL_NAME resolve as PERSON
    # so the vault assigns PERSON_01 style tokens instead of TITLED_NAME_01
    _VAULT_CATEGORY_MAP = {
        "TITLED_NAME": "PERSON",
        "INITIAL_NAME": "PERSON",
        "SSN_PARTIAL": "SSN",
    }

    for start, end, original, category in filtered:
        vault_category = _VAULT_CATEGORY_MAP.get(category, category)
        if mission_vault is not None:
            placeholder = mission_vault.get_or_create(vault_category, original)
        else:
            placeholder = _stable_placeholder(vault_category, original, salt, placeholder_cache)
        placeholder_map[placeholder] = original
        counts[category] = counts.get(category, 0) + 1
        ghost_map.append({
            "token": placeholder,
            "entity_type": vault_category,
            "raw_category": category,          # preserves TITLED_NAME / INITIAL_NAME etc.
            "source_pass": (
                "regex" if category in REGEX_PATTERNS else
                "ner_person" if category == "PERSON" else
                "ner_org" if category == "ORG" else
                "ner_location" if category == "LOCATION" else
                "custom" if category == "CUSTOM" else "ner_proper"
            ),
            "char_offset": start,
            "char_length": end - start,
        })
        redacted = redacted[:start] + placeholder + redacted[end:]

    # -----------------------------------------------------------------------
    # METADATA (safe to serialize — contains NO original values)
    # -----------------------------------------------------------------------
    high_risk_categories = {"SSN", "CC_NUM", "ACCT_NUM"}
    high_risk_count = sum(counts.get(c, 0) for c in high_risk_categories)

    execution_time_ms = (time.time() - start_time) * 1000
    
    metadata = {
        "level": falcon_level.value,
        "redaction_mode": "deterministic" if mission_vault is not None else "hash",
        "total_redactions": len(filtered),
        "counts_by_category": counts,
        "high_risk_items_count": high_risk_count,
        "categories_found": list(counts.keys()),
        "custom_terms_loaded": len(custom_terms) if custom_terms else 0,
        "execution_time_ms": round(execution_time_ms, 2),
        "exposure_risk": _assess_exposure_risk(len(filtered), high_risk_count, len(text)),
    }

    if debug:
        print(f"[FALCON DEBUG] Level: {level} | Redacted: {len(filtered)} | Risk: {metadata['exposure_risk']} | Latency: {metadata['execution_time_ms']}ms")

    # Restore original module-level COMMON_WORDS if we swapped it for workflow
    if workflow and _orig_common_words is not None:
        import sys as _sys
        _sys.modules[__name__].COMMON_WORDS = _orig_common_words

    return FalconResult(redacted, placeholder_map, metadata, ghost_map=ghost_map)


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


def _assess_exposure_risk(total_redactions: int, high_risk_count: int,
                          text_length: int = 0) -> str:
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
    # Long prompt but nothing redacted — potential miss
    elif text_length >= 80:
        return "potential_miss"
    return "none"


# ---------------------------------------------------------------------------
# DEBUG MODE: Safe diagnostic output (never exposes raw text or map values)
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# GHOST MAP UTILITIES
# ---------------------------------------------------------------------------

def build_ghost_map_summary(result: FalconResult) -> Dict:
    """
    Build a structured, safe-to-serialize Ghost Map summary from a FalconResult.
    Groups tokens by entity_type with counts — suitable for MIMIR prompt injection
    and the Decision Ledger pii_scan event.

    Returns a dict with:
      - token_inventory: [{token, entity_type, source_pass, char_offset}]
      - by_type: {entity_type: [token, ...]}
      - total_redacted: int
      - high_risk_types: [entity_types with SSN/CC/ACCT]
    """
    by_type: Dict[str, List[str]] = {}
    for entry in result.ghost_map:
        etype = entry["entity_type"]
        by_type.setdefault(etype, []).append(entry["token"])

    high_risk = {e for e in by_type if e in {"SSN", "CC_NUM", "ACCT_NUM"}}

    return {
        "token_inventory": result.ghost_map,
        "by_type": by_type,
        "total_redacted": len(result.ghost_map),
        "high_risk_types": sorted(high_risk),
        "redaction_mode": result.metadata.get("redaction_mode", "hash"),
        "falcon_level": result.metadata.get("level", "STANDARD"),
    }


def detect_residual_pii(redacted_text: str,
                        original_result: FalconResult,
                        debug: bool = False) -> Dict:
    """
    PII Diff Event — runs a secondary LIGHT Falcon pass on already-redacted text
    to surface any PII that the primary pass missed.

    Use this AFTER falcon_preprocess to generate the pii_diff ledger event.

    Returns a structured residual report:
    {
      "residual_count": int,
      "residuals": [{text_fragment, category, char_offset, confidence}],
      "missed_categories": [str],
      "pii_diff_clean": bool,     # True if zero residuals found
      "audit_note": str           # Human-readable summary for MIMIR
    }

    Security: residual text fragments are included here for audit purposes.
    This dict should be stored in the ledger under pii_diff and NEVER
    returned to the client directly.
    """
    import time

    # Run a LIGHT pass on the already-redacted text.
    # LIGHT catches: EMAIL, PHONE, SSN, SSN_PARTIAL, IP_ADDR, ACCT_NUM,
    #                CURRENCY_AMOUNT, IBAN, TITLED_NAME, INITIAL_NAME
    # These are the most egregious misses — structured identifiers that
    # regex should always catch regardless of level.
    secondary = falcon_preprocess(
        redacted_text,
        level="LIGHT",
        debug=debug,
    )

    residuals = []
    for entry in secondary.ghost_map:
        # Skip hits that are just placeholder tokens re-detected
        # (e.g. [PERSON_01] caught by PASSPORT pattern — false alarm)
        frag = redacted_text[entry["char_offset"]: entry["char_offset"] + entry["char_length"]]
        if frag.startswith("[") and frag.endswith("]"):
            continue
        residuals.append({
            "text_fragment": frag,
            "category": entry["entity_type"],
            "raw_category": entry["raw_category"],
            "char_offset": entry["char_offset"],
            "confidence": (
                "high"   if entry["entity_type"] in {"SSN", "CC_NUM", "IBAN", "EMAIL"} else
                "medium" if entry["entity_type"] in {"PHONE", "ACCT_NUM", "CURRENCY_AMOUNT"} else
                "low"
            ),
        })

    missed_cats = sorted({r["category"] for r in residuals})
    clean = len(residuals) == 0

    if clean:
        audit_note = (
            f"PII_DIFF_CLEAN: Secondary pass found no residual PII in "
            f"{len(redacted_text)} chars of redacted text. "
            f"Primary pass captured {original_result.metadata.get('total_redactions', 0)} entities."
        )
    else:
        audit_note = (
            f"PII_DIFF_ALERT: {len(residuals)} residual item(s) detected after primary Falcon pass. "
            f"Missed categories: {', '.join(missed_cats)}. "
            f"Primary pass captured {original_result.metadata.get('total_redactions', 0)} entities. "
            f"Re-run at STANDARD or BLACK level, or add missed terms to falcon_config.json."
        )

    if debug:
        print(f"[RESIDUAL] {audit_note}")

    return {
        "residual_count": len(residuals),
        "residuals": residuals,
        "missed_categories": missed_cats,
        "pii_diff_clean": clean,
        "audit_note": audit_note,
        "primary_redaction_count": original_result.metadata.get("total_redactions", 0),
        "primary_level": original_result.metadata.get("level", "STANDARD"),
    }

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
    # STANDARD and BLACK should catch the date, LIGHT should not
    _assert("DATE" not in r_light.metadata['counts_by_category'],
            "LIGHT does not redact dates")
    _assert("DATE" in r_standard.metadata['counts_by_category'],
            "STANDARD redacts dates")
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
    # TEST 11: Falcon acid test prompt coverage
    # ------------------------------------------------------------------
    print("\n--- Test 11: Acid Prompt Coverage ---")
    text = (
        "Contact Agent 4402 regarding the Blue-Vein shipment arriving at "
        "Sector 7-G tomorrow at 0900. Email confirmation to h.vance@aetherflow.net."
    )
    result = falcon_preprocess(text, level="BLACK")
    _assert(len(result.placeholder_map) >= 4,
            f"Acid prompt: placeholder map has {len(result.placeholder_map)} entries (expected >= 4)")
    _assert("ALNUM_TAG" in result.metadata['categories_found'],
            "Acid prompt: ALNUM_TAG detected")
    _assert("EMAIL" in result.metadata['categories_found'],
            "Acid prompt: EMAIL detected")
    _assert(
        ("PROPER_NOUN" in result.metadata['categories_found'])
        or ("LOCATION" in result.metadata['categories_found'])
        or ("CUSTOM" in result.metadata['categories_found']),
        "Acid prompt: proper noun/location/project detected"
    )

    # ------------------------------------------------------------------
    # TEST 12: Single-word proper noun detection ("Reykjavik Gap")
    # ------------------------------------------------------------------
    print("\n--- Test 12: Single-Word Proper Noun Detection ---")
    text = (
        "we met with Vance and Thorne to discuss the relocation to Akureyri "
        "before the handoff to Matsuda at the safe house."
    )
    result = falcon_preprocess(text, level="STANDARD")
    _assert("PROPER_NOUN" in result.metadata['categories_found'],
            "Single-word proper nouns detected")
    _assert("Vance" not in result.redacted_text,
            "Proper noun 'Vance' was redacted")
    _assert("Thorne" not in result.redacted_text,
            "Proper noun 'Thorne' was redacted")
    _assert("Akureyri" not in result.redacted_text,
            "Proper noun 'Akureyri' was redacted")
    _assert("Matsuda" not in result.redacted_text,
            "Proper noun 'Matsuda' was redacted")
    # Common words should NOT be redacted
    _assert("relocation" in result.redacted_text,
            "Common word 'relocation' preserved")
    _assert("handoff" in result.redacted_text,
            "Common word 'handoff' preserved")

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

