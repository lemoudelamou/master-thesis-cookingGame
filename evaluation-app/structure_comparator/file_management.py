import json
import streamlit as st

from structure_comparator.generated_editor import ensure_generated_editor_ids


def render_file_management():
    st.header("File Management")

    file_type = st.selectbox(
        "Select file type:",
        ["Process Files", "Text Files"],
        key="file_type_select",
    )

    if file_type == "Process Files":
        render_process_file_upload()
    else:
        render_text_file_upload()


def render_process_file_upload():
    col1, col2 = st.columns(2)

    with col1:
        gt_file = st.file_uploader(
            "Upload Ground Truth Process JSON",
            type="json",
            key="gt_process",
        )

    with col2:
        gen_file = st.file_uploader(
            "Upload Generated Process JSON",
            type="json",
            key="gen_process",
        )

    if gt_file and gen_file:
        if st.button("Load Process Files", key="load_process_files_btn"):
            clear_process_ui_state()

            gt_file.seek(0)
            gen_file.seek(0)

            st.session_state.gt_data = json.load(gt_file)
            st.session_state.gen_data = json.load(gen_file)
            st.session_state.active_tab = "Process"

            ensure_generated_editor_ids(st.session_state.gen_data)

            st.session_state.recipes_list = extract_recipe_list(
                st.session_state.gt_data
            )

            st.success(f"Loaded {len(st.session_state.recipes_list)} recipe(s)")


def render_text_file_upload():
    col1, col2 = st.columns(2)

    with col1:
        gt_text_file = st.file_uploader(
            "Upload Ground Truth Text JSON",
            type="json",
            key="gt_text",
        )

    with col2:
        gen_text_file = st.file_uploader(
            "Upload Generated Text JSON",
            type="json",
            key="gen_text",
        )

    if gt_text_file and gen_text_file:
        if st.button("Load Text Files", key="load_text_files_btn"):
            clear_text_ui_state()

            gt_text_file.seek(0)
            gen_text_file.seek(0)

            st.session_state.gt_text_data = json.load(gt_text_file)
            st.session_state.gen_text_data = json.load(gen_text_file)
            st.session_state.active_tab = "Text"

            st.success("Loaded text files")


def extract_recipe_list(gt_data):

    if isinstance(gt_data, dict) and ("tasks" in gt_data or "transitions" in gt_data):
        return ["Recipe"]

    if isinstance(gt_data, dict):
        return list(gt_data.keys())

    if isinstance(gt_data, list):
        return [f"Recipe {i + 1}" for i in range(len(gt_data))]

    return []


def clear_process_ui_state():

    prefixes_to_clear = (
        "gt_task_toggle_",
        "gen_task_toggle_",
        "gt_trans_toggle_",
        "gen_trans_toggle_",
        "identical_tasks_toggle_",
        "identical_transitions_toggle_",
        "gen_task_",
        "gen_trans_",
        "identical_tasks_",
        "identical_transitions_",
        "expand_all_gt_tasks",
        "expand_all_gen_tasks",
        "expand_all_gt_trans",
        "expand_all_gen_trans",
    )

    keys_to_delete = [
        key for key in st.session_state.keys() if key.startswith(prefixes_to_clear)
    ]

    for key in keys_to_delete:
        del st.session_state[key]


def clear_text_ui_state():

    prefixes_to_clear = (
        "gt_section_toggle_",
        "gen_section_toggle_",
        "expanded_gt_sections",
        "expanded_gen_sections",
    )

    keys_to_delete = [
        key
        for key in st.session_state.keys()
        if key.startswith(prefixes_to_clear) or key in prefixes_to_clear
    ]

    for key in keys_to_delete:
        del st.session_state[key]
