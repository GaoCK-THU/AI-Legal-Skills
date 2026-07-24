---
name: product-requirement-analysis
description: Analyze, explore, validate, and communicate product requirements from project context, user pain points, existing capabilities, source materials, competitor evidence, lightweight demos, isolated Agent trials, and live product runs. Use when Codex needs to discover a product opportunity, build a Demo to make an idea discussable, refine or test a requirement Skill, prepare a development set, run an isolated subagent or Alpha evaluation, assess functions against evidence, draft an evidence-led requirement or Demo explanation, or update project memory after requirement work.
---

# Product Requirement Analysis

Use a lightweight, evidence-aware process. Standardize the work and quality checks, not the product conclusion.

## Select The Depth

- **Explore**: turn a vague opportunity into something concrete enough to discuss by building the smallest useful Demo, such as a pseudo-UI, workflow diagram, interaction script, lightweight prototype, or isolated Agent simulation. Treat the result as a requirement hypothesis, not validation.
- **Analyze**: test and refine a candidate requirement. This may include preparing a development set, tuning a reusable Skill, running an isolated subagent, evaluating a live Alpha product when available, diagnosing failures, and iterating.
- **Document**: turn confirmed design decisions and observed evidence into a concise requirement brief, evaluation report, competitor note, Demo explanation, or user-requested format.

Do only the depth the user currently needs. The three depths may connect, but do not force every task through the full sequence.

## Build Context First

1. Read applicable project instructions and project memory before task-local material.
2. Identify product positioning, target users, current capabilities, project stage, and existing decisions.
3. Read only the sources and artifacts relevant to the candidate requirement.
4. Preserve the project's existing document structure and terminology.

If the task is not inside an established project, ask only for context that materially changes the analysis. Proceed with clearly labeled assumptions when reasonable.

## Frame The Opportunity

Describe the opportunity in plain language:

- Who encounters the problem?
- What are they trying to accomplish?
- What is difficult, slow, risky, fragmented, or currently impossible?
- How do they handle it today?
- Why might this matter to the product now?

Keep these categories distinct:

- **Evidence**: supported by interviews, observed behavior, source material, product data, traceable research, or an actual run.
- **Hypothesis**: a plausible interpretation that still requires validation.
- **Decision**: a direction explicitly confirmed by the user or project authority.
- **Open question**: information still needed before scope can be fixed.

Do not promote brainstorming language, Demo behavior, or one successful test into a confirmed production capability.

## Research Proportionately

Choose research based on uncertainty rather than following a fixed checklist. Possible methods include source-material analysis, user interviews, workflow observation, existing-product inspection, competitor research, and lightweight prototypes.

When researching external facts or competitors:

- Prefer primary and official sources.
- Provide links or other traceable source references.
- Distinguish directly supported facts from inference.
- Record what the evidence does not establish.

Do not use competitor similarity as proof of user demand. Treat it as evidence about possible interaction patterns, market positioning, or feasibility.

## Converge The Requirement

Assess the candidate against the dimensions that matter for the current project:

- User value and severity of the problem.
- Frequency, urgency, or strategic importance.
- Fit with product positioning and existing capabilities.
- Feasibility and dependencies.
- Differentiation or ecosystem value.
- Evidence strength and remaining uncertainty.

Then state:

1. The recommended requirement hypothesis.
2. The smallest coherent first scope.
3. Explicit exclusions and deferred questions.
4. What must be validated next.

Use human checkpoints before fixing important product positioning, MVP scope, or conclusions based mainly on assumptions.

## Explore Through A Demo

Use a Demo to expose the product idea, not merely decorate a document. Before building it, state the question the Demo should help answer and the minimum behavior it must show.

Choose the cheapest adequate form:

- pseudo-UI for information architecture and interaction discussion;
- workflow or sequence diagram for responsibilities and handoffs;
- interaction script for multi-party or multi-round behavior;
- lightweight prototype for concrete controls and state changes;
- isolated Agent simulation for workflow logic, missing inputs, unsafe autonomy, or human checkpoints.

Keep the Demo faithful to the current hypothesis and label imagined behavior. Delegate detailed visual design, frontend implementation, browser testing, deployment, and document-format work to the relevant specialized skills.

## Analyze Through Validation

When a Demo, Workflow, Skill, or live product exists, use this loop as needed:

1. **Define the validation question.** Name the functions, risks, or product assumptions the run should test.
2. **Prepare a development set if none exists.** Create realistic user-facing materials and neutral prompts, plus separate evaluator-only truth and assessment guidance.
3. **Tune the reusable Skill.** Keep test answers, case-specific facts, evaluator notes, and previous diagnoses out of the Skill package.
4. **Run an isolated subagent trial when useful.** Give the test Agent only the proposed Skill or workflow, current-round materials, and neutral prompt. Do not leak expected answers or parent-session conclusions.
5. **Run the live Alpha or equivalent product when available.** Test through the actual user-facing interface and preserve visible responses, files, tool limitations, state changes, corrections, and screenshots.
6. **Evaluate, diagnose, and iterate.** Attribute gaps to the Skill, tool or connector, platform capability, test material, interaction design, or missing coverage before changing the design.

Read [references/validation-and-documentation.md](references/validation-and-documentation.md) when preparing a development set, running a subagent or Alpha test, assessing functions, preserving evidence, or writing an evaluation-based requirement document.

## Use A Four-Layer Evaluation

Match evaluation depth to the decision. Use these layers:

1. **Delivery**: did the Skill trigger, inputs parse, tools execute, and required artifact or state appear?
2. **Quality**: did the Agent understand, judge, retrieve, maintain state, and produce a professionally usable result?
3. **Security**: did the run respect data boundaries, approvals, permissions, and limits on external effects?
4. **Regression**: when comparable versions exist, did a newer version lose previously demonstrated behavior? Omit this layer when there is no meaningful baseline.

Prefer deterministic checks for Delivery and mechanically verifiable Security rules. Use evidence-based human review for semantic Quality. Read [references/quality-rubric.md](references/quality-rubric.md) whenever Quality is being evaluated or a task-specific rubric is being prepared.

Do not let an aggregate score conceal a severe error. Fabricated authority, premature conclusions before required material reading, missed critical conflicts, stale-state actions, unauthorized external effects, or final outputs that contradict approved facts must be reported separately.

## Record Observable Interaction

When documenting a simulated or live run, reconstruct the experience around observable human interaction:

`input material -> user instruction -> Agent-visible response -> human decision -> Agent action or output`

- Show who provided what, what the Agent returned, what decision or material it requested, and how the matter advanced.
- Separate user-visible messages and deliverables from retrieval, parsing, comparison, state updates, and tool logs.
- Never present hidden chain-of-thought or process-log narration as a message received by a user.
- Distinguish raw test output from reader-facing dialogue reconstructed or edited for presentation.
- Preserve approval boundaries and state exactly which external actions remained unexecuted.
- If the Agent first exposed an incorrect conclusion and later corrected it, record both. A correction demonstrates recovery but does not erase the visible quality defect.

## Produce The Requested Artifact

Adapt the output to the audience instead of imposing one template. A lightweight product explanation commonly includes:

- Problem and user context.
- Product opportunity and value.
- Relevant evidence or competitor findings.
- Proposed experience and main functions.
- Scope, exclusions, risks, and open questions.
- Demo image, link, or run evidence when available.

For a Workflow or Agent evaluation document, prefer this evidence-led structure when it fits:

1. Requirement background.
2. Functional design and current capability assessment.
3. Actual user-facing interaction replay.
4. Conclusions, optimization priorities, and next-round acceptance criteria.

Introduce the test method at the start of the functional assessment. Give each function its own compact record of design, current status, observed result and limitation, and direct evidence. Place screenshots near the function or interaction they prove. Clearly separate demonstrated capability, partial capability, untested design, and future target behavior.

Keep early-stage documents concise. Expand into a full PRD only after the requirement and initial scope are sufficiently confirmed.

## Close The Work

When working inside a project with persistent memory:

1. Save source materials and complete deliverables in their proper input or output locations.
2. Record confirmed requirement knowledge in the nearest requirement documentation.
3. Record current status, artifacts, blockers, and next steps in the nearest work log.
4. Promote only project-wide conclusions, reusable methods, or milestone changes to project-level memory.
5. Replace superseded decisions rather than preserving competing truths.

Do not store full research transcripts, development sets, raw test runs, or copied deliverables as shared project memory.
