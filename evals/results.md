# Smoke evaluation — 2026-11-11

Method: two fresh isolated agent sessions using the revised SKILL.md and one
synthetic repository each. Reviewers were given the skill path and case directory,
not the scoring guide or expected findings. This evaluated the workflow through
agents in this session; it did not validate native skill discovery in each CLI.
Standalone Codex CLI attempts were blocked by local app-server initialization
permissions. Claude Code and Gemini CLI were not run.

| Case | Verified checks | Review outcome |
| --- | --- | --- |
| A: boundary regression | Existing 2-test suite passed; targeted 100% discount assertion failed with ValueError | Identified inclusive-contract regression at pricing.py:2 and missing boundary test; BLOCKED |
| B: docstring only | Existing 2-test suite passed | No actionable findings; READY WITHIN CHECKED SCOPE |

Both reports disclosed scanner unavailability and worktree execution scope.
One seeded defect was detected; no unsupported defect was reported for the clean
case. These are two observations, not an accuracy estimate. No baseline-prompt
comparison, repeated sampling, native three-CLI evaluation or historical-MR
benchmark has been completed. Use prepare.py and README.md to reproduce and expand.

Regression suite: 23 tests passed locally, including partial-copy failure,
second-destination swap failure, symlink rollback, preservation of pre-existing
backups, retained recovery data after restoration failure, explicit commit policy,
and breaking-change commit messages. Python 3.9 syntax parsing passed; CI separately
runs Python 3.9/3.12 on Linux/macOS. A passing local result does not imply CI success.
