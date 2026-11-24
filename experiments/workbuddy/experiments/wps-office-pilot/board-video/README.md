# Automated WPS board demo recording

`run.py` opens a fresh copy of the original board task deck in WPS, starts a
cropped screen capture, runs Clover and CodeBuddy with the scoped WPS writer,
and renders a combined video. The activity panel is generated from timestamped
agent tool calls and WPS selection/edit events. It is a reconstruction from
actual logs, not a recording of a terminal. Synchronization uses the first
FFmpeg progress timestamp minus encoded output time and is approximate.

This is a Mac-specific pilot. It requires the local WPS bridge on port 18766,
the staged task inputs, CodeBuddy and Python under `/private/tmp`, the prior
sandbox profile and task prompt, the Clover proxy and a valid configured key.
FFmpeg uses AVFoundation device index 4, which must be checked again on other
machines or after devices change. macOS Screen Recording permission is needed.
The current capture records the rectangular WPS window area without audio; keep
WPS visible and stationary. Other windows covering the rectangle are captured.

Run from the repository root outside the execution sandbox:

```sh
/private/tmp/wps-local-python/bin/python experiments/workbuddy/experiments/wps-office-pilot/board-video/run.py
```

The final run directory contains `board-demo-combined.mp4`, `wps.mp4`, the
presentation, event logs, and capture metadata. `render.py RUN_DIR` can
recreate the combined video. Tool and edit logs can contain task content; review
before sharing. The generated panel uses event times, not invented actions.
