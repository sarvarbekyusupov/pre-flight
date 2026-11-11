# Review checklist

Only apply checks relevant to the change. Patterns alone do not establish bugs.

| Area | Evidence |
| --- | --- |
| Money | Units, rounding, negatives, zero denominators and missing rates |
| APIs | Validation, authentication, authorization, tenant isolation and compatibility |
| Async | Rejections, retry idempotency, cancellation, timeouts and cleanup |
| Database | Parameters, actual injection paths, indexes, transactions and rollout compatibility |
| Tests | Assertions for changed behavior, failure branches and boundaries |
| Security | Untrusted input reaching dangerous sinks, exposed credentials and sensitive logs |

Missing optional chaining and raw SQL are not inherently wrong. Migration locks depend on engine, version and operation: state missing context rather than asserting production impact.

Finding: `[HIGH | needs review] path:line — trigger → consequence. Evidence: caller/type/test. Proposed fix: ...`

Optional `.pre-flight/rules.md` examples (adapt; not company policy): monetary code uses the project's decimal/minor-unit convention; authenticated endpoints have authorization failure tests; migrations remain compatible with the previous application version.
