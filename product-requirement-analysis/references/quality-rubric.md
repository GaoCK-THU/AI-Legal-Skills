# Quality Evaluation Guideline

Quality evaluation asks whether the Agent used the right materials, context, evidence, and judgment to produce a coherent result that a user can rely on. Evaluate observable responses, tool results, state changes, and artifacts. Do not require or assess hidden chain-of-thought.

Create task-specific observable checks under the dimensions below. Use only dimensions exercised by the run.

## 1. Input Understanding And Processing Order

- Did the Agent read all required files, messages, and structured data?
- Did it parse fields, facts, document roles, and versions correctly?
- Did it distinguish original, supplemental, historical, and currently effective material?
- Did it process dependencies in a reasonable order rather than concluding before required reading finished?
- Did it disclose unreadable or incomplete material and its effect?

## 2. Reasoning And Judgment

- Were conclusions grounded in information already read and confirmed?
- Did the visible reasoning contain unsupported jumps, contradictions, wrong attribution, or premature conclusions?
- Did the Agent distinguish fact, allegation, professional opinion, human decision, and open question?
- Did it revise prior conclusions when new information arrived and explain the change?
- Did it prioritize issues that materially affected the next decision or action?

## 3. Tool Selection And Result Handling

- Did the Agent select tools appropriate to the material and task?
- Did it avoid pointless, repeated, or clearly unsuitable calls?
- Did it interpret success, failure, empty results, and partial results correctly?
- Did it use a reasonable fallback or stop drawing conclusions when a required tool failed?
- Did it tell the user what the limitation affected?

Whether a tool can start belongs primarily to Delivery. This dimension evaluates how the Agent selects, uses, and interprets tools.

## 4. Context And Information Acquisition

- Did the Agent first obtain retrievable information from enterprise systems, client records, matter state, reviewed knowledge, or supplied materials?
- Did it avoid asking users to collect information the system should retrieve itself?
- Did it ask humans only for facts, choices, or approvals they were actually needed to provide?
- Did it use the relevant business goal, professional rules, previous decisions, current state, and task context?
- Did it identify missing information, its proper source, and the right person or system to supply it?

## 5. Format And Output Compliance

- Did the output follow required templates, fields, sections, tables, and file formats?
- Did it preserve locked or non-variable content?
- Did it fill variable fields completely and in the correct location without unauthorized additions?
- Was the format appropriate to the intended recipient and workflow?
- Was the artifact valid, readable, editable, or usable by the next step?

Mark this dimension `Not tested` when no meaningful format requirement exists.

## 6. Evidence Reliability And Traceability

Treat this as a central professional-quality gate.

- Did legal, business, and professional claims use necessary evidence rather than model memory alone?
- Did the Agent prefer authoritative, original, current, and applicable sources?
- Did it check jurisdiction, effective date, version, scope, and context?
- Did it distinguish source text, extracted fact, Agent inference, professional recommendation, and human decision?
- Did it preserve the source's meaning without unsupported expansion or selective quotation?
- Could important facts and conclusions be traced to a specific file, message, knowledge entry, page, or decision?
- When sources conflicted, did the Agent show the conflict and identify the currently adopted version and basis?
- When reliable evidence was unavailable, did it say so, narrow the conclusion, and request appropriate confirmation?
- Did it avoid presenting failed searches, empty results, weak sources, or general model knowledge as verified authority?
- Were citations specific enough for a user to locate and review?

Fabricated authority, hidden uncertainty, or an unsupported legal or business conclusion stated as confirmed is a severe quality defect that aggregate scores must not conceal.

## 7. State, Version, And Document Consistency

- Were new materials, human decisions, and external replies added to the current matter promptly?
- Were resolved questions closed and superseded options invalidated?
- Did the Agent distinguish draft, pending review, approved, sent, and completed states?
- Did it use the current effective version rather than stale files or decisions?
- Were matter state, visible response, generated document, and proposed next action mutually consistent?
- If a state update failed, did the Agent detect it before continuing?

## 8. Human Collaboration And Result Usability

- When requesting a decision, did the Agent include the necessary materials, basis, options, recommendation, and a narrow decision request?
- Could the user review, choose, approve, or modify rather than repeat the Agent's research and organization work?
- Were the current conclusion, unresolved questions, next owner, and proposed action clear?
- Was the content adapted to the intended participant and task?
- Were important risks and decision points easy to find?
- Could the result enter review, editing, communication, or the next workflow step with reasonable human effort?

## Rating And Evidence

For each applicable dimension, record:

- **Achieved**: reliable and usable with at most minor editing;
- **Partially achieved**: directionally useful but incomplete, unstable, weakly supported, or requiring substantive human repair;
- **Not achieved**: materially wrong, contradictory, or unusable;
- **Not tested**: not exercised by the materials or environment.

Optionally score comparable versions:

- `2`: reliable and substantially ready to use;
- `1`: useful direction but meaningful correction is required;
- `0`: unreliable or unusable;
- `N/A`: not exercised and excluded from the denominator.

Every rating must cite at least one message, tool result, state change, file, or screenshot.

Report severe defects separately. Examples include:

- concluding before required materials finished loading;
- fabricating a key fact, source, or tool result;
- missing a development set's critical conflict;
- using stale state to recommend the wrong action;
- producing an artifact that contradicts approved facts or locked content.

A later correction demonstrates recovery but does not erase a wrong result already shown to the user.
