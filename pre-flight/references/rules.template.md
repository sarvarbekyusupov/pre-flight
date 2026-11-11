# Pre-Flight Repository Rules Template
<!-- Copy to .pre-flight/rules.md in your repository root and adapt to your project standards -->

## 1. Architectural Integrity & Decoupling
- **No Domain Leaks in Generic Layers**: Shared utilities, orchestrators, and generic mappers must remain agnostic. They must never hardcode domain-specific concepts or keys.
- **Explicit Interfaces**: Domain-specific behaviors must be declared via explicit interfaces, factory contracts, or configuration injected into generic pipelines.
- **No Magic Strings**: Use exported constants or enums for business-critical identifiers, event names, and status codes.

## 2. Test Integrity & Failure Path Coverage
- **No Vacuous Tests**: A passing test is not enough. Verify that test fixtures actually contain the necessary data to trigger the logic under test (e.g., if testing a merge algorithm, the fixture must contain mergeable inputs).
- **Semantic Test Organization**: Place test cases in their correct conceptual suite or `describe` block.
- **Agnostic Core Fixtures**: Core service and domain tests should test behavior generically rather than coupling assertions to third-party integrations, unless explicitly testing the adapter.
- **Timezone Consistency**: Run test suites under `TZ=UTC` to match CI runners and prevent time-sensitive assertion failures.

## 3. Commit & Merge Request Hygiene
- **Branch Naming**: Branch names should follow repository conventions (e.g., `feature/<TICKET>`, `bugfix/<TICKET>`, or short kebab-case descriptions).
- **Commit Messages**: Each commit subject must follow the project standard (e.g., Ticket prefix `<TICKET>. <Subject>` or Conventional Commits `feat: ...`, `fix: ...`).
- No work-in-progress commit messages (`wip`, `fixup!`, `squash!`, `temp`, `backup`). Squash or reword locally before review.

## 4. Monorepo Verification & Scoping
- In large monorepos, use targeted testing (e.g., `pnpm --filter <app> test`) to ensure fast feedback, but remain aware that changing core libraries may impact downstream apps not explicitly listed.
