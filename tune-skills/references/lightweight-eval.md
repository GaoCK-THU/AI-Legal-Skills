# Lightweight evaluation

Use the smallest evaluation that supports the current tuning decision. Evaluation means checking a system against explicit criteria; a benchmark is a stable, repeatable set of tasks and scoring rules used to compare versions over time. Most early tuning rounds need evaluation, not a full benchmark.

## Derive criteria from the task

Define:

- unit of review: task, output item, required event, field, action, or another domain-appropriate unit;
- acceptance criteria and hard failures;
- valid denominator;
- handling of unclear, blocked, and source-absent cases;
- who or what can judge each criterion reliably.

Do not import metrics from an unrelated Skill. A file-conversion Skill, research Skill, browser workflow, coding Skill, and media Skill may require different review units and failure definitions.

## Assign graders by competence

Use deterministic checks for objectively computable properties, such as:

- required files or fields exist;
- files parse or commands complete;
- schema, dimensions, page count, naming, links, timestamps, or checksums match a contract;
- tests or linters pass;
- prohibited side effects did not occur when that can be verified.

Use human review for semantic correctness, relevance, completeness, usability, visual quality, tone, judgment, and ambiguous equivalence.

When truth is ambiguous, define the categories before grading, use primary evidence rather than candidate-produced intermediates, allow `unclear`, and record reviewer adjudication. Do not report complete recall unless the required items were exhaustively annotated or otherwise established. Review a sample of non-findings when false negatives matter.

Use model-based graders only when they save meaningful effort and have been compared with human judgments on representative cases. A model grader is another model asked to judge an output; it can scale review but can also repeat the same blind spots.

## Minimal reporting

Prefer raw counts with explicit denominators during early tuning:

```text
Tasks passed: 4/5
Valid required items recalled: 18/20
Incorrect output items: 1/22
Unclear items: 2/22
Source-absent requested items: 1
Artifact-contract failures: 0/5 tasks
```

Pair output-item review with coverage review. Looking only at produced outputs cannot reveal a completely missed requirement.

Record source-absent or impossible requirements separately; do not count an honest non-production as a recall failure. Do count falsely claiming completion or fabricating a substitute as an error.

For artifact- or state-changing Skills, independently check:

- the original or protected state remained unchanged where required;
- the output or resulting state is valid and reachable;
- the complete observed diff matches authorized and reported changes;
- no unauthorized target, field, region, formatting, permission, identity, or resource changed;
- retries did not duplicate effects;
- cleanup or rollback completed when required.

Treat unauthorized actions, wrong targets or identities, duplicate consequential effects, fabricated success, and unverified external state as hard failures rather than averaging them into a total score.

## Diagnose for iteration

Attach a short error tag and supported cause to each failure. Suggested top-level causes are:

- `trigger`
- `scope_or_contract`
- `core_instructions`
- `reference_guidance`
- `script_or_asset`
- `model_execution`
- `tool_or_environment`
- `task_or_source_data`
- `grader_or_rubric`
- `unresolved`

Keep the observed error separate from the suspected cause. For example, “missing output field” is an observation; “reference omitted the field mapping” is a cause hypothesis.

## Decide the next step

- Accept the candidate when the intended improvement is demonstrated and material regression is not observed.
- Continue iterating when failures map to an actionable tuning surface.
- Retain the baseline when benefit is unproven or regression is material.
- Expand into a benchmark only when repeated version comparison, release gating, or team-wide reporting justifies the maintenance cost.

Always state sample limits, untested variations, reviewer count, and contamination or comparability risks.
