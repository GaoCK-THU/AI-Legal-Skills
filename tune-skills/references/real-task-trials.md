# Real-task trials

Use realistic task runs to determine whether a candidate Skill works on its intended tasks and meaningful variations.

## Build a small task portfolio

Choose tasks based on the tuning decision. A useful first round normally contains:

- a representative task for the intended core use;
- a meaningful variation that tests transfer;
- a boundary or difficult case related to the proposed change;
- a previously reliable task when regression is plausible.

One task may cover several roles. Do not inflate the suite when a smaller set answers the decision.

Select variation axes from the target capability. Examples include different document layouts, repositories, websites, data quality, languages, file sizes, user constraints, or output formats. These are examples, not mandatory categories.

## Protect run validity

- Use the prompt and inputs an ordinary user would provide.
- Provide examples only if the real task would provide them.
- Do not reveal hidden expected outputs, prior failure analysis, or candidate rationale to the executing Agent.
- Isolate candidate runs from stale artifacts that disclose answers.
- Record the exact candidate version, runtime, tools, dependencies, prompt, inputs, and relevant configuration.
- Record mutable input state, applicable project instructions, and whether the Skill was invoked implicitly or explicitly when they affect the result.
- Keep conditions materially comparable when comparing versions.
- Record retries and interventions; do not silently replace a failed first run.

When fresh tasks or isolated agents are unavailable, state the contamination risk rather than presenting the run as independent evidence.

## Respect authority and data boundaries

- Obtain authorization before using private data, changing installed Skills, sending messages, publishing, purchasing, deploying, or modifying production state.
- Prefer copies, staging environments, drafts, and reversible local actions.
- Do not assume that a remote draft, test record, uploaded asset, or reversible production write is side-effect free.
- Do not commit or redistribute confidential inputs and outputs without approval.
- Redact or summarize sensitive records when full retention is unnecessary.

## Capture useful evidence

Preserve what the decision and diagnosis require:

- task identifier and user request;
- source input references and source-availability notes;
- Skill version or hashes;
- dependency versions and relevant input or environment state;
- final artifacts;
- result status and human interventions;
- concise trace or error log when needed for diagnosis;
- environment failures and blocked actions.

Avoid retaining large traces by default. Observable outcomes are primary; they may be files, answers, actions, or state changes. Traces support diagnosis.

## Interpret outcomes fairly

Distinguish:

- Skill failure: the instructions or bundled resources caused or failed to prevent the problem;
- execution variance: the model chose a poor path despite adequate guidance;
- tool or environment failure: required capability was unavailable or malfunctioned;
- task or data defect: the request was unsolvable, contradictory, or the source lacked the target;
- grader uncertainty: reviewers cannot reliably determine correctness.

Do not force every failure into `SKILL.md`. Tune the earliest supported cause.
