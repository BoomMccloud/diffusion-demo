# Run multi-step agents with the Clover API

**For teams building agents, copilots, and tool-driven workflows**

When an agent makes several model calls to complete a task, generation time can add up at each step. Clover's block diffusion architecture can generate multiple token positions in parallel, helping shorten the time spent generating plans, tool calls, and responses. Plug the hosted model into your existing agent and measure how quickly it completes the whole task.

## Where to start

- **Operations agents.** Retrieve information, check it against business rules, and prepare a proposed update for approval.
- **Coding agents.** Read a codebase, draft a change, run tests through your tools, and revise the patch based on the results.
- **Interactive copilots.** Stream a response while the application looks up records or guides a user through a multi-step workflow.

## Published performance

In DiffuSpace's internal agent-workload tests, Clover reached **680 output tokens per second** on one NVIDIA GB300 at BF16 and batch size 1. On an H200 agent workload, the published result was **515 tokens per second**, compared with **365** for the DFlash2 configuration in that test. These figures describe model generation on the benchmark setups. For the hosted pilot, measure task time from your own application, including network and tool execution. [DiffuSpace launch benchmarks](https://huggingface.co/blog/Diffuspace/clover-35b-a3b-preview)

## Connect your agent

Use an OpenAI-compatible Chat Completions client with base URL `https://api.diffuspace.ai/v1` and model ID `Clover-35B-A3B-Preview`. The hosted API supports streaming, tool calling, and a thinking toggle. Your application supplies tool schemas, validates and executes calls, and returns results to the model. API keys are available after account approval. [API access and integration guide](https://diffuspace.ai/developers/)

## Proposed partner pilot

Run Clover beside your current model on a representative set of tasks using the same tools and success criteria. Compare task completion rate, valid tool calls, retries, time to first token, and median and 95th-percentile time to a successful result at your expected concurrency. Track model latency and tool latency so you can see where faster generation saves time.

To scope a pilot with DiffuSpace, share one agent workflow, its typical call volume, and the completion time and success rate you need.
