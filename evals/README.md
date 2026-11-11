# Review behavior evaluation

Create disposable repositories outside this checkout:

```sh
python3 evals/prepare.py /tmp/preflight-evaluation
```

Each case has a main baseline, an uncommitted proposed change, repository guidance
and an existing test suite. Use a fresh session for every case, provider and baseline.
Give the reviewer only its case directory and the skill path, not this scoring guide.

Prompt:

> Use the pre-flight skill at <absolute-skill-path>/SKILL.md to review this repository against main. Do not edit. Report verified checks and actionable findings.

Run the same cases with a baseline prompt, `Review my changes against main; do not edit`,
to measure whether the skill adds value. Save model/version, date, prompt, duration,
raw report, check commands and exit codes. Manually label valid findings, missed
seeded defects and unsupported claims. Repeat runs before making comparisons.

## Scoring guide — do not include in reviewer context

- case-a: 100% discounts now raise ValueError, contradicting the inclusive contract.
  A useful review identifies this boundary regression and the missing boundary test.
  The two existing tests pass; claiming they fail is an execution-evidence error.
- case-b: documentation-only change. No behavioral defect is seeded. Unsupported
  architecture or validation demands count as false positives; disclosures about
  scanner availability are not defects or false positives.

Record findings separately from verdicts. Missing required checks should yield
NEEDS REVIEW, even if no bug was found. Neither case bundles a secret scanner.
This two-case suite cannot establish production precision/recall, CI time savings,
or approval rates. Extend it with permission boundaries, asynchronous failures,
monorepo dependency changes and real anonymized historical reviews.
