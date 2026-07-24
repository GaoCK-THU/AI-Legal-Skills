---
name: tune-skills
description: Review, revise, forward-test, and evaluate an existing Codex Skill as a complete reusable package, including SKILL.md, references, scripts, assets, and agent metadata. Use when a user asks to audit, optimize, tune, generalize, debug, or compare versions of a Skill and wants the revision validated on realistic or real tasks rather than judged only as documentation. Do not use for creating an unrelated Skill from scratch or for merely executing a Skill without improving it.
---

# Tune Skills

Improve an existing Skill through a protected baseline, an explicit candidate revision, realistic task runs, and evidence-based iteration. Adapt the review and evaluation to the target Skill's domain instead of imposing one fixed task type, tool path, artifact format, or score.

## Core rules

- Treat the complete Skill package and its execution environment as the system under review.
- Preserve the current working version before editing. Work on a candidate copy by default.
- Do not modify an installed or shared Skill without explicit user authorization.
- Choose an explicit mode: `audit-only`, `candidate-tuning`, or `version-comparison`. Do not force edits or runs in `audit-only` mode.
- Separate reusable Skill behavior from dataset-specific examples, platforms, labels, tools, and output formats.
- Prefer evaluating final outcomes. Enforce an exact process only when that process is itself a requirement.
- Use real user-style tasks whenever authorized and practical. Do not declare success from prose review alone.
- Keep expected answers, prior diagnoses, and hidden annotations away from the executing Agent unless the task genuinely provides them.
- Prefer primary inputs over OCR, extraction, transcription, summaries, caches, or other lossy intermediates when validating a material judgment. Record failures at the layer where they arise.
- Ask focused clarification questions only when unresolved ambiguity would materially change the revision, run, or judgment.
- Match evaluation depth to the decision. Keep early iterations lightweight unless the user needs a repeatable benchmark or release gate.
- Preserve user data, unrelated files, credentials, and production state. Request approval before consequential external actions.
- Classify side-effect risk before a trial. Use simulation or isolated state when a comparable live run would message, publish, purchase, deploy, change permissions, expose data, or create duplicate production effects.

## Workflow

### 1. Establish the tuning contract

Read the target Skill completely, including files directly referenced by `SKILL.md`, its `agents/openai.yaml`, relevant scripts, assets, and applicable project instructions.

Confirm or infer, then state:

- the target Skill and current version or snapshot;
- the intended users, tasks, inputs, and outputs;
- the observed problem or desired capability change;
- behavior that must not regress;
- available real tasks, examples, and human reviewers;
- authorization boundaries for editing, running tools, and using data;
- the decision this tuning round must support.
- the mode: read-only audit, candidate tuning, or existing-version comparison.

If the request is exploratory, propose a small first round instead of forcing a complete benchmark.

### 2. Freeze the baseline and prepare the selected mode

Record enough provenance to reproduce the work: source path, relevant file hashes or version identifier, date, runtime and dependency versions, applicable project instructions, and mutable input state such as repository revision or remote test state when relevant.

In `audit-only` mode, preserve the baseline identity and proceed through findings, hypotheses, and a proposed validation design without creating or running a candidate. State that improvement remains unverified.

In `candidate-tuning` mode, create a separate candidate copy unless the user explicitly requests an in-place edit. In `version-comparison` mode, preserve the identity of every tested version and do not silently modify them.

Never describe a candidate as an improvement merely because its wording appears cleaner.

### 3. Review the complete Skill

Read [references/review-framework.md](references/review-framework.md). Produce findings tied to evidence and a concrete tuning surface. Review at least:

- triggering and scope;
- input, output, and clarification contracts;
- workflow reasoning and degree of freedom;
- consistency across instructions, references, scripts, assets, and metadata;
- dependency ownership, versions, availability, fallback behavior, and failure attribution;
- determinism, safety, portability, and failure handling;
- overfitting and generalization risks;
- testability and observability.

Distinguish confirmed defects, plausible risks, and optional improvements. Do not rewrite sections that lack a supported reason to change.

### 4. Form and, when authorized, implement tuning hypotheses

For each material change, record:

- observed evidence;
- suspected cause;
- proposed change;
- expected observable effect;
- regression risk;
- the task or check that could disprove the hypothesis.

In `audit-only` mode, stop at proposed changes and validation design. Otherwise, edit the smallest appropriate layer. Put core routing and non-negotiable workflow rules in `SKILL.md`; put detailed or domain-specific guidance in references; use scripts for repeated deterministic operations; use assets only for files copied into outputs.

Validate syntax and run any changed scripts on representative and boundary inputs. Keep user examples as examples, not universal definitions, unless the user explicitly defines a closed domain.

### 5. Run realistic tasks

Read [references/real-task-trials.md](references/real-task-trials.md). Select a small task portfolio that represents intended use and at least one meaningful variation or boundary. Use actual user prompts and raw inputs where authorized.

Run the candidate in a context that does not contain hidden expected answers. When a baseline comparison is necessary for the decision, run materially comparable tasks and conditions. Do not require a Skill-enabled versus Skill-disabled experiment unless it answers the user's actual question. If triggering behavior changed, include implicit-invocation trials; an explicitly forced Skill run does not test whether its description triggers correctly.

Classify the trial using [references/side-effect-trials.md](references/side-effect-trials.md). A realistic task may use real inputs and user-style prompts without executing a real external action. Never duplicate high-impact production actions merely to compare versions.

Save final artifacts and the minimum useful trace for diagnosis. Record missing source information, blocked actions, and environment failures separately from Skill failures.

### 6. Evaluate at the required depth

Read [references/lightweight-eval.md](references/lightweight-eval.md). Derive acceptance criteria from the target task rather than importing fixed metrics.

Use:

- deterministic checks for properties code can verify reliably;
- human review for semantic correctness, usefulness, quality, and ambiguous cases;
- model-based grading only when useful and calibrated against human judgment.

Report explicit counts and denominators. A valid denominator must exclude impossible or source-absent requirements while recording them separately. Do not hide hard failures inside one weighted score.

When a Skill modifies artifacts or state, verify authorized scope, unexpected differences, preserved originals or protected regions, output validity, and resulting state. Treat unauthorized or wrongly targeted effects as hard failures. Test repeated runs only when reliability or variance matters to the decision.

### 7. Diagnose and iterate

Map each failure to the earliest supported cause: trigger, core instructions, reference guidance, script, tool, runtime, task data, grader, or ambiguity. Change only what the evidence supports, then rerun the affected task and relevant regression tasks.

Stop when the decision is supported, not when every imaginable test exists. Present:

- what changed and why;
- what was run;
- observed results and limitations;
- remaining risks;
- recommendation: retain baseline, continue iterating, accept candidate, or install with approval.

## Reusable records

Copy and adapt these assets when persistent records are useful:

- [assets/skill-review-template.md](assets/skill-review-template.md) for findings and tuning hypotheses;
- [assets/trial-record-template.md](assets/trial-record-template.md) for task runs and provenance;
- [assets/human-review-template.csv](assets/human-review-template.csv) for item-level human review.

Do not create process documents that the current tuning decision does not need.
