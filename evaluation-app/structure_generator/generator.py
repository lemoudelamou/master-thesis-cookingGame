import streamlit as st
import json
import os
import re
import glob
import time
from openai import OpenAI
from dotenv import load_dotenv

from structure_checker.json_validator import (
    validate_json_file,
    validate_cross_file_references,
)

from config.config import (
    PROCESS_JSON_SCHEMA,
    TASKS_TEXT_JSON_SCHEMA,
)

# ── Load .env ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))


# ── Constants ──────────────────────────────────────────────────────────────────

DEFAULT_SYSTEM_MESSAGE = (
    "You are a recipe-to-JSON conversion engine. Your task is to convert "
    "cooking recipes into two JSON files (process.json and taskTexts.json) "
    "for a cooking game."
)

PRICES = {
    "gpt-5.2": {"input": 1.75 / 1_000_000, "output": 14.00 / 1_000_000},
    "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
    "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    "gpt-4-turbo": {"input": 10.00 / 1_000_000, "output": 30.00 / 1_000_000},
    "gpt-3.5-turbo": {"input": 0.50 / 1_000_000, "output": 1.50 / 1_000_000},
}


# ── Helpers ────────────────────────────────────────────────────────────────────


def find_shot_files():
    found = {}
    for path in glob.glob(os.path.join(SCRIPT_DIR, "*.txt")):
        fname = os.path.basename(path)
        m = re.search(r"(\d+)", fname)
        if m:
            n = int(m.group(1))
            if 0 <= n <= 13 and "shot" in fname.lower():
                found[n] = path
    return dict(sorted(found.items()))


def estimate_cost(model, inp, out):
    p = PRICES.get(model, {"input": 0, "output": 0})
    return inp * p["input"] + out * p["output"]


def find_json_object(text, start_pos=0):
    json_start = -1
    for i in range(start_pos, len(text)):
        if text[i] == "{":
            json_start = i
            break
    if json_start == -1:
        return None, -1

    brace_count = 0
    for i in range(json_start, len(text)):
        if text[i] == "{":
            brace_count += 1
        elif text[i] == "}":
            brace_count -= 1
            if brace_count == 0:
                return text[json_start : i + 1].strip(), i + 1

    return None, -1


def extract_analysis_and_json(text):
    text = text.replace("```json", "").replace("```", "")
    first_json, first_end = find_json_object(text, 0)
    if first_json is None:
        raise ValueError("Could not find first JSON object in the response.")

    second_json, _ = find_json_object(text, first_end)
    if second_json is None:
        raise ValueError("Could not find second JSON object in the response.")

    analysis = text[: text.find(first_json)].strip()
    analysis = re.sub(r"^---+\s*$", "", analysis, flags=re.MULTILINE).strip()
    return analysis, first_json, second_json


def inject_recipe(prompt_text: str, recipe_text: str) -> str:
    """Inject recipe into the RECIPE INPUT section of the prompt."""
    marker = "RECIPE INPUT:"
    sep = "=" * 80
    if marker in prompt_text:
        idx = prompt_text.index(marker)
        base = prompt_text[:idx].rstrip()
    else:
        base = prompt_text.rstrip()

    return f"{base}\n\n{sep}\n{marker}\n{sep}\n\n{recipe_text.strip()}"


def run_conversion(
    api_key, full_prompt, recipe_name, model, system_message, temperature=0.0
):
    client = client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    start = time.time()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": full_prompt},
        ],
        temperature=temperature,
    )

    elapsed = time.time() - start
    raw = response.choices[0].message.content.strip()
    inp = response.usage.prompt_tokens
    out = response.usage.completion_tokens

    try:
        analysis, p_str, t_str = extract_analysis_and_json(raw)
    except ValueError as e:
        return {
            "recipe_name": recipe_name,
            "raw": raw,
            "parse_failed": True,
            "parse_failed_reason": str(e),
            "analysis": "",
            "process_json": {},
            "task_texts_json": {},
            "input_tokens": inp,
            "output_tokens": out,
            "total_tokens": inp + out,
            "cost": estimate_cost(model, inp, out),
            "elapsed": elapsed,
            "model": model,
            "temperature": temperature,
            "process_validation": {
                "valid": False,
                "checks": {},
                "errors": [],
                "error_details": {},
            },
            "taskstext_validation": {
                "valid": False,
                "checks": {},
                "errors": [],
                "error_details": {},
            },
        }

    process_validation = validate_json_file(p_str, PROCESS_JSON_SCHEMA, "process")
    taskstext_validation = validate_json_file(
        t_str, TASKS_TEXT_JSON_SCHEMA, "taskstext"
    )
    validate_cross_file_references(process_validation, taskstext_validation)

    process_json = (
        process_validation["parsed_json"]
        if process_validation["parsed_json"] is not None
        else {}
    )
    task_texts_json = (
        taskstext_validation["parsed_json"]
        if taskstext_validation["parsed_json"] is not None
        else {}
    )

    return {
        "recipe_name": recipe_name,
        "raw": raw,
        "parse_failed": False,
        "parse_failed_reason": "",
        "analysis": analysis,
        "process_json": process_json,
        "task_texts_json": task_texts_json,
        "input_tokens": inp,
        "output_tokens": out,
        "total_tokens": inp + out,
        "cost": estimate_cost(model, inp, out),
        "elapsed": elapsed,
        "model": model,
        "temperature": temperature,
        "process_validation": process_validation,
        "taskstext_validation": taskstext_validation,
    }


# ── Validation UI helpers ──────────────────────────────────────────────────────


def _color_badge(label: str, hex_color: str) -> str:
    return (
        f'<span style="'
        f"background-color:{hex_color};"
        f"color:#fff;"
        f"padding:2px 10px;"
        f"border-radius:4px;"
        f"font-size:0.82rem;"
        f"font-weight:600;"
        f"letter-spacing:0.03em;"
        f'">{label}</span>'
    )


_CATEGORY_META = {
    "parse_errors": ("Parse Errors", "#c0392b"),
    "schema_errors": ("Schema Errors", "#e67e22"),
    "parent_child_errors": ("Parent-Child Errors", "#8e44ad"),
    "duplicate_transition_errors": ("Duplicate Transition Errors", "#6d4c41"),
    "reference_errors": ("Reference Errors", "#7f8c8d"),
}


def _effective_checks(filename: str, checks: dict) -> dict:
    if filename == "taskTexts.json":
        return {
            k: v
            for k, v in checks.items()
            if k
            not in (
                "transitionsParentChildValid",
                "transitionsDuplicateValid",
            )
        }
    return checks


def _display_validation_results(results: dict):
    st.markdown("---")
    st.header("Validation Statistics")

    total_files = len(results)
    total_score = 0
    valid_files = 0

    for filename, result in results.items():
        effective_checks = _effective_checks(filename, result["checks"])
        passed = sum(1 for v in effective_checks.values() if v)
        score = (passed / len(effective_checks)) * 100 if effective_checks else 0
        total_score += score
        if result["valid"]:
            valid_files += 1

    avg_score = total_score / total_files if total_files else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Files", total_files)
    with col2:
        st.metric("Valid Files", valid_files)
    with col3:
        st.metric("SV Score", f"{avg_score:.1f}%")

    _display_check_rates(results)

    st.markdown("---")
    st.header("Detailed Results")

    for filename, result in results.items():
        _display_file_result(filename, result)


def _display_check_rates(results: dict):
    st.subheader("Check Pass Rates")

    check_labels = {
        "parseable": "1. JSON Parsability",
        "schemaCompliant": "2. Schema Compliance",
        "transitionsParentChildValid": "3. Parent ≠ Child (process.json only)",
        "transitionsDuplicateValid": "4. No Duplicate Transitions (process.json only)",
        "referenceValid": "5. Reference Validity",
    }

    for check_key, label in check_labels.items():
        applicable = [
            r
            for fname, r in results.items()
            if not (
                check_key
                in (
                    "transitionsParentChildValid",
                    "transitionsDuplicateValid",
                )
                and fname == "taskTexts.json"
            )
        ]

        if not applicable:
            continue

        passed = sum(1 for r in applicable if r["checks"].get(check_key, False))
        percentage = (passed / len(applicable)) * 100

        st.progress(
            percentage / 100,
            text=f"{label}: {passed}/{len(applicable)} ({percentage:.1f}%)",
        )


def _display_file_result(filename: str, result: dict):
    if filename == "taskTexts.json":
        check_labels = {
            "parseable": "Parsability",
            "schemaCompliant": "Schema",
            "referenceValid": "Reference Validity",
        }
    else:
        check_labels = {
            "parseable": "Parsability",
            "schemaCompliant": "Schema",
            "transitionsParentChildValid": "Parent ≠ Child",
            "transitionsDuplicateValid": "No Duplicate Transitions",
            "referenceValid": "Reference Validity",
        }

    with st.expander(f" {filename}", expanded=not result["valid"]):
        if result["valid"]:
            st.markdown(
                _color_badge("All validation checks passed!", "#27ae60"),
                unsafe_allow_html=True,
            )
            st.write("")
        else:
            failed = sum(1 for k in check_labels if not result["checks"].get(k, False))
            st.markdown(
                _color_badge(f"Failed {failed} validation check(s)", "#c0392b"),
                unsafe_allow_html=True,
            )
            st.write("")

        st.subheader("Validation Checks")
        cols = st.columns(len(check_labels))
        for idx, (key, label) in enumerate(check_labels.items()):
            with cols[idx]:
                if result["checks"].get(key, False):
                    st.success(f"✓\n{label}")
                else:
                    st.error(f"✗\n{label}")

        if result.get("error_details"):
            _display_categorized_errors(result["error_details"], filename)
        elif result.get("errors"):
            st.subheader(f"Validation Errors ({len(result['errors'])})")
            for i, error in enumerate(result["errors"], 1):
                st.markdown(f"**{i}.** {error}")


def _display_categorized_errors(error_details: dict, filename: str):
    error_categories = [
        ("parse_errors", "Parse syntax errors that prevent the file from being read"),
        (
            "schema_errors",
            "All schema violations including missing required fields, unexpected fields, wrong types, and structural issues",
        ),
        (
            "parent_child_errors",
            "Transitions where parent equals child (process.json only)",
        ),
        (
            "duplicate_transition_errors",
            "Duplicate parent-child transition pairs (process.json only)",
        ),
        ("reference_errors", "Cross-file reference validation errors"),
    ]

    total_errors = sum(len(error_details.get(key, [])) for key, _ in error_categories)
    if total_errors == 0:
        return

    st.subheader(f"Validation Errors ({total_errors} total)")

    for error_key, description in error_categories:
        if filename == "taskTexts.json" and error_key in (
            "parent_child_errors",
            "duplicate_transition_errors",
        ):
            continue

        label, hex_color = _CATEGORY_META[error_key]
        errors_list = error_details.get(error_key, [])
        badge_html = _color_badge(label, hex_color)

        if errors_list:
            with st.expander(f"{label} ({len(errors_list)})", expanded=True):
                st.markdown(badge_html, unsafe_allow_html=True)
                st.caption(description)
                for i, error in enumerate(errors_list, 1):
                    st.markdown(f"**{i}.** {error}")
        else:
            with st.expander(f"{label} (0)", expanded=False):
                st.markdown(badge_html, unsafe_allow_html=True)
                st.caption(description)
                st.success("No errors in this category")


def render_recipe_converter_page():
    shot_files = find_shot_files()

    if "rc_shot_idx" not in st.session_state:
        st.session_state["rc_shot_idx"] = len(shot_files) - 1 if shot_files else 0
    if "rc_panel_open" not in st.session_state:
        st.session_state["rc_panel_open"] = True
    if "rc_api_key" not in st.session_state:
        st.session_state["rc_api_key"] = os.getenv("OPENAI_API_KEY", "")
    if "rc_prompt_value" not in st.session_state:
        st.session_state["rc_prompt_value"] = ""
    if "rc_use_manual" not in st.session_state:
        st.session_state["rc_use_manual"] = False
    if "rc_system_message" not in st.session_state:
        st.session_state["rc_system_message"] = DEFAULT_SYSTEM_MESSAGE
    if "rc_temperature" not in st.session_state:
        st.session_state["rc_temperature"] = 0.0

    has_result = "recipe_result" in st.session_state

    if has_result and not st.session_state.get("rc_panel_auto_collapsed"):
        st.session_state["rc_panel_open"] = False
        st.session_state["rc_panel_auto_collapsed"] = True

    st.title("JSON Conversion")
    st.markdown(
        "Convert cooking recipes into `process.json` and `taskTexts.json` for the game engine."
    )

    if os.getenv("OPENAI_API_KEY"):
        st.success("API key loaded from `.env`")
    else:
        st.info("No `.env` file found — enter your API key manually below.")

    if has_result:
        panel_open = st.session_state["rc_panel_open"]
        label = "◀ Hide inputs" if panel_open else "▶ Show inputs"
        if st.button(label, key="rc_toggle_btn"):
            st.session_state["rc_panel_open"] = not panel_open
            st.rerun()

    panel_open = st.session_state["rc_panel_open"]

    if has_result and not panel_open:
        col_left = None
        col_right = st.container()
    else:
        col_left, col_right = st.columns([1, 1], gap="large")

    if col_left is not None:
        with col_left:
            st.subheader("Settings")

            st.text_input(
                "OpenAI API Key",
                type="password",
                placeholder="sk-proj-...  (or set OPENAI_API_KEY in .env)",
                key="rc_api_key",
            )

            col_model, col_name = st.columns(2)
            with col_model:
                st.selectbox("Model", list(PRICES.keys()), key="rc_model")
            with col_name:
                st.text_input(
                    "Output name",
                    value="my_recipe",
                    placeholder="e.g. carbonara",
                    key="rc_recipe_name",
                )

            st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,
                step=0.1,
                value=st.session_state["rc_temperature"],
                help="0 = deterministic output · higher values = more creative / random",
                key="rc_temperature",
            )

            st.divider()

            st.subheader("System Message")
            st.caption("Sent as the `system` role before the user prompt. Edit freely.")

            col_sm_label, col_sm_reset = st.columns([3, 1])
            with col_sm_reset:
                if st.button(
                    "↺ Reset", key="rc_reset_system_msg", use_container_width=True
                ):
                    st.session_state["rc_system_message"] = DEFAULT_SYSTEM_MESSAGE
                    st.rerun()

            st.text_area(
                "System message",
                height=120,
                label_visibility="collapsed",
                key="rc_system_message",
            )
            st.caption(f"{len(st.session_state['rc_system_message']):,} chars")

            st.divider()

            st.subheader("Prompt")

            use_manual = st.toggle(
                "Enter prompt manually",
                key="rc_use_manual",
                help="OFF = select from shot files on disk   |   ON = type your own prompt",
            )

            if not use_manual:
                if not shot_files:
                    st.error(
                        f"No shot files found in `{SCRIPT_DIR}`.\n\n"
                        "Place files named like `1-shot.txt`, `11-shot.txt` etc. "
                        "in the same folder as this script."
                    )
                    selected_shot_n = None
                    prompt_text = ""
                else:
                    options = {
                        f"{n}-shot  ({os.path.basename(p)})": n
                        for n, p in shot_files.items()
                    }
                    shot_labels = list(options.keys())

                    safe_idx = min(
                        st.session_state["rc_shot_idx"], len(shot_labels) - 1
                    )

                    chosen_label = st.selectbox(
                        "Select prompt file",
                        shot_labels,
                        index=safe_idx,
                        label_visibility="collapsed",
                    )

                    st.session_state["rc_shot_idx"] = shot_labels.index(chosen_label)

                    selected_shot_n = options[chosen_label]
                    prompt_path = shot_files[selected_shot_n]

                    with open(prompt_path, "r", encoding="utf-8") as f:
                        prompt_text = f.read()

                    st.caption(
                        f" {os.path.basename(prompt_path)} · {len(prompt_text):,} chars"
                    )
            else:
                selected_shot_n = "manual"
                prompt_text = st.text_area(
                    "Your prompt",
                    height=240,
                    placeholder=(
                        "Paste or type your full prompt here.\n\n"
                        "If you include a RECIPE INPUT: marker, the recipe will be\n"
                        "injected there. Otherwise it is appended at the end."
                    ),
                    label_visibility="collapsed",
                    key="rc_manual_prompt",
                )
                if prompt_text:
                    st.caption(f"{len(prompt_text):,} chars")

            st.divider()

            st.subheader("Recipe Input")
            st.caption(
                "Injected into the RECIPE INPUT section of the assembled prompt."
            )

            st.text_area(
                "Recipe",
                height=180,
                placeholder=(
                    "Marinierte Auberginen\n(für 4 Personen)\n\n"
                    "2-3 Knoblauchzehen\nca. 100 ml Olivenöl\nMeersalz\n"
                    "2 Auberginen\n\n"
                    "1. Knoblauch abziehen, fein hacken. Mit Öl und Salz mischen. \n"
                    "2. Auberginen waschen und in ca. 1 cm dicke Scheiben schneiden.\n"
                    "3. Auf ein Blech legen und mit der Marinade reichlich einpinseln..\n"
                    "4. Im Ofen bei 180 °C (Gas Stufe 2) ca. 20 Minuten braten, bis die Scheiben goldbraun sind."
                ),
                label_visibility="collapsed",
                key="rc_recipe_input",
            )

            st.divider()

            st.subheader("Assembled Prompt")
            st.caption(
                "Click **Assemble** to build from the selections above, "
                "then edit freely before converting."
            )

            col_assemble, col_reset = st.columns(2)
            with col_assemble:
                assemble_clicked = st.button(
                    "🔧  Assemble",
                    use_container_width=True,
                    key="rc_assemble_btn",
                )
            with col_reset:
                reset_clicked = st.button(
                    "↺  Reset",
                    use_container_width=True,
                    key="rc_reset_prompt",
                )

            if assemble_clicked:
                st.session_state["rc_prompt_value"] = inject_recipe(
                    prompt_text,
                    st.session_state.get("rc_recipe_input", ""),
                )
                st.rerun()

            if reset_clicked:
                st.session_state["rc_prompt_value"] = ""
                st.rerun()

            final_prompt = st.text_area(
                "Final prompt",
                value=st.session_state.get("rc_prompt_value", ""),
                height=350,
                label_visibility="collapsed",
                placeholder="Click 'Assemble' above to populate this field…",
            )
            st.session_state["rc_prompt_value"] = final_prompt

            char_count = len(final_prompt)
            if char_count:
                st.caption(
                    f"{char_count:,} chars · ~{char_count // 4:,} tokens (estimate)"
                )

            st.divider()

            run_btn = st.button(
                "▶  Convert Recipe", use_container_width=True, type="primary"
            )

            if run_btn:
                active_key = st.session_state.get("rc_api_key", "").strip()
                full_prompt = st.session_state.get("rc_prompt_value", "").strip()
                model_choice = st.session_state.get("rc_model", list(PRICES.keys())[0])
                recipe_name = st.session_state.get("rc_recipe_name", "my_recipe")
                system_message = st.session_state.get(
                    "rc_system_message", DEFAULT_SYSTEM_MESSAGE
                ).strip()
                temperature = st.session_state.get("rc_temperature", 0.0)

                errors = []
                if not active_key:
                    errors.append(
                        "Enter your OpenAI API key (or add it to the .env file)."
                    )
                if not full_prompt:
                    errors.append("Assembled prompt is empty — click 'Assemble' first.")
                if not system_message:
                    errors.append(
                        "System message is empty — enter a system message or reset to default."
                    )

                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    label = selected_shot_n if selected_shot_n != "manual" else "manual"
                    with st.spinner(f"Calling {model_choice} ({label} prompt)…"):
                        try:
                            result = run_conversion(
                                active_key,
                                full_prompt,
                                recipe_name,
                                model_choice,
                                system_message,
                                temperature=temperature,
                            )
                            result["shot_used"] = selected_shot_n
                            st.session_state["recipe_result"] = result
                            st.session_state["rc_panel_open"] = False
                            st.session_state["rc_panel_auto_collapsed"] = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"API error: {e}")

    if has_result:
        res = st.session_state["recipe_result"]

        with col_right:
            shot_label = res.get("shot_used", "?")
            shot_label = (
                f"{shot_label}-shot" if shot_label != "manual" else "manual prompt"
            )

            st.subheader("Results")
            st.caption(
                f"{shot_label} · {res['model']} · "
                f"temp {res.get('temperature', 0.0):.2f}"
            )

            m1, m2, m3, m4, m5 = st.columns(5)
            for col, lbl, val in [
                (m1, "In tokens", f"{res['input_tokens']:,}"),
                (m2, "Out tokens", f"{res['output_tokens']:,}"),
                (m3, "Total", f"{res['total_tokens']:,}"),
                (m4, "Cost", f"${res['cost']:.5f}"),
                (m5, "Time", f"{res['elapsed']:.1f}s"),
            ]:
                with col:
                    st.metric(lbl, val)

            st.divider()

            if res.get("parse_failed"):
                st.error(
                    f" Could not extract JSON from the model response: "
                    f"{res['parse_failed_reason']}\n\n"
                    "The raw output is shown below."
                )
                st.code(res["raw"], language="text")

            else:
                p_valid = res["process_validation"]["valid"]
                t_valid = res["taskstext_validation"]["valid"]

                if p_valid and t_valid:
                    st.success("Both files passed validation.")
                else:
                    failed = []
                    if not p_valid:
                        failed.append("process.json")
                    if not t_valid:
                        failed.append("taskTexts.json")
                    st.warning(
                        f"Validation issues detected in: {', '.join(failed)}. "
                        "See the **Validation** tab for details. Downloads are still available."
                    )

                p_str = json.dumps(res["process_json"], indent=2, ensure_ascii=False)
                t_str = json.dumps(res["task_texts_json"], indent=2, ensure_ascii=False)

                dl1, dl2, dl3, dl4 = st.columns(4)
                with dl1:
                    st.download_button(
                        "⬇ process.json",
                        data=p_str,
                        file_name=f"{res['recipe_name']}_process.json",
                        mime="application/json",
                        key="dl_p",
                        use_container_width=True,
                    )
                with dl2:
                    st.download_button(
                        "⬇ taskTexts.json",
                        data=t_str,
                        file_name=f"{res['recipe_name']}_taskTexts.json",
                        mime="application/json",
                        key="dl_t",
                        use_container_width=True,
                    )
                with dl3:
                    st.download_button(
                        "⬇ raw_output.txt",
                        data=res["raw"],
                        file_name=f"{res['recipe_name']}_raw_output.txt",
                        mime="text/plain",
                        key="dl_r",
                        use_container_width=True,
                    )
                with dl4:
                    st.download_button(
                        "⬇ analysis.txt",
                        data=res["analysis"] if res["analysis"] else "No analysis.",
                        file_name=f"{res['recipe_name']}_analysis.txt",
                        mime="text/plain",
                        key="dl_a",
                        use_container_width=True,
                    )

                st.divider()

                t1, t2, t3, t4, t5 = st.tabs(
                    [
                        " Analysis",
                        " process.json",
                        " taskTexts.json",
                        " Raw",
                        " Validation",
                    ]
                )

                with t1:
                    if res["analysis"]:
                        st.markdown(res["analysis"])
                    else:
                        st.info("No analysis text before the JSON blocks.")

                with t2:
                    n_tasks = len(res["process_json"].get("tasks", []))
                    n_trans = len(res["process_json"].get("transitions", []))
                    st.caption(f"{n_tasks} tasks · {n_trans} transitions")
                    st.code(p_str, language="json")

                with t3:
                    n_titles = len(res["task_texts_json"].get("titles", []))
                    n_descs = len(res["task_texts_json"].get("descriptions", []))
                    st.caption(f"{n_titles} titles · {n_descs} descriptions")
                    st.code(t_str, language="json")

                with t4:
                    st.code(res["raw"], language="text")

                with t5:
                    validation_results = {
                        "process.json": res["process_validation"],
                        "taskTexts.json": res["taskstext_validation"],
                    }
                    _display_validation_results(validation_results)
