# pre-flight

A shared before-push review skill for Claude Code, Codex and Gemini CLI.
It combines actual repository checks with evidence-backed AI review concerns.
It does not guarantee CI success or MR approval.

## Install into your project

Requires Python 3.9+ and Git. Download the source, then install into your project:

```sh
git clone https://github.com/sarvarbekyusupov/pre-flight.git
cd pre-flight
python3 install.py --repo /absolute/path/to/your-project
```

Or install with default team rules template (`.pre-flight/rules.md`):

```sh
python3 install.py --repo /absolute/path/to/your-project --init-rules
```

To update an existing installation, use the `--force` flag:

```sh
python3 install.py --repo /absolute/path/to/your-project --force
```

Or install for one CLI:

```sh
python3 install.py --repo /absolute/path/to/your-project --agent claude
python3 install.py --repo /absolute/path/to/your-project --agent codex
python3 install.py --repo /absolute/path/to/your-project --agent gemini
```

The installer copies the same self-contained skill into:

| CLI | Project destination | Invocation inside CLI |
| --- | --- | --- |
| Claude Code | `.claude/skills/pre-flight/` | `/pre-flight` |
| Codex | `.agents/skills/pre-flight/` | `$pre-flight` |
| Gemini CLI | `.gemini/skills/pre-flight/` | `Use the pre-flight skill to review my changes before I push.` |

Open the CLI in the target project. Use its skill list/reload mechanism if the
new skill is not yet visible. Gemini can also discover `.agents/skills`; the
identical Gemini-specific copy provides a standalone installation. Never assume
Gemini exposes `/pre-flight` as a custom command.

The installer refuses existing destinations rather than replacing customizations, unless `--force` is provided.
It does not alter global CLI settings, install packages, enable hooks or contact a server.
Commit installed files to your team repository if you want teammates to use them.

## Example requests

- “Use pre-flight to review all my changes against origin/dev. Do not edit.”
- “Use pre-flight on staged changes only.”
- “Use pre-flight, then apply the lint fix and add a regression test for the confirmed bug.”

The skill gathers change metadata, reads relevant code and team conventions,
runs inspected project checks, and reports verified failures separately from
AI concerns. Fixes are proposed by default and applied when requested.

## Standalone helper

```sh
python3 pre-flight/scripts/preflight.py collect --repo /path/to/project --base origin/dev
python3 pre-flight/scripts/preflight.py collect --repo /path/to/project --scope staged
python3 pre-flight/scripts/preflight.py collect --repo /path/to/project --rules test --rules architecture
python3 pre-flight/scripts/preflight.py check --repo /path/to/project --name types --timeout 120 -- npm run typecheck
python3 pre-flight/scripts/preflight.py check --repo /path/to/project --name test --env TZ=UTC -- pnpm test
```

Inspect repository scripts before running them. The helper does not determine
whether an arbitrary command is safe. It never invokes a shell itself, but
commands such as npm can invoke lifecycle scripts and other programs.

Scopes: `all` (default), `branch`, `staged`, `working`. Collection includes file
names and metadata only, avoiding automatic ingestion of untracked secrets.
Base discovery tries origin/HEAD, origin/main, origin/dev, origin/develop, origin/master,
main, dev, develop, master; pass `--base` for other branches. Local refs can be stale;
no fetch is performed. Missing HEAD/base produces an explicit error. Branch and index
review do not change the fact that check commands execute on the current worktree.

Metadata collection also surfaces:
- `branch`: current active branch name
- `commits`: list of commits between merge-base and HEAD
- `commit_hygiene_warnings`: automated warnings for WIP/fixup/squash subjects and branch ticket prefix mismatches
- `affected_modules`: heuristic list of affected apps, packages, or top-level modules in monorepos. Treat as a starting point for test selection, not a definitive dependency graph (modifying a shared core library may affect downstream modules not explicitly listed).
- `active_rules`: selectively filters `.pre-flight/rules.md` based on `--rules` substring matches (e.g. `--rules testing` matches `## Testing Rules`)

JSON check statuses: PASS, FAIL, TIMEOUT, ERROR. Output is capped at 16 KB;
truncation is disclosed. Exit codes: 0 for successful collection/passed check,
1 for conflicts/failed check, 2 for invalid input or collection errors.
Timeouts terminate the process group on macOS/Linux; Windows only guarantees
termination of the immediate process. Output is raw tool output and may contain
sensitive values: do not share it without inspection. The AI workflow must redact
credentials in its report. No secret scanner is bundled; missing scanning is
reported as SKIPPED, never clean.

## Team rules

Add `.pre-flight/rules.md` to the target repository (scaffolded automatically with
`--init-rules` from `pre-flight/references/rules.template.md`). Include concrete
rules, architectural boundaries, test non-vacuity rules, and MR conventions.

## Validation and limits

Run `python3 -m unittest discover -s tests -v` from this folder.
The tests cover change layers, unusual filenames, staged/worktree disagreement,
missing bases, deletions/ignored files, command statuses, timeouts, output limits,
literal argv handling and installation collision protection.

This is a tested helper plus an agent workflow, not a standalone AI review engine.
The host CLI provides the model and editing tools. End-to-end review quality in
a real repository has not been benchmarked. Model processing can be remote
according to your CLI/account settings. No approval prediction score is fabricated.
Checks are sequential; dependencies and test selection are handled by the agent.

## Format references

- Claude Code: https://code.claude.com/docs/en/skills
- Codex: https://developers.openai.com/codex/skills
- Gemini CLI: https://geminicli.com/docs/cli/skills/
