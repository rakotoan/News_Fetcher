import os
import sys
import time
import json
import webbrowser
import subprocess
from pathlib import Path

import gradio as gr
import app_config


CUSTOM_CSS = """
nav {
    display: none !important;
}

body {
    background:
        radial-gradient(circle at top left, rgba(255, 140, 0, 0.10), transparent 24%),
        linear-gradient(180deg, #11131a 0%, #171923 100%) !important;
    color: #f5f7fb !important;
}

.gradio-container {
    max-width: 980px !important;
    margin: 0 auto !important;
    padding-top: 20px !important;
    padding-bottom: 36px !important;
}

.mission-link {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    min-height: 64px;
    margin: 10px 0;
    padding: 14px 18px;
    border-radius: 12px;
    border: 1px solid rgba(255, 153, 51, 0.60);
    background: linear-gradient(180deg, rgba(34, 39, 54, 0.96), rgba(24, 28, 40, 0.96));
    color: #f8fbff !important;
    text-decoration: none !important;
    font-size: 22px;
    font-weight: 700;
    text-align: left;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.16);
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.mission-link::after {
    content: "→";
    font-size: 22px;
    color: #ffb15c;
    opacity: 0.95;
}

.mission-link:hover {
    transform: translateY(-1px);
    border-color: rgba(255, 166, 77, 0.95);
    background: linear-gradient(180deg, rgba(40, 47, 66, 0.98), rgba(28, 34, 48, 0.98));
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.22);
}

.mission-link:active {
    transform: translateY(0);
}

.back-link {
    display: inline-block;
    margin-top: 20px;
    color: #ffb15c !important;
    text-decoration: none !important;
    font-weight: 700;
}

.back-link:hover {
    color: #ffd19a !important;
}

@media (max-width: 768px) {
    .mission-link {
        min-height: 58px;
        padding: 12px 14px;
        font-size: 18px;
        border-radius: 10px;
    }

    .mission-link::after {
        font-size: 18px;
    }
}
"""


OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)


def slugify(name):
    return name.lower().replace(" ", "-")


def open_in_chrome():
    url = "http://127.0.0.1:7860"
    possible_paths = [
        "C:/Program Files/Google/Chrome/Application/chrome.exe %s",
        "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s"
    ]

    for chrome_path in possible_paths:
        try:
            browser = webbrowser.get(chrome_path)
            browser.open(url)
            return
        except Exception:
            pass

    webbrowser.open(url)


def normalize_single_file(file_value):
    if file_value is None:
        return None
    if isinstance(file_value, str):
        return file_value
    if hasattr(file_value, "name"):
        return file_value.name
    return str(file_value)


def normalize_multi_file(files_value):
    if not files_value:
        return []

    normalized = []
    for f in files_value:
        if isinstance(f, str):
            normalized.append(f)
        elif hasattr(f, "name"):
            normalized.append(f.name)
        else:
            normalized.append(str(f))
    return normalized


def parse_button_input(raw_text):
    if ":" not in raw_text:
        return raw_text.strip(), []

    label, choices_str = raw_text.split(":", 1)
    choices = [x.strip() for x in choices_str.split(",") if x.strip()]
    return label.strip(), choices


def extract_output_files(stdout_text, outputs_cfg):
    lines = [line.strip() for line in stdout_text.splitlines() if line.strip()]
    output_paths = []

    for line in lines:
        candidate = Path(line)
        if candidate.exists():
            output_paths.append(str(candidate))

    if output_paths:
        return output_paths[:len(outputs_cfg)]

    produced_files = []
    for output_cfg in outputs_cfg:
        output_name = output_cfg[0]
        output_format = output_cfg[1]
        expected_file = OUTPUT_DIR / f"{output_name}.{output_format}"
        produced_files.append(str(expected_file) if expected_file.exists() else None)

    return produced_files


def run_mission(mission_cfg, *values):
    single_inputs_cfg = mission_cfg.get("inputs", [])
    multi_inputs_cfg = mission_cfg.get("multi_inputs", [])
    text_inputs_cfg = mission_cfg.get("text_inputs", [])
    button_inputs_cfg = mission_cfg.get("button_inputs", [])
    outputs_cfg = mission_cfg.get("outputs", [])

    idx = 0

    single_files = {}
    for label in single_inputs_cfg:
        single_files[label] = normalize_single_file(values[idx])
        idx += 1

    multi_files = {}
    for label in multi_inputs_cfg:
        multi_files[label] = normalize_multi_file(values[idx])
        idx += 1

    text_values = {}
    for label in text_inputs_cfg:
        text_values[label] = values[idx]
        idx += 1

    button_values = {}
    for raw_button in button_inputs_cfg:
        button_label, _ = parse_button_input(raw_button)
        button_values[button_label] = values[idx]
        idx += 1

    payload = {
        "inputs": single_files,
        "multi_inputs": multi_files,
        "text_inputs": text_values,
        "button_inputs": button_values,
        "outputs": outputs_cfg
    }

    script_path = mission_cfg["script"]
    if not os.path.exists(script_path):
        empty_outputs = [None] * len(outputs_cfg)
        return [f"Erreur : script introuvable -> {script_path}"] + empty_outputs

    result = subprocess.run(
        [sys.executable, script_path, json.dumps(payload, ensure_ascii=False)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        empty_outputs = [None] * len(outputs_cfg)
        return [f"Erreur d'exécution :\n\n{result.stderr}"] + empty_outputs

    stdout = result.stdout.strip() if result.stdout.strip() else "Exécution terminée avec succès."
    produced_files = extract_output_files(stdout, outputs_cfg)

    return [stdout] + produced_files


def render_mission_page(mission_name, mission_cfg):
    gr.Markdown(f"# {mission_name}")

    inputs_components = []

    if mission_cfg.get("inputs"):
        gr.Markdown("### Fichiers d'entrée")
        for label in mission_cfg["inputs"]:
            comp = gr.File(label=label, file_count="single", type="filepath")
            inputs_components.append(comp)

    if mission_cfg.get("multi_inputs"):
        gr.Markdown("### Fichiers multiples")
        for label in mission_cfg["multi_inputs"]:
            comp = gr.File(label=label, file_count="multiple", type="filepath")
            inputs_components.append(comp)

    if mission_cfg.get("text_inputs"):
        for label in mission_cfg["text_inputs"]:
            comp = gr.Textbox(label=label, value="", lines=1, interactive=True)
            inputs_components.append(comp)

    if mission_cfg.get("button_inputs"):
        for raw_button in mission_cfg["button_inputs"]:
            button_label, choices = parse_button_input(raw_button)
            comp = gr.Radio(
                label=button_label,
                choices=choices,
                value=choices[0] if choices else None,
                interactive=True
            )
            inputs_components.append(comp)

    run_button = gr.Button("Run", variant="primary")
    log_output = gr.Textbox(label="Log error", lines=12, interactive=False)

    file_outputs = []

    if mission_cfg.get("outputs"):
        gr.Markdown("### Output")
        for output_cfg in mission_cfg["outputs"]:
            output_name = output_cfg[0]
            output_format = output_cfg[1]
            comp = gr.File(
                label=f"{output_name}.{output_format}",
                interactive=False,
                visible=True
            )
            file_outputs.append(comp)

    run_button.click(
        fn=lambda *vals, cfg=mission_cfg: run_mission(cfg, *vals),
        inputs=inputs_components,
        outputs=[log_output] + file_outputs
    )

    gr.HTML('<a href="/" target="_self" class="back-link">← Back to the App</a>')


with gr.Blocks(title="App") as demo:
    gr.Markdown("# Welcome to the App ! Select a program and launch your workflow !")

    for mission_name, mission_cfg in app_config.MISSIONS.items():
        slug = slugify(mission_name)
        gr.HTML(
            f'''
            <a href="/{slug}" target="_self" class="mission-link">
                {mission_name}
            </a>
            '''
        )


for mission_name, mission_cfg in app_config.MISSIONS.items():
    slug = slugify(mission_name)
    with demo.route(mission_name, f"/{slug}"):
        render_mission_page(mission_name, mission_cfg)


if __name__ == "__main__":
    demo.launch(
        inbrowser=False,
        server_name="127.0.0.1",
        server_port=7860,
        prevent_thread_lock=True,
        css=CUSTOM_CSS
    )

    time.sleep(2)
    open_in_chrome()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass