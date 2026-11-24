# Experiment directory

Start with the README in the folder for the question you are interested in.
Each folder identifies the experiment, its code, evidence, and findings where
available. Results vary from exploratory demos to benchmark screens; read the
individual notes before comparing scores.

| Folder | Question or activity |
| --- | --- |
| [addition-in-words](addition-in-words/) | Can models add numbers written as words? |
| [clover-gguf](clover-gguf/) | Can local Clover weights run, and how do they compare on Spark? |
| [clover-sft](clover-sft/) | Can Clover's block-diffusion fine-tuning recipe run on Spark? |
| [decision-index](decision-index/) | Can a retrieval index support a decision workload? |
| [decoding-screens](decoding-screens/) | What did earlier diffusion and autoregressive decoding screens show? |
| [deeptutor](deeptutor/) | Can DeepTutor chat through Clover, and when does Clover reuse prompt prefixes? |
| [hle](hle/) | How do models perform on Humanity's Last Exam questions? |
| [jepa](jepa/) | Does JEPA training improve diffusion decoding? |
| [medical-fill](medical-fill/) | How well do models generate or edit fictional medical records? |
| [miniwob](miniwob/) | How do agents perform on small browser tasks? |
| [sudoku](sudoku/) | How do models solve the same Sudoku puzzles? |
| [synthetic-data](synthetic-data/) | How much valid and varied fictional medical data do models generate? |
| [synthdata-video](synthdata-video/) | A replay and video of the synthetic-data experiment. |
| [tabdlm](tabdlm/) | Do generated records remain consistent and satisfy constraints? |
| [tau2](tau2/) | How do agents handle customer-service tool-use tasks? |
| [taxloop](taxloop/) | Can models maintain dependencies between tax forms? |
| [terminal-bench](terminal-bench/) | How do agent harnesses and models perform on terminal tasks? |
| [testdata](testdata/) | Can models generate fictional people and customer data with specified properties? |
| [throughput](throughput/) | How do concurrency and content affect model speed? |
| [webarena](webarena/) | How do browser agents perform on realistic sites? |
| [windtunnel](windtunnel/) | WindTunnel browser-agent benchmark and demos. |
| [workbuddy](workbuddy/) | What does Clover score on WorkBuddy, and how does the harness affect it? |

## How the folders are organized

Older experiment files live in `bench/`, `bench/results/`, `docs/`, and, for
some local data, `downloads/`. Their experiment folders contain relative
symbolic links to those original files. Open a link to work with the original;
there is no second copy. This preserves existing commands, Python imports,
historical references, and local datasets. The WorkBuddy folder and several
standalone demos contain their files directly.

`downloads/`, new outputs in `bench/results/`, model weights, and caches are
ignored by Git. Links to those files may be unavailable in a fresh checkout. The DGX
Spark has additional run artifacts that are not copied to this machine. A
README describing a planned experiment does not imply that it has been run.
