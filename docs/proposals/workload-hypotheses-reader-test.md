# Workload Hypotheses Reader-Test Evidence

This artifact preserves the context-free reader test used by the
`workload-hypotheses` proposal. The reader received no conversation or repository
context beyond the named document and did not edit files.

## First test

### Prompt

> Act as a context-free reader tester. Read only
> `/Users/jasonbxu/Documents/GitHub/diffusion-demo/docs/workload_hypotheses.md`.
> Do not inspect other repository files. Answer concisely: (1) What is the
> project trying to discover? (2) Which diffusion strengths are hypotheses?
> (3) What must happen before native infilling can be tested? (4) What does the
> first benchmark test and what could it establish? (5) What has actually been
> completed and what remains? Then list any ambiguity, unsupported claim,
> internal contradiction, or assumed context that would confuse a new reader.
> Do not edit files.

### Independent response

The reader correctly identified the workflow-discovery goal, the long independent
output, bidirectional infilling, sparse repair, and whole-output revision
hypotheses, the native-mask prerequisite, the nine-cell dependency benchmark,
the model-specific interpretation boundary, and the incomplete Colab run.

It found these material ambiguities:

- Exact checkpoint, runner, and hardware identities were incomplete.
- The capability-gate terminology did not align with every hypothesis.
- The 18-row pilot was not clearly separated from evidentiary screening.
- Exact validity, latency eligibility, effect thresholds, sample sizes, and the
  confirmation statistic were insufficiently defined.
- Multi-block semantics and the provisional nature of output-size labels were
  unclear.
- Empirical runner observations lacked their exact timing boundary and tested
  temperature values.

## Final test

### Prompt

> Re-read the updated document only. Check whether the dependency-density
> confirmation statistic, bootstrap unit, latency eligibility, and
> long-independent interpretation are now operationally unambiguous. Return
> only remaining material blockers, or “No material blockers.” Do not edit
> files.

### Independent response

> No material blockers.

## Resulting changes

The document now records exact intended artifacts and the last attempted runtime,
aligns capability terminology and status, separates transport pilot from
screening evidence, defines exact validity and paired-both-valid latency, sets
numeric dependency thresholds, specifies per-cell sample sizes and stratified
bootstrap units, explains runtime-owned multi-block generation, and gives the
source and boundary for existing telemetry observations.
