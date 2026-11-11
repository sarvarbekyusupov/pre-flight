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

The installer refuses existing destinations rather than replacing customizations.
It does not alter global CLI settings, install packages, enable hooks or contact a server.
Commit installed files to your team repository if you want teammates to use them.

## Example requests

- “Use pre-flight to review all my changes against origin/main. Do not edit.”
- “Use pre-flight on staged changes only.”
- “Use pre-flight, then apply the lint fix and add a regression test for the confirmed bug.”

The skill gathers change metadata, reads relevant code and team conventions,
runs inspected project checks, and reports verified failures separately from
AI concerns. Fixes are proposed by default and applied when requested.

## Standalone helper

```sh
python3 pre-flight/scripts/preflight.py collect --repo /path/to/project --base origin/main
python3 pre-flight/scripts/preflight.py collect --repo /path/to/project --scope staged
python3 pre-flight/scripts/preflight.py check --repo /path/to/project --name types --timeout 120 -- npm run typecheck
```

Inspect repository scripts before running them. The helper does not determine
whether an arbitrary command is safe. It never invokes a shell itself, but
commands such as npm can invoke lifecycle scripts and other programs.

Scopes: `all` (default), `branch`, `staged`, `working`. Collection includes file
names and metadata only, avoiding automatic ingestion of untracked secrets.
Base discovery tries origin/HEAD, origin/main, origin/master, main, master;
pass `--base` for develop or other branches. Local refs can be stale; no fetch is
performed. Missing HEAD/base produces an explicit error. Branch and index
review do not change the fact that check commands execute on the current worktree.

JSON check statuses: PASS, FAIL, TIMEOUT, ERROR. Output is capped at 16 KB;
truncation is disclosed. Exit codes: 0 for successful collection/passed check,
1 for conflicts/failed check, 2 for invalid input or collection errors.
Timeouts terminate the process group on macOS/Linux; Windows only guarantees
termination of the immediate process. Output is raw tool output and may contain
sensitive values: do not share it without inspection. The AI workflow must redact
credentials in its report. No secret scanner is bundled; missing scanning is
reported as SKIPPED, never clean.

## Team rules

Optionally add `.pre-flight/rules.md` to the target repository. Include concrete
rules, their scope and rationale. Example: “New authenticated campaign endpoints
must test cross-tenant access denial.” No DanAds policies are assumed.

## Validation and limits

Run `python3 -m unittest discover -s tests -v` from this folder.
The tests cover change layers, unusual filenames, staged/worktree disagreement,
missing bases, deletions/ignored files, command statuses, timeouts, output limits,
literal argv handling and installation collision protection.

This is a tested helper plus an agent workflow, not a standalone AI review engine.
The host CLI provides the model and editing tools. End-to-end review quality in
a real DanAds repository has not been benchmarked. Model processing can be remote
according to your CLI/account settings. No approval prediction score is fabricated.
Checks are sequential; dependencies and test selection are handled by the agent.

## Format references

- Claude Code: https://code.claude.com/docs/en/skills
- Codex: https://developers.openai.com/codex/skills
- Gemini CLI: https://geminicli.com/docs/cli/skills/
