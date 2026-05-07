# Evaluation Plan

Updated: 2026-05-07

FocusLens needs evaluation before heavier assistant features. This
document defines how to measure the local attention classifier without storing
or sharing webcam frames.

## Goal

Measure whether FocusLens classifies derived observations correctly enough for
personal feedback.

Evaluation should answer:

- does a centered face classify as `FOCUSED`;
- does no face classify as `AWAY`;
- do distance thresholds classify `TOO_CLOSE` and `TOO_FAR`;
- do large horizontal head offsets classify `LOOKING_AWAY`;
- do missing orientation landmarks classify `UNKNOWN`;
- do known camera-position scenarios, such as a low camera looking upward,
  remain documented and measurable;
- do changes preserve event timing behavior in `SessionTracker`.

## Privacy Boundary

Evaluation fixtures must not contain:

- frames;
- screenshots;
- video;
- face images;
- face embeddings;
- raw full landmark arrays from real users;
- names or identity labels.

Allowed fixture data:

- `detected`;
- `face_bbox_ratio`;
- derived `head_offset`;
- synthetic minimal landmarks;
- expected `AttentionState`;
- optional notes about lighting or camera scenario without identity data.

Known scenarios to include early:

- centered, front-facing camera;
- slightly elevated camera looking downward;
- low camera looking upward, which was observed in `0.2.0` smoke testing to
  make state sensitivity noisier.

## Fixture Shape

Recommended JSONL shape:

```json
{"case_id":"centered_face","detected":true,"face_bbox_ratio":0.18,"head_offset":0.07,"expected_state":"focused"}
{"case_id":"no_face","detected":false,"face_bbox_ratio":null,"head_offset":null,"expected_state":"away"}
```

The harness can convert `head_offset` into synthetic landmarks or evaluate a
small helper that mirrors `calculate_head_offset` behavior. The important rule
is that fixtures stay derived and privacy-safe.

## Metrics

Minimum metrics for `0.3.0`:

- total cases;
- passed cases;
- failed cases;
- accuracy by state;
- confusion pairs such as `FOCUSED -> LOOKING_AWAY`;
- list of case IDs that failed.

Future metrics:

- threshold sensitivity by profile;
- false looking-away rate;
- false away rate;
- calibration stability over repeated samples;
- camera-position sensitivity, especially low bottom-up camera placement;
- event-count stability for noisy state sequences.

## Acceptance Criteria for 0.3.0

- Evaluation runs in CI without camera access.
- Fixtures contain only derived or synthetic data.
- A classifier regression fails tests or a dedicated eval command.
- Output identifies which state or case regressed.
- Documentation explains what the metrics mean and what they do not prove.

## What Evaluation Does Not Prove

Evaluation does not prove scientific attention measurement. It also does not
prove medical fatigue detection, emotion detection, productivity truth, or
identity recognition. It only protects the behavior of FocusLens' simple local
signals.

## Suggested Implementation

Add:

```text
tests/fixtures/attention_eval.jsonl
focuslens/evaluation.py
tests/test_evaluation.py
```

Optional CLI after the library layer is stable:

```powershell
focuslens eval
```

The CLI should print compact metrics and return a non-zero exit code only when
configured quality gates fail.
