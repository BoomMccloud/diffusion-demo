import os
import socket

# Check for terminal execution mode
if (
    os.environ.get("BENCHMARK_MODE", "").lower() in ("terminal", "cli")
    or globals().get("USE_TERMINAL_RUNNER", False)
):
    print("ℹ️ Terminal mode selected. Executing terminal benchmark runner...")
    _cell7_path = os.path.join(os.path.dirname(__file__), "cell_7_terminal_runner.py")
    if os.path.exists(_cell7_path):
        with open(_cell7_path, "r", encoding="utf-8") as _f:
            exec(compile(_f.read(), _cell7_path, "exec"), globals())
    else:
        raise FileNotFoundError(f"Cannot find {_cell7_path}")
    sys.exit(0) if "__file__" in globals() and __name__ == "__main__" else None

import gradio as gr
from IPython.display import HTML, display


for required_name in (
    "UI_CASE_OPTIONS",
    "ui_case_description",
    "ui_run_single",
    "ui_run_suite",
):
    if required_name not in globals():
        raise RuntimeError(
            f"{required_name} is missing. Run Cell 6 before Cell 7."
        )


def port_is_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return probe.connect_ex(("127.0.0.1", port)) != 0


UI_PORT = int(globals().get("BENCHMARK_UI_PORT", 7860))

# Close an earlier copy when this notebook cell is rerun.
previous_ui = globals().get("benchmark_ui")
if previous_ui is not None and hasattr(previous_ui, "close"):
    try:
        previous_ui.close()
    except Exception:
        pass

if not port_is_available(UI_PORT):
    original_port = UI_PORT
    for candidate_port in range(original_port + 1, original_port + 21):
        if port_is_available(candidate_port):
            UI_PORT = candidate_port
            break
    else:
        raise RuntimeError(
            f"Ports {original_port} through {original_port + 20} are busy. "
            "Restart the runtime and rerun Cell 7."
        )
    print(f"Port {original_port} was busy. Using port {UI_PORT} instead.")

first_case_id = UI_CASE_OPTIONS[0][1]

with gr.Blocks(title=f"{PUZZLE_NAME}: AR vs DiffusionGemma") as benchmark_ui:
    gr.Markdown(f"# {PUZZLE_NAME}: AR vs DiffusionGemma")
    gr.Markdown(
        "Compare one case interactively, or run a repeated suite. Model startup "
        "and warm response latency are reported separately."
    )

    with gr.Tab("Single case"):
        with gr.Row():
            case_picker = gr.Dropdown(
                choices=UI_CASE_OPTIONS,
                value=first_case_id,
                label="Test case",
            )
            attempt_picker = gr.Slider(
                minimum=1,
                maximum=5,
                step=1,
                value=1,
                label="Attempt",
            )

        case_description = gr.Markdown(
            value=ui_case_description(first_case_id)
        )
        run_single_button = gr.Button(
            "Run selected case",
            variant="primary",
        )

        with gr.Row():
            ar_image = gr.Image(label="Gemma 4 AR", type="numpy")
            diff_image = gr.Image(label="DiffusionGemma", type="numpy")

        single_summary = gr.Markdown()

        with gr.Accordion("Raw model outputs", open=False):
            ar_raw = gr.Code(label="Gemma 4 AR raw output", language="json")
            diff_raw = gr.Code(
                label="DiffusionGemma raw output",
                language="json",
            )

        case_picker.change(
            fn=ui_case_description,
            inputs=case_picker,
            outputs=case_description,
        )
        run_single_button.click(
            fn=ui_run_single,
            inputs=[case_picker, attempt_picker],
            outputs=[
                ar_image,
                diff_image,
                single_summary,
                ar_raw,
                diff_raw,
            ],
        )

    with gr.Tab("Repeated suite"):
        gr.Markdown(
            "Start with three cases and one attempt. Large suites may run for "
            "more than an hour. Results are saved incrementally to Google Drive."
        )
        with gr.Row():
            case_count_picker = gr.Slider(
                minimum=1,
                maximum=len(PUZZLE_CASES),
                step=1,
                value=3,
                label="Number of cases",
            )
            repeats_picker = gr.Slider(
                minimum=1,
                maximum=5,
                step=1,
                value=1,
                label="Attempts per case",
            )

        run_suite_button = gr.Button(
            "Run repeated suite",
            variant="primary",
        )
        suite_summary = gr.Markdown()
        suite_table = gr.Dataframe(
            headers=[
                "Model",
                "Attempts",
                "Success rate",
                "Optimal rate",
                "Median warm response (s)",
            ],
            datatype=["str", "number", "str", "str", "number"],
            interactive=False,
            label="Aggregate results",
        )
        results_path = gr.Textbox(
            label="Saved JSONL results",
            interactive=False,
        )

        run_suite_button.click(
            fn=ui_run_suite,
            inputs=[case_count_picker, repeats_picker],
            outputs=[suite_summary, suite_table, results_path],
        )

benchmark_ui.queue(default_concurrency_limit=1)

# Ask Colab for its fallback URL before launching. Passing this URL as
# root_path is important, otherwise the page can render while callbacks point
# at an unreachable localhost address.
proxy_url = None
try:
    from google.colab import output as colab_output

    proxy_url = colab_output.eval_js(
        f"google.colab.kernel.proxyPort({UI_PORT})"
    )
except Exception:
    proxy_url = None


def launch_ui(share, root_path=None):
    return benchmark_ui.launch(
        server_name="0.0.0.0",
        server_port=UI_PORT,
        share=share,
        inline=False,
        debug=False,
        prevent_thread_lock=True,
        quiet=False,
        show_error=True,
        root_path=root_path,
    )


share_url = None
share_error = None

try:
    launch_result = launch_ui(share=True)
    _, local_url, share_url = launch_result
except Exception as error:
    share_error = error

if share_url:
    display(
        HTML(
            f'<p><a href="{share_url}" target="_blank" '
            'style="font-size:18px;font-weight:600">'
            f'Open {PUZZLE_NAME} Gradio UI</a></p>'
        )
    )
    print(f"Gradio share URL: {share_url}")
    print("This public URL expires when the Colab runtime stops.")
else:
    print("Gradio could not create a public share URL.")
    if share_error is not None:
        print(f"Share error: {share_error}")

    try:
        benchmark_ui.close()
    except Exception:
        pass

    if not proxy_url:
        raise RuntimeError(
            "Neither a Gradio share URL nor a Colab proxy URL is available."
        )

    # Relaunch with the external proxy URL embedded in Gradio's configuration
    # so events and API calls return to the correct host.
    launch_ui(share=False, root_path=proxy_url)
    display(
        HTML(
            f'<p><a href="{proxy_url}" target="_blank" '
            'style="font-size:18px;font-weight:600">'
            f'Open {PUZZLE_NAME} Colab UI</a></p>'
        )
    )
    print(f"Colab fallback URL: {proxy_url}")

print(f"✅ Cell 7: Web UI running on port {UI_PORT}")
