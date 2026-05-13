"""
eval/eval_layer1.py — Layer 1: Structural assertions (deterministic, no LLM)

Checks run against the raw itinerary text before any LLM evaluation:
  - City presence (with diacritic aliases)
  - Day count matches trip_length
  - No empty day sections
  - Itinerary not suspiciously short
  - No attraction repeated across multiple days  (new)
  - No city drastically over/under-allocated days  (new)
"""

import re
from collections import defaultdict

# ---------------------------------------------------------------------------
# City alias map — GeoNames spellings vs ASCII variants the LLM may write
# ---------------------------------------------------------------------------

CITY_ALIASES = {
    "Kraków":     ["Krakow", "Cracow"],
    "Zürich":     ["Zurich"],
    "Köln":       ["Cologne", "Koeln"],
    "München":    ["Munich"],
    "Düsseldorf": ["Dusseldorf"],
    "Nürnberg":   ["Nuremberg"],
    "Göteborg":   ["Gothenburg"],
    "Malmö":      ["Malmo"],
    "Łódź":       ["Lodz"],
    "Wrocław":    ["Wroclaw"],
    "Gdańsk":     ["Gdansk"],
    "Poznań":     ["Poznan"],
    "Brno":       ["Brünn"],
}

# Allocation thresholds (can be overridden by callers if needed)
OVERALLOC_CAP   = 0.70   # flag if one city holds > 70% of days
DRIFT_THRESHOLD = 0.40   # flag if a city deviates from fair share by > 40pp


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _city_variants(city: str) -> list[str]:
    variants = [city] + CITY_ALIASES.get(city, [])
    for canonical, aliases in CITY_ALIASES.items():
        if city in aliases:
            variants.append(canonical)
    return variants


def _parse_day_sections(itinerary: str) -> list[tuple[int, str]]:
    """Return [(day_number, body_text), ...] for each day in the itinerary."""
    parts = re.split(r'(Day\s+\d+)', itinerary, flags=re.IGNORECASE)
    sections = []
    for i in range(1, len(parts) - 1, 2):
        header = parts[i]
        body   = parts[i + 1] if i + 1 < len(parts) else ""
        day_num = int(re.search(r'\d+', header).group())
        sections.append((day_num, body))
    return sections


def _parse_attractions(section_text: str) -> list[str]:
    """
    Pull candidate attraction names from a single day's text.
    Two patterns: bullet/dash lines and action-verb phrases.
    Returns lowercase deduplicated names.
    """
    found = []
    # "- Colosseum" or "• Roman Forum"
    for m in re.finditer(r'^[\-•*]\s+([A-Z][^\n]{3,60})', section_text, re.MULTILINE):
        found.append(m.group(1).strip().lower())
    # "Visit the Uffizi Gallery"
    for m in re.finditer(
        r'\b(?:visit|explore|see|tour|walk through|head to|stop at)\s+(?:the\s+)?([A-Z][^\.\n,]{3,50})',
        section_text,
    ):
        found.append(m.group(1).strip().lower())

    seen, unique = set(), []
    for a in found:
        if a not in seen:
            seen.add(a)
            unique.append(a)
    return unique


def _check_attraction_repetition(sections: list[tuple[int, str]]) -> list[str]:
    """Flag any attraction name (≥6 chars) found in more than one day."""
    days_by_attraction: dict[str, list[int]] = defaultdict(list)
    for day_num, body in sections:
        for attr in _parse_attractions(body):
            days_by_attraction[attr].append(day_num)

    return [
        f"repeated_attraction:'{attr}':days {days}"
        for attr, days in days_by_attraction.items()
        if len(days) > 1 and len(attr) >= 6
    ]


def _check_allocation_drift(
    sections: list[tuple[int, str]],
    cities: list[str],
    itinerary: str,
) -> list[str]:
    """
    Parse which city each day belongs to, then flag over-allocation or drift.
    Skipped for single-city trips and when >40% of days can't be matched.
    """
    if len(cities) <= 1:
        return []

    header_map = {
        int(re.search(r'\d+', hl).group()): hl
        for hl in re.findall(r'Day\s+\d+[^\n]*', itinerary, re.IGNORECASE)
        if re.search(r'\d+', hl)
    }

    city_days: dict[str, int] = {c: 0 for c in cities}
    unmatched = 0
    for day_num, body in sections:
        search = (header_map.get(day_num, "") + " " + body[:200]).lower()
        matched_city = next(
            (c for c in cities if any(v.lower() in search for v in _city_variants(c))),
            None,
        )
        if matched_city:
            city_days[matched_city] += 1
        else:
            unmatched += 1

    total = sum(city_days.values())
    if total == 0 or unmatched > len(sections) * 0.4:
        return []

    fair = total / len(cities)
    failures = []
    for city, days in city_days.items():
        share = days / total
        if share > OVERALLOC_CAP:
            failures.append(
                f"over_allocation:{city}:{days}d/{total}d ({share:.0%} > {OVERALLOC_CAP:.0%})"
            )
        elif abs(days - fair) / total > DRIFT_THRESHOLD:
            direction = "over" if days > fair else "under"
            failures.append(
                f"allocation_drift:{city}:{direction}:{days}d (fair={fair:.1f}d)"
            )
    return failures


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def structural_assertions(itinerary: str, cities: list[str], trip_length: int) -> tuple[bool, list[str]]:
    """
    Run all Layer 1 checks. Returns (passed: bool, failures: list[str]).
    An empty failures list means all checks passed.
    """
    failures = []

    # City presence
    for city in cities:
        if not any(v.lower() in itinerary.lower() for v in _city_variants(city)):
            failures.append(f"missing_city:{city}")

    # Day count
    found_days = len(set(re.findall(r'\bDay\s+(\d+)\b', itinerary, re.IGNORECASE)))
    if found_days == 0:
        failures.append("no_day_headings_found")
    elif found_days != trip_length:
        failures.append(f"day_count_mismatch:expected_{trip_length}_got_{found_days}")

    # Empty sections
    for i, section in enumerate(re.split(r'\bDay\s+\d+', itinerary, flags=re.IGNORECASE)[1:], 1):
        if len(section.strip()) < 30:
            failures.append(f"empty_day_section:day_{i}")

    # Minimum length
    if len(itinerary) < trip_length * 80:
        failures.append(f"itinerary_too_short:{len(itinerary)}_chars")

    # Attraction repetition (new)
    sections = _parse_day_sections(itinerary)
    failures.extend(_check_attraction_repetition(sections))

    # Allocation drift (new)
    failures.extend(_check_allocation_drift(sections, cities, itinerary))

    return (len(failures) == 0), failures