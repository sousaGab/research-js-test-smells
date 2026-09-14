#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyzes assertion changes in the before/after refactoring pairs.

Extracts the 3,600 code pairs from the database, compares their ASTs with
the Babel analyzer (scripts/analysis/assertion_ast_analyzer.js), classifies
each pair with verification-weakening flags, and aggregates the results
used by the article's "Changes in Test Assertions" section. The complete
rules are documented in docs/assertion-analysis.md.

Outputs in research_data/assertion_analysis/:
  pairs.jsonl               pairs extracted from the database
  metrics.jsonl             per-snippet counts (before and after)
  classified.jsonl          flags and execution context per pair
  validation_package.csv    flagged cases, laid out for human rating
"""

import csv
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import sqlite3

from llm_refactor.core.paths import PIPELINE_ROOT, RESEARCH_DATA, RESEARCH_DB

OUT_DIR = RESEARCH_DATA / "assertion_analysis"
ANALYZER = Path(__file__).resolve().parent / "assertion_ast_analyzer.js"
NODE_MODULES = (
    PIPELINE_ROOT / "src/llm_refactor/modules/detect_smells/get_method/node_modules"
)

ERROR_TYPES = "'syntax_error','runtime_error','module_resolution_error','timeout','unknown'"

# Flags that signal a weakening of the verification logic
STRICT_FLAGS = {
    "ASSERTION_LOSS",
    "ALL_ASSERTIONS_GONE",
    "TAUTOLOGY_ADDED",
    "TEST_DISABLED",
    "TEST_EMPTIED",
    "TEST_CASE_REMOVED",
    "ASSERTION_COMMENTED_OUT",
    "EXPECT_ASSERTIONS_REMOVED",
    "EXECUTED_TESTS_DECREASED",
}

# Mechanically verifiable flags; a bare assertion-count loss
# (ASSERTION_LOSS alone) requires human validation
MECHANICAL_FLAGS = {
    "TAUTOLOGY_ADDED",
    "EXECUTED_TESTS_DECREASED",
    "TEST_DISABLED",
    "TEST_EMPTIED",
    "ASSERTION_COMMENTED_OUT",
    "EXPECT_ASSERTIONS_REMOVED",
}


def extract_pairs():
    """Extracts the before/after pairs and execution context from the database."""
    conn = sqlite3.connect(RESEARCH_DB)
    conn.row_factory = sqlite3.Row
    query = f"""
        SELECT e.id, e.ai_model_version AS model, e.prompting_approach AS prompt,
               e.smell_removed, e.tests_failed_type,
               COALESCE(ss.smell_type, '?') AS smell, r.name AS repo,
               e.original_code, e.refactored_code,
               tb.tests_failed AS tb_fail, ta.tests_failed AS ta_fail,
               tb.test_suites_failed AS tb_sfail, ta.test_suites_failed AS ta_sfail,
               tb.tests_total AS tb_total, ta.tests_total AS ta_total
        FROM experiments e
        LEFT JOIN study_smells ss ON e.study_smell_id = ss.id
        LEFT JOIN files f ON e.file_id = f.id
        LEFT JOIN repositories r ON f.repository_id = r.id
        LEFT JOIN test_results tb ON tb.experiment_id = e.id AND tb.phase = 'before'
        LEFT JOIN test_results ta ON ta.experiment_id = e.id AND ta.phase = 'after'
        WHERE ta.id IS NOT NULL
    """
    pairs = {}
    with open(OUT_DIR / "pairs.jsonl", "w") as fh:
        for row in conn.execute(query):
            d = dict(row)
            pairs[d["id"]] = d
            fh.write(json.dumps({
                "id": d["id"],
                "original_code": d["original_code"],
                "refactored_code": d["refactored_code"],
            }) + "\n")
    return pairs


def run_ast_analyzer():
    """Runs the Babel analyzer over the extracted pairs."""
    env = dict(os.environ, NODE_PATH=str(NODE_MODULES))
    subprocess.run(
        ["node", str(ANALYZER),
         str(OUT_DIR / "pairs.jsonl"), str(OUT_DIR / "metrics.jsonl")],
        check=True, env=env,
    )
    metrics = {}
    with open(OUT_DIR / "metrics.jsonl") as fh:
        for line in fh:
            m = json.loads(line)
            metrics[m["id"]] = m
    return metrics


def classify(pair, metric):
    """Applies the classification flags and the official test-state criterion."""
    before, after = metric["before"], metric["after"]
    flags = []
    passed = (
        (pair["ta_fail"] or 0) <= (pair["tb_fail"] or 0)
        and (pair["ta_sfail"] or 0) <= (pair["tb_sfail"] or 0)
        and (pair["tests_failed_type"] is None
             or pair["tests_failed_type"] not in {
                 "syntax_error", "runtime_error",
                 "module_resolution_error", "timeout", "unknown"})
    )
    exec_delta = None
    if pair["tb_total"] is not None and pair["ta_total"] is not None:
        exec_delta = pair["ta_total"] - pair["tb_total"]

    if after["assertions"] < before["assertions"]:
        flags.append("ASSERTION_LOSS")
    if after["assertions"] == 0 and before["assertions"] > 0:
        flags.append("ALL_ASSERTIONS_GONE")
    if after["tautological"] > before["tautological"]:
        flags.append("TAUTOLOGY_ADDED")
    if after["skips"] > before["skips"]:
        flags.append("TEST_DISABLED")
    if after["emptyTests"] > before["emptyTests"]:
        flags.append("TEST_EMPTIED")
    # Real execution is the arbiter: a snippet that loses it()/test() while
    # the suite executes MORE tests is a split/parameterization, not a removal
    if after["testCases"] < before["testCases"] and (exec_delta is None or exec_delta <= 0):
        flags.append("TEST_CASE_REMOVED")
    if after["commentedAssertions"] > before["commentedAssertions"]:
        flags.append("ASSERTION_COMMENTED_OUT")
    if before["expectAssertionsDecl"] and not after["expectAssertionsDecl"]:
        flags.append("EXPECT_ASSERTIONS_REMOVED")
    if pair["tb_total"] and pair["ta_total"] is not None and pair["ta_total"] < pair["tb_total"]:
        flags.append("EXECUTED_TESTS_DECREASED")
    return flags, passed


def is_strict_flagged(row):
    """Flagged outside the expected-reduction scenario.

    For Duplicate Assert the assertion reduction is the intended
    transformation itself, so ASSERTION_LOSS alone does not count there.
    """
    hits = set(row["flags"]) & STRICT_FLAGS
    if not hits:
        return False
    return not (row["smell"] == "Duplicate Assert" and hits == {"ASSERTION_LOSS"})


def write_validation_package(rows, pairs):
    """Exports the flagged cases for independent human rating."""
    flagged = sorted(
        (r for r in rows if r["passed"] and r["smell_removed"] and is_strict_flagged(r)),
        key=lambda r: r["id"],
    )
    out = OUT_DIR / "validation_package.csv"
    with open(out, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "experiment_id", "repo", "smell_type", "model", "flags", "category",
            "assertions_before", "assertions_after",
            "tests_exec_before", "tests_exec_after",
            "original_code", "refactored_code",
            "RATER1_weakened(yes/no/unsure)", "RATER2_weakened",
            "RATER3_weakened", "NOTES",
        ])
        for r in flagged:
            p = pairs[r["id"]]
            hits = set(r["flags"]) & STRICT_FLAGS
            category = "mechanical" if hits & MECHANICAL_FLAGS else "judgment-required"
            writer.writerow([
                r["id"], r["repo"], r["smell"], r["model"],
                ";".join(sorted(hits)), category,
                r["b_assert"], r["a_assert"], r["tb_total"], r["ta_total"],
                p["original_code"], p["refactored_code"], "", "", "", "",
            ])
    return len(flagged)


def main():
    if not RESEARCH_DB.exists():
        print(f"❌ Database not found at: {RESEARCH_DB}")
        sys.exit(1)
    if not NODE_MODULES.exists():
        print(f"❌ Analyzer dependencies not found at: {NODE_MODULES}")
        print("   Run npm install in llm-refactor-pipeline/src/llm_refactor/modules/detect_smells/get_method")
        sys.exit(1)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"📊 Analyzing database: {RESEARCH_DB}\n")
    pairs = extract_pairs()
    print(f"✅ Pairs extracted: {len(pairs)}")

    metrics = run_ast_analyzer()

    rows = []
    for pair_id, pair in pairs.items():
        flags, passed = classify(pair, metrics[pair_id])
        rows.append({
            "id": pair_id, "repo": pair["repo"], "smell": pair["smell"],
            "model": pair["model"], "prompt": pair["prompt"],
            "smell_removed": pair["smell_removed"], "passed": passed,
            "flags": flags,
            "b_assert": metrics[pair_id]["before"]["assertions"],
            "a_assert": metrics[pair_id]["after"]["assertions"],
            "tb_total": pair["tb_total"], "ta_total": pair["ta_total"],
        })
    with open(OUT_DIR / "classified.jsonl", "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")

    successes = [r for r in rows if r["passed"] and r["smell_removed"]]
    strict = [r for r in successes if is_strict_flagged(r)]
    broad = [r for r in successes if set(r["flags"]) & STRICT_FLAGS]
    loss = [r for r in rows if "ASSERTION_LOSS" in r["flags"]]
    loss_green = [r for r in loss if r["passed"]]
    taut_green = [r for r in rows if "TAUTOLOGY_ADDED" in r["flags"] and r["passed"]]
    n_validation = write_validation_package(rows, pairs)

    print(f"\n✅ Apparent successes (passing and smell removed): {len(successes)}")
    print(f"✅ Assertion loss: {len(loss)} total, {len(loss_green)} passing")
    print(f"✅ Always-true assertions added and passing: {len(taut_green)}")
    print(f"✅ Flagged (strict criterion): {len(strict)}"
          f" = {100 * len(strict) / len(successes):.1f}% of successes")
    print(f"✅ Flagged (broad criterion): {len(broad)}"
          f" = {100 * len(broad) / len(successes):.1f}%")
    print(f"✅ Flag distribution (strict set): "
          f"{Counter(f for r in strict for f in set(r['flags']) & STRICT_FLAGS)}")
    print(f"\n📋 Human validation package: {n_validation} cases at "
          f"{OUT_DIR / 'validation_package.csv'}")


if __name__ == "__main__":
    main()
