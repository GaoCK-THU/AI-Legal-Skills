# Validation And Evidence-Led Documentation

Read this reference when a product requirement has a Demo, Workflow, Skill, or live product that should be tested rather than discussed only as a proposal.

## Define The Test

Before preparing materials, state:

- the requirement hypothesis;
- the functions or transitions being tested;
- the expected user and operating context;
- the consequential actions that must remain simulated or approval-gated;
- the decision the test should support.

Do not create a broad benchmark when one focused run can answer the current question.

## Prepare A Development Set

If no suitable evaluation material exists, create a lightweight development set with logically separated contexts.

### Execution Context

The executing Agent may receive:

- the generic Skill or Workflow;
- materials a real user or connected system could provide;
- neutral, user-style prompts;
- prior-round information that would naturally exist in the same matter.

### Evaluation Context

Keep these away from the executing Agent:

- expected answers and planted conflicts;
- scoring criteria and acceptance notes;
- later-round materials before their scheduled turn;
- previous run diagnoses or intended fixes;
- parent-session conclusions about how the Agent should behave.

For a repeatable multi-round test, prepare:

1. staged user materials;
2. round delivery prompts;
3. evaluator-only ground truth;
4. per-round expected outcomes and critical failures;
5. an operator rule for neutral interventions;
6. a raw evidence record.

These are logical responsibilities, not mandatory folder or archive names. A small test may keep them as separate text blocks; a reusable test should store them as distinct files.

Use synthetic data when real data is unavailable or sensitive. State what the synthetic set can and cannot validate.

## Run In Increasingly Real Conditions

Use the lowest-cost environment that can answer the question:

1. inspect the workflow or Skill statically;
2. use an isolated subagent to test logic and interaction;
3. use a live Alpha or equivalent product to test actual tools, files, state, interface, and permissions;
4. use real or customer-derived materials only when authorized and necessary.

Subagent success does not prove live-product success. Record environment failures separately from Skill failures.

During a run:

- deliver only the current-round materials;
- do not hint, praise a specific answer, or silently correct the Agent;
- answer procedural questions only as needed to continue;
- preserve any operator intervention;
- do not execute consequential external actions merely to complete a test.

## Assess Each Function

Use one compact assessment for each designed function:

| Field | Guidance |
| --- | --- |
| Design | What the function is intended to accomplish. |
| Current status | `Achieved`, `Partially achieved`, `Not achieved`, or `Not tested`. |
| Observed result and limitation | What actually happened and why the result is incomplete or unreliable. |
| Direct evidence | The message, file, state, tool result, or screenshot that supports the conclusion. |

Distinguish:

- **failed**: the test exercised the capability and it produced the wrong result;
- **blocked**: a required tool, permission, source, or environment was unavailable;
- **not tested**: the run did not exercise the capability;
- **source absent**: the required information was not present in the supplied materials;
- **partially achieved**: the result was useful but unstable, incomplete, weakly sourced, or required substantial human repair.

Do not call an untested capability a failure, and do not call a blocked capability successful because the Agent described how it would work.

## Preserve Evidence

After each round, retain:

- exact user materials and prompt;
- exact user-visible Agent response;
- generated files and current matter state;
- visible tool success or failure;
- operator questions and answers;
- approval state and next responsible party;
- screenshots when the interface itself matters.

Keep the raw record unchanged. Add analysis, reconstructed dialogue, and product commentary separately.

## Reconstruct The User-Facing Run

For each round, write:

1. **Input materials**: what entered the system.
2. **User instruction**: the actual user request.
3. **Agent-visible response**: the message or artifact the user received.
4. **Human decision**: what the person approved, rejected, corrected, or supplied.
5. **Progression**: how the matter state and next action changed.
6. **Assessment**: what this round demonstrated and what remained missing.

Quote visible messages when useful. Summarize background tool activity only to explain a limitation or result. Do not expose or fabricate hidden chain-of-thought.

If dialogue is shortened or rewritten for readability, label it as edited or reconstructed. Never substitute an ideal target interaction for an actual run without saying so.

## Write The Requirement Document

For a Workflow or Agent evaluation report, use this structure when appropriate:

### 1. Requirement Background

Explain the user problem, current workflow, and reason the requirement is worth testing.

### 2. Functional Design And Current Capability Assessment

Introduce the test method, materials, environment, and status vocabulary. Assess each function separately using the compact assessment above.

### 3. Actual User-Facing Interaction Replay

Reconstruct the run round by round. Emphasize what users provided, what the Agent returned, what humans decided, and how the work advanced.

### 4. Conclusions And Optimization

Translate gaps into:

- tool or connector configuration;
- Skill instruction tuning;
- state, file, or version-management capability;
- interaction or approval design;
- new development-set coverage;
- next-round acceptance criteria.

Place each screenshot beside the function or interaction it proves. Do not collect unexplained screenshots in a detached evidence section.

Before materially restructuring a shared document, preserve a recoverable copy of the current version.
