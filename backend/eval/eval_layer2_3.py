"""
eval/eval_layer2_3.py — Layer 2: Critic score checks  |  Layer 3: Judge

Layer 2 (deterministic):
  - Critic scores fall within expected min/max bounds from the test CSV
  - Critic issues list contains expected flag keywords for seeded bad cases

Layer 3 (LLM-based, bad cases only by default):
  - Cerebras judge audits whether the critic's reasoning is accurate
  - Uses the same CEREBRAS_API_KEY already in the environment
  - Returns accuracy_score 1-10 plus missed/hallucinated issues
"""

import json
import os
import time
from pathlib import Path

import requests

JUDGE_MODEL = "qwen-3-32b"   # lighter than 235B; adequate for text reasoning

JUDGE_SYSTEM = """\
You are an expert travel itinerary auditor.
You will be given: an itinerary, a critic's scores and issues, and context about the case.
Your job is NOT to re-evaluate the itinerary. Your job is to audit whether the CRITIC is accurate.

Assess:
- Do the flagged issues actually exist in the itinerary text?
- Did the critic miss any obvious problems?
- Are the scores consistent with the issues found?
- For seeded bad cases: did the critic identify the planted problem?

Return ONLY valid JSON, no markdown fences:
{
  "accuracy_score": <int 1-10>,
  "missed_issues": [<string>, ...],
  "hallucinated_issues": [<string>, ...],
  "score_consistency": <"consistent" | "inflated" | "deflated">,
  "reasoning": <one-sentence summary>
}

Scoring guide:
  8-10  critic found all real problems, no false ones
  5-7   minor misses or slight score inflation/deflation
  1-4   missed the main planted problem, or scores contradict issues
"""

KEYWORD_MAP = {
    "transport":  ["transport", "train", "distance", "travel time", "feasib", "unrealistic journey", "km"],
    "pacing":     ["pacing", "too many cities", "too few days", "rushed", "one city", "only one city", "overcrowded"],
    "preference": ["beach", "preference", "interest", "mismatch", "nordic", "cold", "climate"],
}


# ---------------------------------------------------------------------------
# Layer 2
# ---------------------------------------------------------------------------

def score_in_range(score, min_val, max_val):
    """
    Returns True/False if bounds exist, None if neither bound is set (N/A).
    """
    has_min = min_val not in ("", None)
    has_max = max_val not in ("", None)
    if not has_min and not has_max:
        return None
    try:
        s = float(score)
    except (TypeError, ValueError):
        return False
    if has_min and s < float(min_val):
        return False
    if has_max and s > float(max_val):
        return False
    return True


def check_flags(expected_flags_str: str, issues: list[str]) -> tuple[bool | None, str, str]:
    """
    Check that all expected flag keywords appear in the critic's issues text.
    Returns (passed, expected_str, actual_str).
    passed is None if no flags were expected.
    """
    if not expected_flags_str or not expected_flags_str.strip():
        return None, "", ""

    expected = [f.strip().lower() for f in expected_flags_str.split("|") if f.strip()]
    issues_text = " ".join(issues).lower()

    matched, missing = [], []
    for flag in expected:
        keywords = KEYWORD_MAP.get(flag, [flag])
        (matched if any(kw in issues_text for kw in keywords) else missing).append(flag)

    actual = "|".join(matched) if matched else "none"
    if missing:
        return False, expected_flags_str, f"missing:{','.join(missing)}|found:{actual}"
    return True, expected_flags_str, actual


# ---------------------------------------------------------------------------
# Layer 3
# ---------------------------------------------------------------------------

def _load_api_key() -> str:
    key = os.environ.get("CEREBRAS_API_KEY", "")
    if key:
        return key
    env_path = Path("backend/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("CEREBRAS_API_KEY="):
                return line.split("=", 1)[1].strip().strip("\"'")
    return ""


def run_judge(
    itinerary: str,
    critique: dict,
    case_type: str,
    planted_problem: str = "",
) -> tuple[dict | None, float, str | None]:
    """
    Ask the Cerebras judge whether the critic's evaluation is accurate.
    Returns (result_dict, elapsed_seconds, error_or_None).
    result_dict keys: accuracy_score, missed_issues, hallucinated_issues,
                      score_consistency, reasoning
    """
    api_key = _load_api_key()
    if not api_key:
        return None, 0.0, "CEREBRAS_API_KEY not found — skipping judge"

    issues_text = "\n".join(f"- {i}" for i in critique.get("issues", [])) or "(none)"
    planted_note = f"\nNOTE — planted problem: {planted_problem}" if planted_problem else ""

    user_msg = (
        f"Itinerary:\n{itinerary}\n\n"
        f"Critic scores: realism={critique.get('realism_score')}  "
        f"pacing={critique.get('pacing_score')}  "
        f"preference={critique.get('preference_score')}\n\n"
        f"Critic issues:\n{issues_text}\n\n"
        f"Case type: {case_type}{planted_note}"
    )

    payload = {
        "model": JUDGE_MODEL,
        "max_tokens": 600,
        "messages": [
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user",   "content": user_msg},
        ],
    }

    t0 = time.perf_counter()
    try:
        resp = requests.post(
            "https://api.cerebras.ai/v1/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=120,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        elapsed = time.perf_counter() - t0

        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()

        return json.loads(raw), elapsed, None

    except requests.RequestException as exc:
        return None, time.perf_counter() - t0, f"judge_request_error: {exc}"
    except (json.JSONDecodeError, KeyError) as exc:
        return None, time.perf_counter() - t0, f"judge_parse_error: {exc}"