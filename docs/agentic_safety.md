# Agentic Safety

Updated: 2026-05-07

FocusLens can become useful to assistants through reports, MCP, and optional
LLM reflection. This document defines safety boundaries for those features.

## Core Rule

Agents may read aggregate session summaries. Agents must not access webcam
frames.

This rule applies to MCP tools, local agents, LLM integrations, report
generators, and future plugins.

## Allowed Agent Data

Agents may receive:

- session start and end timestamps;
- state durations;
- event counts;
- focus and presence scores;
- derived trend summaries;
- privacy documentation text;
- local report summaries generated from aggregate metrics.

## Disallowed Agent Data

Agents must not receive:

- webcam frames;
- screenshots;
- video clips;
- face images;
- face embeddings;
- raw full landmark arrays from real users;
- identity labels;
- arbitrary local files;
- environment secrets;
- unreviewed custom save directories outside the allowed session root.

## MCP Safety Requirements

The first MCP implementation must be read-only.

Allowed tools:

- `list_sessions`;
- `summarize_sessions`;
- `compare_periods`;
- `get_focus_trends`;
- `read_privacy_contract`.

Disallowed tools in the first MCP release:

- start camera;
- stop camera;
- delete sessions;
- modify config;
- upload data;
- read arbitrary paths;
- run shell commands;
- call external LLMs.

## LLM Reflection Requirements

LLM reflection must be opt-in and separate from normal FocusLens usage.

Requirements:

- default behavior uses no external LLM;
- user chooses provider explicitly;
- payload preview is shown before any external request;
- payload includes aggregate metrics only;
- prompts forbid identity, medical, emotional, and employment judgments;
- generated text must describe uncertainty and limitations.

## User Consent

Any feature that sends data outside the local machine must require explicit
user action at runtime. Documentation alone is not enough.

Minimum consent flow:

1. Explain the provider and destination.
2. Show exactly which summary fields will be sent.
3. Confirm that no frames, images, video, or landmarks are included.
4. Let the user cancel without changing local data.

## Prompt Safety

LLM prompts should say:

```text
You are analyzing aggregate FocusLens session summaries only. Do not infer
identity, emotions, medical conditions, fatigue, employment performance, or
scientific productivity. Provide personal productivity reflections with clear
uncertainty and local-first privacy reminders.
```

## Threats To Test

MCP and agentic features should have tests for:

- path traversal;
- malformed CSV rows;
- symlink or external path attempts;
- empty history;
- hidden write actions;
- prompt injection inside local notes if notes are ever added;
- accidental inclusion of unsupported fields.

## Release Gate

No MCP or LLM release should ship unless these are true:

- tests prove the feature cannot read outside the allowed session root;
- docs list every exposed tool or payload field;
- no tool starts webcam capture;
- no external network call happens by default;
- privacy docs are updated in the same release.
