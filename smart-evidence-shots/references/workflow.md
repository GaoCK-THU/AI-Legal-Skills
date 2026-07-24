# Screenshot Extraction Workflow Reference

Use this reference for detailed judgment during example-driven screenshot extraction. Follow the user's explicit instructions over these defaults. Do not assume any platform, page type, object class, or evidentiary purpose unless the task supplies it.

## Contents

1. Build the target specification
2. Choose an inspection strategy
3. Locate candidate intervals
4. Select stable frames
5. Check coverage, redundancy, and alternatives
6. Build review artifacts
7. Apply the PDF contract
8. Use the bundled scripts

## 1. Build the Target Specification

Interpret the user's written criteria and example screenshots before scanning the video. For each target category, determine:

- **Target meaning:** the content, state, action, or relationship the screenshot should establish.
- **Required cues:** the elements that must be visible for a frame to qualify.
- **Allowed variation:** details that may change without changing the target meaning, such as text values, position, scale, color, or surrounding content.
- **Exclusions:** visually similar content that should not qualify.
- **Coverage:** whether the user wants every distinct occurrence, one representative occurrence, a fixed number, or another selection rule.

Treat an example as evidence of intent, not automatically as a pixel-perfect template. Decide whether the user is pointing to visual appearance, semantic content, an interface or physical state, an action, or a relationship between visible elements. When several examples are provided, use their shared features to infer the category and their differences to infer acceptable variation.

Ask the minimum necessary clarification questions only when unresolved ambiguity would materially change the selected screenshots. Keep each question specific and combine related uncertainties when practical. Common material ambiguities include:

- exact visual matching versus semantic matching;
- every occurrence versus representative occurrences;
- the target object alone versus the object together with surrounding context;
- whether two examples are separate categories or variations of one category.

Do not ask the user to confirm details that are already clear from the instructions and examples.

## 2. Choose an Inspection Strategy

Inspect the full relevant range rather than only likely timestamps. Adapt the review method to the video's duration, pace, and complexity:

- Review short or slow-changing videos directly when practical.
- Use time-based samples, contact sheets, or timeline thumbnails to navigate longer videos.
- Combine a coarse global scan with denser local review when the video changes quickly or the target may appear briefly.

Use overviews to understand global sequence and compare distant moments. Do not treat an overview as proof that the final frame is stable or complete; its thumbnails may hide blur, loading, small text, or short-lived content. Preserve traceable timestamps for every sampled or candidate frame.

Fixed-interval sampling is a starting point, not a completeness guarantee. Refine the sampling around transitions, partial matches, brief appearances, and any interval where the target could fall between coarse samples.

## 3. Locate Candidate Intervals

Match candidates to the target specification through visual and contextual understanding. Consider only the cues relevant to the task, which may include:

- objects, people, text, symbols, or interface components;
- layout and relative position;
- visible state, action, or progression;
- surrounding context and relationships among elements.

Record a candidate as a time interval rather than immediately committing to one frame. Inspect enough context before and after it to determine whether the apparent match is genuine, incomplete, transitional, or coincidental. Increase review density when a candidate is brief or adjacent to motion or a scene change.

Keep semantic relevance separate from visual stability. First decide that the interval contains the requested content; then select a stable frame within it.

## 4. Select Stable Frames

Inspect nearby frames at a sufficiently fine temporal resolution, including sub-second timestamps when necessary. Choose the clearest complete frame that still represents the target.

Reject or replace a frame when:

- meaningful content is moving or blurred;
- a transition, animation, swipe, camera move, or scroll is incomplete;
- required content is still loading, blank, clipped, or partially rendered;
- an unintended overlay, keyboard, cursor, control, notification, or other obstruction hides required cues;
- essential text, objects, or relationships are not readable or visually distinguishable;
- the captured interface is merely a player, recorder, exporter, or application switcher rather than the user's target.

Judge completeness against the target specification, not against a generic preference for uncluttered images. Keep an overlay or interface element when the user explicitly targets it or when it is necessary to show the requested state or relationship.

If no stable frame exists for a genuine target occurrence, record the miss and the reason. Do not replace it with an unrelated or unstable frame merely to make the output appear complete.

## 5. Check Coverage, Redundancy, and Alternatives

Compare the selected set with every target category and the requested coverage rule.

- Prefer one best stable frame for the same target occurrence.
- Keep another frame when it supplies distinct requested content that cannot fit or remain legible in the first.
- Remove a near-duplicate only when it adds no material visual or contextual information.
- Keep visually similar frames when they represent different target categories or materially different occurrences.
- When two stable frames are both plausible and the distinction may matter to the user's intent, keep both as alternatives and mark their relationship clearly.

Do not use uncertainty as a reason to dump many adjacent frames. Every retained alternative must be stable, relevant, and meaningfully different.

## 6. Build Review Artifacts

Treat the final screenshots as the primary artifact for user review. Name them with a stable ID and source time so each image can be traced back to the video.

Also generate:

- `evidence_manifest.csv` for scripts and structured checks;
- `evidence_manifest.md` for readable review notes;
- overview sheets showing the final selection with IDs and timecodes.

Use these manifest fields:

- `id`
- `source_video`
- `timecode`
- `seconds`
- `target_category`
- `filename`
- `description`
- `review_note`
- `alternative_group`

Use `seconds` for the precise extraction timestamp and `timecode` for the human-readable label. Leave `alternative_group` blank unless multiple screenshots are alternatives for the same target decision. Before delivery, verify that every manifest row points to an existing image, every final image has one row, the timestamps are plausible, and the overview agrees with the final set.

Treat `review_manifest.csv` and `extracted_frames.csv` from the video utility as mechanical trace files. Build or enrich `evidence_manifest.csv` only after the Agent has decided which extracted frames satisfy the user's target categories.

## 7. Apply the PDF Contract

Create a PDF only after the user requests it or approves the screenshots. Use manifest order as page order unless the user specifies another sequence.

For each page:

- use the screenshot's page size;
- place exactly one screenshot full-bleed;
- add one time label and no decorative framing unless requested;
- follow the user's label style when provided, otherwise use the default defined in `SKILL.md`.

To override the default time-label style, provide a JSON file with any supported keys:

```json
{
  "font_name": "Helvetica",
  "font_size": 24,
  "position": "bottom-right",
  "margin": 18,
  "pad_x": 10,
  "pad_y": 6,
  "fill_color": "white",
  "stroke_color": "black",
  "text_color": "black",
  "stroke_width": 1
}
```

Use `top-left`, `top-right`, `bottom-left`, or `bottom-right` for `position`. Use ReportLab color names or hexadecimal color strings.

## 8. Use the Bundled Scripts

Use the macOS video utility for deterministic mechanics while retaining visual and semantic decisions in the Agent:

```bash
swift scripts/video_frames.swift probe --video "/path/to/video.mp4"

swift scripts/video_frames.swift sample \
  --video "/path/to/video.mp4" \
  --out-dir "/path/to/review" \
  --interval 1 \
  --make-overview

swift scripts/video_frames.swift sample \
  --video "/path/to/video.mp4" \
  --out-dir "/path/to/candidate-window" \
  --start 57.5 --end 60 --interval 0.2

swift scripts/video_frames.swift extract \
  --video "/path/to/video.mp4" \
  --out-dir "/path/to/final" \
  --time 58.4 --time 59.2
```

Use `sample` outputs for navigation and local comparison. Use `extract` only after selecting precise candidate timestamps; it preserves the video's display resolution. On macOS, AVFoundation video decoding may require running outside a restricted sandbox.

After screenshot approval or an explicit PDF request, run:

```bash
python3 scripts/create_time_pdf.py \
  --shot-dir "/path/to/final" \
  --out "/path/to/output.pdf" \
  --style-config "/path/to/optional-style.json"
```

Omit `--style-config` to use the default style. Keep `evidence_manifest.csv` in the screenshot directory unless `--manifest` points to another file.
