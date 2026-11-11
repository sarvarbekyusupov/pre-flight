# Pre-Flight Repository Rules Template
<!-- Copy to .pre-flight/rules.md in your repository root and adapt to your project standards -->

## 1. Architectural Decoupling & Agnostic Layers
- **No Hardcoded Domain Keys in Generic Layers**: Shared utilities, orchestrators, and generic mappers must remain agnostic. They must never hardcode dimension-, provider-, or domain-specific keys (e.g., hardcoding `'ancestors'` in a generic mapper).
- **Explicit Factory/Provider Contracts**: When a generic mapper or pipeline needs to handle domain-specific behaviors (such as ID prefixing or transformations), the domain factory/provider must declare them via its interface (e.g., `idAttributeKeys`, `decorators`, or feature flags).
- **No Magic Strings**: All entity attribute keys, event names, and status codes must use exported constants or enum members (e.g., `ANCESTORS_ATTRIBUTE_KEY`).

## 2. Test Integrity & Failure Path Coverage
- **No Vacuous Tests**: A passing test is not enough. Verify that test fixtures actually trigger the logic under test. For example, when testing hierarchical merging of traits or attributes, fixtures must supply both parent traits and child attributes to force the merge algorithm to execute.
- **Semantic Test Organization**: Place test cases in their correct conceptual suite or `describe` block (e.g., within `hierarchical structure` rather than under an unrelated decorator or wiring suite).
- **Agnostic Core Fixtures**: Core service and domain tests should test behavior generically (`Type One`, `parent-1`, `child-1`) rather than coupling assertions to third-party or producer-specific identifiers unless explicitly testing that integration adapter.
- **Timezone Consistency**: Run test suites under `TZ=UTC` to match CI runners and prevent time-sensitive assertion failures.

## 3. Commit & Merge Request Hygiene
- **Branch Naming**: Branch names must follow repository conventions: `feature/<TICKET>`, `bugfix/<TICKET>`, or kebab-case short subjects.
- **Commit Messages**: Each commit subject must follow the project standard:
  - Ticket prefix: `<TICKET>. <Subject>` (e.g., `OB-213. Expose full ancestor chain in gam-geo attributes.ancestors`) or Conventional Commits (`feat: ...`, `fix: ...`).
  - No work-in-progress commit messages (`wip`, `fixup!`, `squash!`, `temp`, `backup`, `review fixes`). Squash or reword locally before opening an MR.
- **Repository MR Validation**: If the repository includes an MR check script (such as `scripts/release/check-mr.sh`), run it prior to pushing.

## 4. Monorepo Verification & Scoping
- In large monorepos, use the `affected_modules` detected by pre-flight to run scoped tests and typechecks (e.g., `pnpm --filter <app> test`) before running full-suite checks.
