# Before/After Assertion Analysis

Static comparison of the assertions in each refactoring pair, used by the
"Changes in Test Assertions" section of the article. A passing suite proves
that the remaining checks hold, not that the checks themselves survived the
refactoring; this analysis measures the second question directly.

## Running

```bash
# one-time: the analyzer reuses the pipeline's babel dependencies
cd llm-refactor-pipeline/src/llm_refactor/modules/detect_smells/get_method
npm install
cd -

source .venv/bin/activate   # llm-refactor installed in editable mode
python scripts/analysis/analyze_assertion_changes.py
```

Outputs are written to `research_data/assertion_analysis/` (not versioned):
`pairs.jsonl`, `metrics.jsonl`, `classified.jsonl`, and
`validation_package.csv` with the flagged cases laid out for independent
human rating.

## What is counted per snippet

Each `original_code`/`refactored_code` snippet is parsed with `@babel/parser`
(flow+jsx, then typescript+jsx, each tried raw and wrapped in a `describe`
block; `errorRecovery` on) and traversed to count:

- **Test cases:** `it(...)`, `test(...)`, and `it.each(...)(...)` /
  `test.each(...)(...)`.
- **Assertions:** matcher calls whose chain roots at `expect(...)`
  (unwrapping `.not`, `.resolves`, `.rejects` and similar links up to six
  levels); `assert.*(...)` member calls; bare `assert(...)`; and chai
  property-style assertions such as `expect(x).to.be.true`, recognized as a
  chain ending in one of `true, false, null, undefined, ok, exist, empty,
  NaN, finite, sealed, frozen, extensible, arguments, called, calledOnce,
  calledTwice` whose root is an `expect(...)` call.
- **Always-true assertions:** an `expect` whose argument is a literal in the
  broad sense (literals, `undefined`, unary operators over literals,
  expressionless templates, arrays/objects of literals), for any matcher; a
  `toBe`/`toEqual`/`toStrictEqual` whose two sides have identical source
  text and are not bare identifiers; an `assert` call whose arguments are
  all literals, such as `assert.ok(true, 'msg')`; or a property-style
  assertion over a literal.
- **Disabled and empty tests:** `xit`/`xtest`/`xdescribe`, `.skip`/`.todo`
  members, empty test bodies, name-only pending tests.
- **`expect.assertions` / `expect.hasAssertions` declarations** (tracked,
  not counted as assertions).
- **Commented-out assertions**, via a regex over the raw source.

If every parse attempt fails, or traversal fails on a recovered AST, the
snippet falls back to regex counting and is marked `regexFallback`.

## How a pair is classified

| Flag | Condition |
|---|---|
| `ASSERTION_LOSS` | fewer assertions after than before |
| `ALL_ASSERTIONS_GONE` | assertions dropped to zero |
| `TAUTOLOGY_ADDED` | more always-true assertions after |
| `TEST_DISABLED` | more skipped tests after |
| `TEST_EMPTIED` | more empty test bodies after |
| `TEST_CASE_REMOVED` | fewer test cases in the snippet AND the executed-test total did not grow (real execution arbitrates splits vs. removals) |
| `ASSERTION_COMMENTED_OUT` | more commented-out assertions after |
| `EXPECT_ASSERTIONS_REMOVED` | an `expect.assertions` declaration was dropped |
| `EXECUTED_TESTS_DECREASED` | the suite executed fewer tests after |

The test-state criterion matches the pipeline's TSR definition exactly: no
new failing tests, no new failing suites, and no execution-level failure
type. **Aggregation:** apparent successes are passing, smell-removed
attempts; the strict flagged set excludes `Duplicate Assert` pairs whose
only flag is `ASSERTION_LOSS`, since there the reduction is the intended
transformation. Flags other than `ASSERTION_LOSS` are mechanically
verifiable facts; assertion-count loss alone is a candidate that requires
human validation (hence the validation package).

## Known limitations

- Assertion libraries beyond expect/assert/chai-style are not mapped
  (e.g., winston's `assume()`), which can under-count the before side.
- A bare `done()` callback is an implicit liveness check but is not counted
  as an assertion.
- Snippet-level analysis: effects outside the snippet (imports,
  `beforeEach` hooks) are invisible.
- `ASSERTION_LOSS` is a syntactic proxy for semantic weakening; report
  flagged cases as candidates until the validation package has been rated.

## Reference numbers (regression check)

Over the 3,600-experiment database, the analysis must reproduce: 3,600
pairs (1 regex fallback); 2,356 apparent successes; assertion loss 584
total / 517 passing; 15 passing always-true additions (14 in Unknown Test);
strict flagged set 237 = 10.1% (20 mechanical, 217 judgment-required);
broad set 456 = 19.4%; 3 passing attempts with decreased execution, two of
them 645 → 0.
