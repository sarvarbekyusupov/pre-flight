# Pre-Flight Repository Rules Template

Adapt these examples to your project. They are not enforced policy until adopted.

## Required checks
- List actual CI jobs, package scopes, commands, runtime versions and required services.
- Describe checks that cannot run locally and how their results will be verified.

## Architecture
- Document existing dependency boundaries and compatibility contracts.
- Report concrete violations; do not require abstractions solely for style.

## Testing
- Fixtures must exercise the changed behavior and assertions must detect regressions.
- Cover meaningful boundaries and failure paths. Match the CI timezone when required.

## Commit hygiene (optional)
- Default format enforcement is off; WIP detection remains advisory.
- Adopt `--commit-policy conventional` or `--commit-policy ticket-or-conventional` only if this repository requires it.
- Rewrite history only when explicitly authorized; preserve unrelated staged changes.

## Monorepos
- Changed folders are hints, not a dependency graph. Include downstream consumers
  and root configuration changes when selecting verification.
