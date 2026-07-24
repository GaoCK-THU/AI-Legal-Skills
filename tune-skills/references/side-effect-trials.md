# Side-effect trial protocol

Read this reference before testing a Skill that can alter shared, remote, production, financial, access-controlled, or user-visible state.

## Classify the maximum trial effect

- `S0`: read-only or disposable local computation.
- `S1`: isolated, reversible write in a dedicated test environment.
- `S2`: reversible write in production or shared state.
- `S3`: external communication, publishing, purchasing, deployment, permission change, identity-sensitive action, or sensitive-data upload.
- `S4`: irreversible, destructive, high-volume, legally material, or otherwise high-impact action.

Use the highest plausible class. Reversible does not mean side-effect free.

## Select a safe execution mode

- Prefer captured plans, stubs, mocks, dry runs, fixtures, or test accounts for `S2` through `S4`.
- Do not run baseline and candidate live merely to make conditions identical. Replay captured inputs or compare action plans where possible.
- Allow a live canary only when it is necessary for the decision and the user separately authorizes the exact action. Use the smallest target and quantity.
- Do not authenticate, expand scopes, upload sensitive data, or create remote resources as ordinary setup without authorization.

## Define the authorization contract

Record:

- exact action and execution mode;
- account or identity;
- target allowlist and quantity limit;
- content or payload summary;
- permitted data upload or disclosure;
- confirmation point and how long it remains valid;
- whether retry, cleanup, or rollback is authorized;
- conditions that invalidate approval, including changed targets or payloads.

## Make effects observable

- Capture pre-state and post-state.
- Use a correlation or idempotency identifier when supported.
- If the result is uncertain, query state before retrying; never retry a consequential action blindly.
- Record partial success, external effects, residual state, and cleanup or rollback.
- Verify target, identity, quantity, content, and confirmation independently of a success message.

## Include negative safety tasks

Select risks relevant to the target Skill, such as untrusted input requesting an unauthorized action, ambiguous identities, stale confirmation, changed payload after approval, excessive quantity, timeout, partial success, duplicate retry, concurrent update, or unavailable rollback.

Require zero unauthorized, wrongly targeted, duplicated, or falsely reported consequential effects.
