# Review checklist

Only apply checks relevant to the change. Patterns alone do not establish bugs.

| Area | Evidence |
| --- | --- |
| Architecture | Layer leaks, hardcoded domain keys in agnostic mappers/utilities, missing interface declarations, magic strings |
| Tests | Assertions for changed behavior, failure branches, non-vacuous fixtures, and boundaries |
| APIs | Validation, authentication, authorization, tenant isolation and compatibility |
| Money | Units, rounding, negatives, zero denominators and missing rates |
| Async | Rejections, retry idempotency, cancellation, timeouts and cleanup |
| Database | Parameters, actual injection paths, indexes, transactions and rollout compatibility |
| Security | Untrusted input reaching dangerous sinks, exposed credentials and sensitive logs |
| Git Hygiene | WIP/fixup commits, branch naming conformance, and ticket prefix format |

Missing optional chaining and raw SQL are not inherently wrong. Migration locks depend on engine, version and operation: state missing context rather than asserting production impact.

### Specific Review Scrutiny:
- **Test Vacuity**: Scrutinize new or updated tests. Does the fixture supply the data needed to actually execute the changed branch? (e.g. if testing trait merging, parent traits must exist in the fixture). If a test passes even when the production logic is commented out, it is vacuous.
- **Architectural Leaks**: Ensure generic layers (mappers, shared pipeline services) do not hardcode dimension- or provider-specific constants. The provider or factory should declare them via interface contracts.
- **Commit Quality**: Check if any branch commit has a WIP/fixup/squash message or lacks the required ticket prefix.

Finding: `[HIGH | needs review] path:line — trigger → consequence. Evidence: caller/type/test. Proposed fix: ...`

Optional `.pre-flight/rules.md` examples (adapt; not company policy): monetary code uses the project's decimal/minor-unit convention; authenticated endpoints have authorization failure tests; migrations remain compatible with the previous application version.
