# Skill review framework

Use this reference to audit an existing Skill before changing it. Adapt the questions to the Skill's domain and available tools.

## 1. Trigger and scope

- Does the frontmatter description say both what the Skill does and when it should trigger?
- Is it broad enough to cover intended variants but narrow enough to avoid unrelated tasks?
- Does it accidentally define the Skill through one dataset, platform, file type, or example?
- Does it overlap another installed Skill? If so, is the routing distinction understandable?

## 2. User contract

- Are required inputs distinguishable from optional inputs and inferred context?
- Are required outputs distinguishable from optional post-processing?
- Are review-only, proposed-change, and actual-edit requests kept distinct?
- Does the Skill state what to do with missing, contradictory, or impossible requirements?
- Are clarification questions reserved for ambiguity that materially changes the result?
- Are consequential actions protected by appropriate authorization?

## 3. Workflow quality

- Does each step have a clear purpose connected to the outcome?
- Does the workflow separate distinct reasoning problems instead of conflating them?
- Are fixed thresholds, time windows, labels, element types, tools, or sequences justified by a real constraint?
- Is the degree of freedom appropriate: high for context-dependent judgment, low for fragile deterministic operations?
- Does the workflow allow alternative valid approaches while preserving hard requirements?
- Are stopping conditions and failure behavior clear?

## 4. Package coherence

- Do `SKILL.md`, references, scripts, assets, and `agents/openai.yaml` describe the same capability?
- Is detailed material stored once and linked from the core workflow?
- Are referenced files present, reachable in one hop, and loaded only when relevant?
- Are scripts parameterized where tasks vary and strict where consistency matters?
- Are scripts actually tested on representative inputs?
- Do scripts define behavior for missing or empty inputs, special characters, dependency absence, no-result cases, partial failure, and exit status where relevant?
- Are assets genuine output resources rather than unnecessary documentation?
- Are external Skills, tools, services, parsers, models, and runtimes assigned clear responsibilities, versions, fallback paths, and failure ownership?

## 5. Generalization review

Classify every material instruction as one of:

- invariant: required across all intended uses;
- configurable: varies by user, task, environment, or domain;
- heuristic: useful default that may be overridden by evidence;
- example: illustrative only;
- accidental constraint: inherited from one case without justification.

Challenge accidental constraints and unlabelled examples. For each fixed noun, number, format, platform, or tool, ask:

1. What real invariant requires it?
2. What valid task would break it?
3. Should it become a parameter, heuristic, example, or conditional reference?

Check transfer across relevant variation axes, such as:

- input format and size;
- domain vocabulary and language;
- platform or application layout;
- output format and user preference;
- tool availability and operating system;
- incomplete, noisy, ambiguous, or source-absent information;
- low-risk local work versus consequential external actions.

Do not claim universal generality. State the intended domain and the variations actually reviewed or tested.

## 6. Evidence and state integrity

- Is the source of truth identified independently of the candidate output?
- If the workflow uses OCR, extraction, transcription, conversion, caches, or summaries, can material decisions be checked against the primary input?
- Are extraction failures distinguishable from later reasoning failures?
- For modified artifacts, can reviewers verify the original remained protected, the output still parses, authorized changes match the complete diff, and formatting or structure did not change unexpectedly?
- For repositories or other mutable inputs, are revision, branch, dirty state, configuration, and applicable instructions recorded when they affect results?
- For external state, are identity, target, pre-state, post-state, authorization, retry behavior, and rollback observable?

## 7. Testability and observability

- Can a run be tied to the exact Skill version and inputs?
- Are final artifacts sufficient for outcome review?
- Is there enough trace to distinguish instruction, script, tool, environment, and data failures?
- Can deterministic contracts be checked without pretending to judge semantics?
- Can a human reviewer record unclear cases without forcing pass or fail?
- Can implicit triggering be tested separately from explicitly forcing the Skill?
- If the Skill promises speed, cost, consistency, or repeatability, can that property be measured without treating an arbitrary tool path as the goal?

## Finding format

For each material finding, record:

| Field | Meaning |
| --- | --- |
| Evidence | Exact instruction, artifact, run behavior, or omission |
| Classification | Confirmed defect, plausible risk, or optional improvement |
| Impact | User-visible failure or limitation it may cause |
| Tuning surface | Description, core workflow, reference, script, asset, metadata, harness, or dataset |
| Proposed change | Smallest change that addresses the cause |
| Validation | Task or check that could confirm or disprove the hypothesis |

Prioritize by expected user impact, likelihood, and regression risk. Avoid scoring systems that create false precision when evidence is sparse.
