# Drug inventory replay

A visual reconstruction of the saved Clover / CodeBuddy WorkBuddy Office trial `drug-inventory-split-L2-006__sz8HP6h`, not a recording of the original execution. The source workbook and output workbook supply the displayed rows. The trajectory supplies the sequence of actions, and the trial result records 15/15 deterministic checks. The reconstructed tables show six of the ten workbook columns. Playback timing and visual styling are editorial, not recorded timings.

The 2026-11-17 serial trial is under `~/diffusion-demo/runs/workbuddy-smoke/results/clover-serial-office-014-a001/2026-11-17__12-55-49/` on the Spark. `source/` contains copied task input, trajectory, result and output. Deferred Luna-assisted grading gave this trial a combined score of 100%; the video displays only the deterministic result. This single run is not a paper-comparable benchmark score.

Run with Python containing Pillow and openpyxl, plus FFmpeg:

```sh
python3 experiments/workbuddy/experiments/drug-inventory-video/make_video.py
```

Output: `drug-inventory-replay.mp4`. The rendered frames are in `frames/`. No new model calls are made.

`drug-inventory-action-replay.mp4` is the animated follow-up. `make_action_replay.py` reads the five actual Bash calls and their stdout from `source/cbc-output.txt`, animates them in recorded order, then displays the saved workbook in an illustrative viewer. Typing, cursor movement, viewer interaction and timing are reconstructed. The original agent edited the workbook programmatically, not through a spreadsheet UI. Run the script with the same dependencies to regenerate it.

`drug-inventory-split-view.mp4` is the 20-second split-view edit. `make_split_replay.py` shows all five calls in order, using excerpts from the creation script and captured stdout. The worksheet animation uses representative source rows matched to their saved output tabs. It highlights the fields read by each rule and illustrates grouping before showing the saved workbook. The timing is editorial.

`drug-inventory-row-copy.mp4` is the 20-second worksheet-led edit. `make_row_copy_replay.py` starts with one populated source tab and three empty destination tabs, then illustrates the full split in batches using rows from the saved workbooks. The closing zooms show the populated tabs and match their counts to recorded verifier evidence. The animation previews up to three representative records per batch, and the counters cover all 300 records. Recorded Python excerpts appear in the side panel.

`drug-inventory-paper-replay.mp4` is the 20-second desk view. Run `make_paper_replay.py` to regenerate it. The opening fits all 300 source records on one paper, then pulls back to a four-paper grid. Labeled slips represent batches of real records copied to the three destination papers. The ending pushes in on all three saved outputs together and shows the recorded counts and verifier result.
