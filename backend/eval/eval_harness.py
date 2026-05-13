"""
eval/eval_harness.py — Europlan-AI eval harness (main runner)

Runs all test cases through the planner and critic pipeline, then
applies three evaluation layers imported from sibling modules:

  eval_layer1   — structural assertions (deterministic)
  eval_layer2_3 — critic score/flag checks (L2) + Cerebras judge (L3)

Usage:
  python eval/eval_harness.py
  python eval/eval_harness.py --start 15          # resume interrupted run
  python eval/eval_harness.py --judge all         # run judge on every case
  python eval/eval_harness.py --judge none        # skip judge entirely
  EVAL_BASE_URL=http://... python eval/eval_harness.py
"""

import argparse
import csv
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests

# Ensure sibling eval modules are importable regardless of cwd
sys.path.insert(0, str(Path(__file__).parent))

from eval_layer1   import structural_assertions
from eval_layer2_3 import score_in_range, check_flags, run_judge

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_URL      = os.environ.get("EVAL_BASE_URL", "http://localhost:8000")
JUDGE_SCOPE   = os.environ.get("EVAL_JUDGE_SCOPE", "bad")  # "bad" | "all" | "none"
SLEEP_BETWEEN = 0.5
MAX_RETRIES   = 3
RETRY_BACKOFF = [2, 5, 10]

# Paths are resolved relative to this file so the harness works regardless
# of which directory you run it from.
_HERE = Path(__file__).parent

RESULTS_FIELDS = [
    "case_id", "case_type", "cities", "trip_length", "interests", "trip_id",
    "struct_pass", "struct_failures",
    "realism_score", "expected_realism_min", "expected_realism_max", "realism_pass",
    "pacing_score",  "expected_pacing_min",  "expected_pacing_max",  "pacing_pass",
    "preference_score", "expected_preference_min", "expected_preference_max", "preference_pass",
    "expected_flags", "actual_flags", "flags_pass",
    "judge_accuracy", "judge_reasoning",
    "layer1_pass", "layer2_pass", "layer3_pass", "overall_pass",
    "issues_count", "transport_legs_count", "infeasible_legs",
    "plan_time_s", "critique_time_s", "judge_time_s", "total_time_s",
    "status", "error_detail",
]


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _with_retry(fn, label):
    elapsed = 0.0
    for attempt in range(MAX_RETRIES):
        result, elapsed, err = fn()
        if err is None:
            return result, elapsed, None
        wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
        print(f"\n       {label} failed (attempt {attempt+1}/{MAX_RETRIES}): {err}")
        if attempt < MAX_RETRIES - 1:
            print(f"       retrying in {wait}s...", end=" ", flush=True)
            time.sleep(wait)
    return None, elapsed, err


def _plan(cities, trip_length, interests):
    t0 = time.perf_counter()
    try:
        resp = requests.post(
            f"{BASE_URL}/plan-trip",
            json={"cities": cities, "trip_length": trip_length, "interests": interests},
            stream=True, timeout=300,
        )
        resp.raise_for_status()
        itinerary = "".join(c for c in resp.iter_content(chunk_size=None, decode_unicode=True) if c)
        trip_id   = resp.headers.get("X-Trip-Id")
        elapsed   = time.perf_counter() - t0
        return (trip_id, itinerary), elapsed, (None if trip_id else "X-Trip-Id header missing")
    except requests.RequestException as exc:
        return (None, None), time.perf_counter() - t0, str(exc)


def _critique(trip_id):
    t0 = time.perf_counter()
    try:
        resp = requests.post(f"{BASE_URL}/critique-trip/{trip_id}", timeout=120)
        resp.raise_for_status()
        return resp.json(), time.perf_counter() - t0, None
    except Exception as exc:
        return None, time.perf_counter() - t0, str(exc)


def run_plan(cities, trip_length, interests):
    result, elapsed, err = _with_retry(lambda: _plan(cities, trip_length, interests), "plan")
    if err:
        return None, None, elapsed, err
    trip_id, itinerary = result
    return trip_id, itinerary, elapsed, None


def run_critique(trip_id):
    return _with_retry(lambda: _critique(trip_id), "critique")


def _cleanup(results_file: Path):
    if not results_file.exists():
        return
    with results_file.open(newline="", encoding="utf-8") as f:
        trip_ids = [r["trip_id"] for r in csv.DictReader(f) if r.get("trip_id")]
    if not trip_ids:
        return
    print(f"Cleaning up {len(trip_ids)} eval trips...", end=" ", flush=True)
    deleted = sum(
        1 for tid in trip_ids
        if requests.delete(f"{BASE_URL}/trips/{tid}", timeout=10).status_code in (200, 204, 404)
    )
    print(f"deleted {deleted}")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_harness(cases_path, results_path, start_id=0):
    cases_file   = Path(cases_path)
    results_file = Path(results_path)

    if not cases_file.exists():
        print(f"[ERROR] Test cases not found: {cases_file}")
        sys.exit(1)

    with cases_file.open(newline="", encoding="utf-8") as f:
        cases = list(csv.DictReader(f))

    print(f"Europlan-AI eval harness — {len(cases)} cases | {BASE_URL} | judge={JUDGE_SCOPE}")
    if start_id:
        print(f"Resuming from case_id >= {start_id}")
    print("-" * 70)

    mode = "a" if (start_id and results_file.exists()) else "w"
    results_file.parent.mkdir(parents=True, exist_ok=True)

    def fmt(v): return "PASS" if v is True else ("FAIL" if v is False else "N/A")

    with results_file.open(mode, newline="", encoding="utf-8") as rf:
        writer = csv.DictWriter(rf, fieldnames=RESULTS_FIELDS, extrasaction="ignore")
        if mode == "w":
            writer.writeheader()

        for i, case in enumerate(cases, 1):
            case_id  = int(case["case_id"])
            if case_id < start_id:
                continue

            cities      = [c.strip() for c in case["cities"].split(",") if c.strip()]
            trip_length = int(case["trip_length"])
            interests   = [x.strip() for x in case["interests"].split(",") if x.strip()]
            case_type   = case.get("case_type", "good")
            planted     = case.get("planted_problem", "")

            print(f"[{i:02d}/{len(cases)}] case {case_id} ({case_type}) — {case['cities'][:40]} ({trip_length}d)", end=" ... ", flush=True)

            row = {
                "case_id": case_id, "case_type": case_type,
                "cities": case["cities"], "trip_length": trip_length, "interests": case["interests"],
                **{k: case.get(k, "") for k in [
                    "expected_realism_min", "expected_realism_max",
                    "expected_pacing_min",  "expected_pacing_max",
                    "expected_preference_min", "expected_preference_max",
                    "expected_flags",
                ]},
            }
            t_total = time.perf_counter()

            # ---- Plan -------------------------------------------------------
            trip_id, itinerary, plan_time, plan_err = run_plan(cities, trip_length, interests)
            row["plan_time_s"] = f"{plan_time:.2f}"
            if plan_err or not trip_id:
                row.update(status="plan_error", error_detail=plan_err or "no trip_id",
                            total_time_s=f"{time.perf_counter()-t_total:.2f}", overall_pass="ERROR")
                writer.writerow(row); rf.flush()
                print(f"PLAN ERROR — {row['error_detail']}")
                time.sleep(SLEEP_BETWEEN); continue

            row["trip_id"] = trip_id
            time.sleep(SLEEP_BETWEEN)

            # ---- Layer 1 ----------------------------------------------------
            l1_pass, l1_failures = structural_assertions(itinerary, cities, trip_length)
            row.update(
                struct_pass="PASS" if l1_pass else "FAIL",
                struct_failures="; ".join(l1_failures),
                layer1_pass="PASS" if l1_pass else "FAIL",
            )

            # ---- Critique ---------------------------------------------------
            critique, crit_time, crit_err = run_critique(trip_id)
            row["critique_time_s"] = f"{crit_time:.2f}"
            if crit_err or critique is None:
                row.update(status="critique_error", error_detail=crit_err or "empty response",
                            total_time_s=f"{time.perf_counter()-t_total:.2f}",
                            layer2_pass="ERROR", overall_pass="ERROR")
                writer.writerow(row); rf.flush()
                print(f"CRITIQUE ERROR — {row['error_detail']}")
                time.sleep(SLEEP_BETWEEN); continue

            # ---- Layer 2 ----------------------------------------------------
            realism    = critique.get("realism_score", "")
            pacing     = critique.get("pacing_score", "")
            preference = critique.get("preference_score", "")
            issues     = critique.get("issues", [])
            legs       = critique.get("transport_legs", [])

            r_pass    = score_in_range(realism,    case.get("expected_realism_min"),    case.get("expected_realism_max"))
            p_pass    = score_in_range(pacing,     case.get("expected_pacing_min"),     case.get("expected_pacing_max"))
            pref_pass = score_in_range(preference, case.get("expected_preference_min"), case.get("expected_preference_max"))
            f_pass, _, act_f = check_flags(case.get("expected_flags", ""), issues)

            score_checks = [v for v in [r_pass, p_pass, pref_pass, f_pass] if v is not None]
            l2_pass = all(score_checks) if score_checks else True

            row.update(
                realism_score=realism, pacing_score=pacing, preference_score=preference,
                issues_count=len(issues), transport_legs_count=len(legs),
                infeasible_legs=sum(1 for l in legs if not l.get("feasible", True)),
                realism_pass=fmt(r_pass), pacing_pass=fmt(p_pass),
                preference_pass=fmt(pref_pass), flags_pass=fmt(f_pass), actual_flags=act_f,
                layer2_pass="PASS" if l2_pass else "FAIL",
            )

            # ---- Layer 3 (judge) --------------------------------------------
            should_judge = JUDGE_SCOPE == "all" or (JUDGE_SCOPE == "bad" and case_type.startswith("bad"))
            l3_pass = None

            if should_judge:
                print("(judging...)", end=" ", flush=True)
                judge_result, judge_time, judge_err = run_judge(itinerary, critique, case_type, planted)
                row["judge_time_s"] = f"{judge_time:.2f}"

                if judge_err or judge_result is None:
                    row.update(judge_accuracy="", judge_reasoning=judge_err or "no result", layer3_pass="ERROR")
                else:
                    accuracy = judge_result.get("accuracy_score", "")
                    row.update(judge_accuracy=accuracy, judge_reasoning=judge_result.get("reasoning", ""))
                    try:
                        l3_pass = float(accuracy) >= 6
                        row["layer3_pass"] = "PASS" if l3_pass else "FAIL"
                    except (TypeError, ValueError):
                        row["layer3_pass"] = "ERROR"
            else:
                row["layer3_pass"] = "N/A"

            # ---- Overall ----------------------------------------------------
            overall = l1_pass and l2_pass and (l3_pass if l3_pass is not None else True)
            row.update(overall_pass="PASS" if overall else "FAIL", status="ok",
                       total_time_s=f"{time.perf_counter()-t_total:.2f}")
            writer.writerow(row); rf.flush()

            judge_str = f" judge={row.get('judge_accuracy','-')}" if should_judge else ""
            print(
                f"{'PASS' if overall else 'FAIL'}  "
                f"L1={row['layer1_pass']} L2={row['layer2_pass']} L3={row['layer3_pass']}  "
                f"realism={realism} pacing={pacing} pref={preference}{judge_str}  {row['total_time_s']}s"
            )
            for sf in l1_failures:
                print(f"       struct: {sf}")

            time.sleep(SLEEP_BETWEEN)

    print("-" * 70)
    _cleanup(results_file)
    print(f"Results → {results_file}")
    _print_summary(results_file)


# ---------------------------------------------------------------------------
# Summary (pandas, with plain-text fallback)
# ---------------------------------------------------------------------------

def _print_summary(results_file: Path):
    try:
        import pandas as pd
    except ImportError:
        _print_summary_plain(results_file)
        return

    df = pd.read_csv(results_file)
    for col in ["realism_score", "pacing_score", "preference_score", "judge_accuracy",
                "plan_time_s", "critique_time_s", "judge_time_s", "total_time_s"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    ok     = df[df["status"] == "ok"]
    errors = df[df["status"] != "ok"]
    good   = ok[ok["case_type"] == "good"]
    bad    = ok[ok["case_type"].str.startswith("bad", na=False)]

    def pct(subset, col):
        v = subset[col] if col in subset.columns else pd.Series(dtype=str)
        valid = v.isin(["PASS", "FAIL"])
        if not valid.any(): return "N/A"
        n = (v[valid] == "PASS").sum()
        return f"{n}/{valid.sum()} ({100*n//valid.sum()}%)"

    sep = "─" * 70
    print(f"\n{'='*70}")
    print(f"SUMMARY  —  {len(ok)} completed / {len(errors)} errors / {len(df)} total")
    print(f"{'='*70}")
    print(f"Overall:   {pct(ok, 'overall_pass')}")
    print(f"  Layer 1: {pct(ok, 'layer1_pass')}")
    print(f"  Layer 2: {pct(ok, 'layer2_pass')}")
    judged = ok[ok["layer3_pass"].isin(["PASS","FAIL"])]
    print(f"  Layer 3: {pct(judged, 'layer3_pass')}  (judged cases only)")

    # Per case_type table
    print(f"\n{sep}\nBY CASE TYPE\n{sep}")
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 120)
    agg = ok.groupby("case_type").agg(
        n=("case_id","count"),
        realism=("realism_score","mean"),
        pacing=("pacing_score","mean"),
        preference=("preference_score","mean"),
        judge=("judge_accuracy","mean"),
        avg_time=("total_time_s","mean"),
    ).round(2)
    for ct in ok["case_type"].unique():
        sub = ok[ok["case_type"] == ct]
        agg.loc[ct, "overall%"] = pct(sub, "overall_pass")
        agg.loc[ct, "flags%"]   = pct(sub[sub["flags_pass"].isin(["PASS","FAIL"])], "flags_pass")
    print(agg.to_string())

    # Good detail
    if not good.empty:
        print(f"\n{sep}\nGOOD CASES ({len(good)})\n{sep}")
        print(f"  Avg realism={good['realism_score'].mean():.2f}  pacing={good['pacing_score'].mean():.2f}  pref={good['preference_score'].mean():.2f}")
        print(f"  Avg plan time: {good['plan_time_s'].mean():.1f}s")

    # Bad detail + judge
    if not bad.empty:
        print(f"\n{sep}\nBAD CASES ({len(bad)})  — critic should score LOW\n{sep}")
        print(f"  Critic catch rate (L2): {pct(bad, 'layer2_pass')}")
        print(f"  Flags catch rate:       {pct(bad[bad['flags_pass'].isin(['PASS','FAIL'])], 'flags_pass')}")
        print(f"  Avg realism={bad['realism_score'].mean():.2f}  pacing={bad['pacing_score'].mean():.2f}")
        jb = bad[bad["judge_accuracy"].notna()]
        if not jb.empty:
            print(f"\n  Judge accuracy (bad cases):  mean={jb['judge_accuracy'].mean():.2f}")
            print(jb.groupby("case_type")["judge_accuracy"].agg(["mean","count"]).round(2).to_string())

    # Structural failures detail
    sf = ok[ok["layer1_pass"] == "FAIL"]
    if not sf.empty:
        print(f"\n{sep}\nSTRUCTURAL FAILURES ({len(sf)})\n{sep}")
        for _, r in sf.iterrows():
            print(f"  case {int(r['case_id'])} ({r['case_type']}): {r['struct_failures']}")
        counts: dict = defaultdict(int)
        for token in re.split(r"[;,]", " ".join(sf["struct_failures"].dropna())):
            t = token.strip()
            if t:
                counts[re.split(r"[:_]", t)[0]] += 1
        for k, v in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"    {k}: {v}")

    # Score failures detail
    l2f = ok[ok["layer2_pass"] == "FAIL"]
    if not l2f.empty:
        print(f"\n{sep}\nSCORE RANGE FAILURES ({len(l2f)})\n{sep}")
        for _, r in l2f.iterrows():
            details = []
            for dim in ["realism", "pacing", "preference"]:
                if r.get(f"{dim}_pass") == "FAIL":
                    details.append(f"{dim}={r[f'{dim}_score']:.0f} [{r[f'expected_{dim}_min']}-{r[f'expected_{dim}_max']}]")
            if r.get("flags_pass") == "FAIL":
                details.append(f"flags: expected={r['expected_flags']} got={r['actual_flags']}")
            print(f"  case {int(r['case_id'])} ({r['case_type']}): {', '.join(details)}")

    # Critic consistency alert
    alert = bad[bad["judge_accuracy"].notna() & (bad["judge_accuracy"] <= 4)]
    if not alert.empty:
        print(f"\n{sep}\nCRITIC CONSISTENCY ALERT — judge ≤ 4 on {len(alert)} case(s)\n{sep}")
        for _, r in alert.iterrows():
            print(f"  case {int(r['case_id'])} ({r['case_type']}): judge={r['judge_accuracy']}  {r.get('judge_reasoning','')}")

    # Timing
    if not ok.empty:
        print(f"\n{sep}\nTIMING\n{sep}")
        print(f"  plan={ok['plan_time_s'].mean():.1f}s  critique={ok['critique_time_s'].mean():.1f}s  total={ok['total_time_s'].mean():.1f}s")

    if not errors.empty:
        print(f"\n{sep}\nERRORS ({len(errors)})\n{sep}")
        for _, r in errors.iterrows():
            print(f"  case {int(r['case_id'])} [{r['status']}] {r.get('error_detail','')}")
    print()


def _print_summary_plain(results_file: Path):
    with results_file.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    ok     = [r for r in rows if r["status"] == "ok"]
    errors = [r for r in rows if r["status"] != "ok"]
    good   = [r for r in ok if r["case_type"] == "good"]
    bad    = [r for r in ok if r["case_type"].startswith("bad")]

    def pct(subset, field):
        if not subset: return "N/A"
        n = sum(1 for r in subset if r.get(field) == "PASS")
        return f"{n}/{len(subset)} ({100*n//len(subset)}%)"

    def avg(subset, field):
        vals = [float(r[field]) for r in subset if r.get(field) not in ("", None)]
        return f"{sum(vals)/len(vals):.2f}" if vals else "N/A"

    print(f"\n{'='*70}\nSUMMARY — {len(ok)} ok / {len(errors)} errors\n{'='*70}")
    print(f"Overall={pct(ok,'overall_pass')}  L1={pct(ok,'layer1_pass')}  L2={pct(ok,'layer2_pass')}")
    if good: print(f"Good: realism={avg(good,'realism_score')} pacing={avg(good,'pacing_score')} pref={avg(good,'preference_score')}")
    if bad:  print(f"Bad:  catch={pct(bad,'layer2_pass')} flags={pct(bad,'flags_pass')}  realism={avg(bad,'realism_score')} pacing={avg(bad,'pacing_score')}")
    for r in errors:
        print(f"  ERROR case {r['case_id']}: {r.get('error_detail','')}")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Europlan-AI eval harness")
    parser.add_argument("--cases",  default=str(_HERE / "test_cases.csv"))
    parser.add_argument("--out",    default=str(_HERE / "results.csv"))
    parser.add_argument("--start",  type=int, default=0, help="Resume from this case_id")
    parser.add_argument("--judge",  choices=["bad","all","none"], default=None)
    args = parser.parse_args()

    if args.judge is not None:
        JUDGE_SCOPE = args.judge

    run_harness(args.cases, args.out, args.start)