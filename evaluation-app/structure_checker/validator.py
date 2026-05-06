import streamlit as st
from structure_checker.json_validator import (
    validate_json_file,
    validate_cross_file_references,
)
from config.config import PROCESS_JSON_SCHEMA, TASKS_TEXT_JSON_SCHEMA
from .helpers import _display_results, _display_schema_info


def render_validator_page():
    st.title("JSON Schema Validator")
    st.markdown(
        "Validate **process.json** and **tasksText.json** files against defined schemas "
        "using the **jsonschema** library."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("process.json")
        process_file = st.file_uploader(
            "Upload process.json",
            type=["json"],
            key="process",
            help="Upload your process.json file for validation",
        )

    with col2:
        st.subheader("tasksText.json")
        tasks_text_file = st.file_uploader(
            "Upload tasksText.json",
            type=["json"],
            key="taskstext",
            help="Upload your tasksText.json file for validation",
        )

    results = {}

    if process_file:
        content = process_file.read().decode("utf-8")
        results["process.json"] = validate_json_file(
            content, PROCESS_JSON_SCHEMA, "process"
        )

    if tasks_text_file:
        content = tasks_text_file.read().decode("utf-8")
        results["tasksText.json"] = validate_json_file(
            content, TASKS_TEXT_JSON_SCHEMA, "taskstext"
        )

    if "process.json" in results and "tasksText.json" in results:
        validate_cross_file_references(
            results["process.json"],
            results["tasksText.json"],
        )

    if results:
        _display_results(results)
    else:
        st.info("Upload JSON files to begin validation")
        _display_schema_info()
