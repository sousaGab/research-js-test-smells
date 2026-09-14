"""
Before/after assertion analysis over all refactoring experiments.

For every experiment with an after-phase execution, the module parses the
original and refactored snippets with Babel (via analyze_semantics.js),
counts and classifies assertions, and flags weakening patterns:

  ASSERTION_LOSS            fewer assertions after refactoring
  ALL_ASSERTIONS_GONE       every assertion removed
  TAUTOLOGY_ADDED           an always-true assertion was introduced
  TEST_DISABLED             a test was skipped or x-prefixed
  TEST_EMPTIED              a test body became empty
  TEST_CASE_REMOVED         a test case disappeared (execution as arbiter)
  ASSERTION_COMMENTED_OUT   an assertion was moved into a comment
  EXPECT_ASSERTIONS_REMOVED an expect.assertions() declaration was dropped
  EXECUTED_TESTS_DECREASED  the executed-test count shrank

Flags are cross-referenced with the official test-state criterion (no new
failing tests or suites, no execution-level error) to quantify how many
apparently successful refactorings weaken the tests' verification logic.

Outputs (written to research_data/assertion_analysis/ by default):
  pairs.jsonl, metrics.jsonl, classified.jsonl, validation_package.csv
"""

import csv
import json
import os
import shutil
import subprocess
from collections import Counter
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..database.connection import DEFAULT_DB_PATH

console = Console()

MODULE_DIR = Path(__file__).parent
ANALYZER_JS = MODULE_DIR / "analyze_semantics.js"
NODE_MODULES = MODULE_DIR.parent / "detect_smells" / "get_method" / "node_modules"

ERROR_TYPES = {"syntax_error", "runtime_error", "module_resolution_error",
               "timeout", "unknown"}
STRICT_FLAGS = {"ASSERTION_LOSS", "ALL_ASSERTIONS_GONE", "TAUTOLOGY_ADDED",
                "TEST_DISABLED", "TEST_EMPTIED", "TEST_CASE_REMOVED",
                "ASSERTION_COMMENTED_OUT", "EXPECT_ASSERTIONS_REMOVED",
                "EXECUTED_TESTS_DECREASED"}
MECHANICAL_FLAGS = {"TAUTOLOGY_ADDED", "EXECUTED_TESTS_DECREASED",
                    "TEST_DISABLED", "TEST_EMPTIED",
                    "ASSERTION_COMMENTED_OUT", "EXPECT_ASSERTIONS_REMOVED"}

HELP_TEXT = """Assertion Analysis Commands
============================================================
  analyze_assertions                 Run the full before/after analysis
  analyze_assertions --examples=N    Also print N flagged examples
  analyze_assertions --outdir=PATH   Write outputs to a custom directory
  analyze_assertions help            Show this help

The analysis is read-only with respect to the database. Outputs:
  pairs.jsonl               the 3,600 before/after snippet pairs
  metrics.jsonl             per-pair AST metrics
  classified.jsonl          per-pair flags and execution context
  validation_package.csv    flagged successes, ready for human rating
"""


class AssertionAnalysisModule:
    """Runs the before/after assertion analysis end to end."""

    def __init__(self, db_path=None, out_dir=None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        default_out = self.db_path.parent / "assertion_analysis"
        self.out_dir = Path(out_dir) if out_dir else default_out

    # ------------------------------------------------------------------
    # environment checks
    # ------------------------------------------------------------------
    def check_environment(self):
        problems = []
        if not self.db_path.exists():
            problems.append(f"database not found at {self.db_path}")
        if shutil.which("node") is None:
            problems.append("node is not available on PATH")
        if not ANALYZER_JS.exists():
            problems.append(f"analyzer script missing at {ANALYZER_JS}")
        if not (NODE_MODULES / "@babel" / "parser").exists():
            problems.append(
                "@babel/parser not installed for the analyzer; run "
                f"'npm install' in {NODE_MODULES.parent}"
            )
        return problems

    # ------------------------------------------------------------------
    # pipeline stages
    # ------------------------------------------------------------------
    def extract_pairs(self):
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        query = """
            SELECT e.id, e.ai_model_version model, e.prompting_approach prompt,
                   e.smell_removed, e.tests_failed_type,
                   COALESCE(ss.smell_type, '?') smell, r.name repo,
                   e.original_code, e.refactored_code,
                   tb.tests_failed tb_fail, ta.tests_failed ta_fail,
                   tb.test_suites_failed tb_sfail, ta.test_suites_failed ta_sfail,
                   tb.tests_total tb_total, ta.tests_total ta_total
            FROM experiments e
            LEFT JOIN study_smells ss ON e.study_smell_id = ss.id
            LEFT JOIN files f ON e.file_id = f.id
            LEFT JOIN repositories r ON f.repository_id = r.id
            LEFT JOIN test_results tb
                   ON tb.experiment_id = e.id AND tb.phase = 'before'
            LEFT JOIN test_results ta
                   ON ta.experiment_id = e.id AND ta.phase = 'after'
            WHERE ta.id IS NOT NULL
        """
        pairs = {}
        with open(self.out_dir / "pairs.jsonl", "w") as fh:
            for row in conn.execute(query):
                item = dict(row)
                pairs[item["id"]] = item
                fh.write(json.dumps({
                    "id": item["id"],
                    "original_code": item["original_code"],
                    "refactored_code": item["refactored_code"],
                }) + "\n")
        conn.close()
        return pairs

    def run_ast_analyzer(self):
        env = dict(os.environ, NODE_PATH=str(NODE_MODULES))
        result = subprocess.run(
            ["node", str(ANALYZER_JS),
             str(self.out_dir / "pairs.jsonl"),
             str(self.out_dir / "metrics.jsonl")],
            capture_output=True, text=True, timeout=600, env=env,
        )
        if result.returncode != 0:
            raise RuntimeError(f"AST analyzer failed: {result.stderr[:500]}")
        metrics = {}
        with open(self.out_dir / "metrics.jsonl") as fh:
            for line in fh:
                item = json.loads(line)
                metrics[item["id"]] = item
        return metrics

    @staticmethod
    def classify(pair, metric):
        before, after = metric["before"], metric["after"]
        flags = []
        passed = (
            (pair["ta_fail"] or 0) <= (pair["tb_fail"] or 0)
            and (pair["ta_sfail"] or 0) <= (pair["tb_sfail"] or 0)
            and (pair["tests_failed_type"] is None
                 or pair["tests_failed_type"] not in ERROR_TYPES)
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
        if (after["testCases"] < before["testCases"]
                and (exec_delta is None or exec_delta <= 0)):
            flags.append("TEST_CASE_REMOVED")
        if after["commentedAssertions"] > before["commentedAssertions"]:
            flags.append("ASSERTION_COMMENTED_OUT")
        if before["expectAssertionsDecl"] and not after["expectAssertionsDecl"]:
            flags.append("EXPECT_ASSERTIONS_REMOVED")
        if (pair["tb_total"] and pair["ta_total"] is not None
                and pair["ta_total"] < pair["tb_total"]):
            flags.append("EXECUTED_TESTS_DECREASED")
        return flags, passed

    def run(self, examples=0):
        self.out_dir.mkdir(parents=True, exist_ok=True)

        console.print("[cyan]1/4[/cyan] Extracting before/after pairs...")
        pairs = self.extract_pairs()

        console.print(f"[cyan]2/4[/cyan] Parsing {len(pairs)} pairs with Babel...")
        metrics = self.run_ast_analyzer()

        console.print("[cyan]3/4[/cyan] Classifying weakening patterns...")
        rows = []
        for exp_id, pair in pairs.items():
            metric = metrics[exp_id]
            flags, passed = self.classify(pair, metric)
            rows.append({
                "id": exp_id, "repo": pair["repo"], "smell": pair["smell"],
                "model": pair["model"], "prompt": pair["prompt"],
                "smell_removed": pair["smell_removed"], "passed": passed,
                "flags": flags,
                "b_assert": metric["before"]["assertions"],
                "a_assert": metric["after"]["assertions"],
                "tb_total": pair["tb_total"], "ta_total": pair["ta_total"],
                "taut_ex": metric["after"].get("tautologyExamples", []),
            })
        with open(self.out_dir / "classified.jsonl", "w") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")

        console.print("[cyan]4/4[/cyan] Building summary and validation package...")
        return self.summarize(pairs, rows, examples)

    # ------------------------------------------------------------------
    # reporting
    # ------------------------------------------------------------------
    def summarize(self, pairs, rows, examples):
        successes = [r for r in rows if r["passed"] and r["smell_removed"]]
        broad = [r for r in successes if set(r["flags"]) & STRICT_FLAGS]
        strict = [
            r for r in broad
            if not (r["smell"] == "Duplicate Assert"
                    and set(r["flags"]) & STRICT_FLAGS == {"ASSERTION_LOSS"})
        ]
        mechanical = [r for r in strict if set(r["flags"]) & MECHANICAL_FLAGS]

        self._write_validation_package(pairs, strict)

        table = Table(title="Weakening flags among flagged successes")
        table.add_column("Flag")
        table.add_column("Count", justify="right")
        counts = Counter(f for r in strict for f in set(r["flags"]) & STRICT_FLAGS)
        for flag, count in counts.most_common():
            table.add_row(flag, str(count))

        pct = 100 * len(strict) / len(successes) if successes else 0.0
        pct_broad = 100 * len(broad) / len(successes) if successes else 0.0
        console.print(Panel(
            f"Experiments analyzed: [bold]{len(rows)}[/bold]\n"
            f"Apparent successes (state stable and smell removed): "
            f"[bold]{len(successes)}[/bold]\n"
            f"Flagged, strict (excludes expected Duplicate Assert loss): "
            f"[bold]{len(strict)} = {pct:.1f}%[/bold]\n"
            f"  mechanically verifiable: {len(mechanical)} · "
            f"judgment-required: {len(strict) - len(mechanical)}\n"
            f"Flagged, broad: {len(broad)} = {pct_broad:.1f}%",
            title="Before/After Assertion Analysis", border_style="cyan",
        ))
        console.print(table)

        if examples > 0:
            shown = 0
            for row in strict:
                if row["taut_ex"] and shown < examples:
                    console.print(
                        f"[yellow]exp {row['id']}[/yellow] "
                        f"{row['repo']}/{row['smell']} ({row['model']}): "
                        f"{row['taut_ex'][0]}"
                    )
                    shown += 1

        return (
            f"Done. {len(strict)} of {len(successes)} apparent successes "
            f"({pct:.1f}%) carry a weakening flag. "
            f"Outputs in {self.out_dir}"
        )

    def _write_validation_package(self, pairs, strict):
        path = self.out_dir / "validation_package.csv"
        with open(path, "w", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow([
                "experiment_id", "repo", "smell_type", "model", "flags",
                "category", "assertions_before", "assertions_after",
                "tests_exec_before", "tests_exec_after",
                "original_code", "refactored_code",
                "RATER1_weakened(yes/no/unsure)", "RATER2_weakened",
                "RATER3_weakened", "NOTES",
            ])
            for row in sorted(strict, key=lambda r: r["id"]):
                pair = pairs[row["id"]]
                category = ("mechanical"
                            if set(row["flags"]) & MECHANICAL_FLAGS
                            else "judgment-required")
                writer.writerow([
                    row["id"], row["repo"], row["smell"], row["model"],
                    ";".join(sorted(set(row["flags"]) & STRICT_FLAGS)),
                    category, row["b_assert"], row["a_assert"],
                    row["tb_total"], row["ta_total"],
                    pair["original_code"], pair["refactored_code"],
                    "", "", "", "",
                ])


def execute(args: str = "") -> str:
    """Entry point for the analyze_assertions CLI command."""
    args = (args or "").strip()
    if args.lower() in {"help", "--help", "-h"}:
        return HELP_TEXT

    out_dir = None
    examples = 0
    for token in args.split():
        if token.startswith("--outdir="):
            out_dir = token.split("=", 1)[1]
        elif token.startswith("--examples="):
            try:
                examples = int(token.split("=", 1)[1])
            except ValueError:
                return f"Invalid --examples value in '{token}'. See 'analyze_assertions help'."
        else:
            return f"Unknown argument '{token}'. See 'analyze_assertions help'."

    module = AssertionAnalysisModule(out_dir=out_dir)
    problems = module.check_environment()
    if problems:
        lines = "\n".join(f"  ✗ {p}" for p in problems)
        return f"Cannot run the assertion analysis:\n{lines}"

    return module.run(examples=examples)
