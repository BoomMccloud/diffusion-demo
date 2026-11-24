# Deploy Clover inside your vertical application

**For local AI platforms, appliance vendors, and software teams that deploy at customer sites**

Embed Clover in the software your customers already use and run inference on a workstation or server they control. Your application owns document retrieval, permissions, and review. Clover handles the language work, such as extracting fields, summarizing evidence, or drafting a response. This lets you build workflows that keep application data inside the customer's environment.

## Where to start

- **Procurement and operations.** Read purchase orders and vendor proposals, extract fields into your existing forms, and flag missing information for review.
- **Field service and manufacturing.** Use site manuals and technician notes to draft service reports or surface relevant procedures from a local knowledge base.
- **Document-heavy enterprise software.** Turn internal documents into searchable summaries or draft case notes grounded in records your application retrieves.

## Deployment and hardware

Clover-35B-A3B-Preview is a text model with 35 billion total parameters, about 3 billion active per token, and up to 128K tokens across input and output. The weights are available under Apache 2.0. For a workstation or appliance evaluation, start with the official GGUF and a Clover-compatible llama.cpp build. For an on-premises server, evaluate the SGLang serving path. [Model and runtime documentation](https://github.com/DiffuSpace/Clover-35B-A3B-Preview), [official GGUF downloads](https://huggingface.co/Diffuspace/Clover-35B-A3B-Preview-GGUF)

The official Q4_0 and Q4_K_M GGUF files are 18.24 GiB and 21.42 GiB, respectively. Budget additional RAM or VRAM for runtime state and the intended context length. In a separate launch test, an INT4 configuration on an RTX 5070 Ti with 16 GB of VRAM generated 101.8 tokens per second on MATH-500. Size the deployment for the exact weights, runtime, and workload you plan to ship. [GGUF sizing guide](https://huggingface.co/Diffuspace/Clover-35B-A3B-Preview-GGUF#available-quantizations), [launch benchmark](https://huggingface.co/blog/Diffuspace/clover-35b-a3b-preview)

## Proposed partner pilot

Choose one workflow, one representative machine, and a sample of real inputs cleared for evaluation. Connect Clover to your existing interface and compare it with your current workflow on output accuracy, time to a usable result, peak memory, and how often a person needs to correct the output. Agree on those thresholds before testing.

To scope a pilot with DiffuSpace, share the application, target hardware and runtime, and one example of the expected output.
