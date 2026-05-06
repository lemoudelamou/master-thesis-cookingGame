import streamlit as st

from structure_comparator.file_management import render_file_management
from structure_comparator.process_comparison import render_process_comparison
from structure_comparator.text_comparison import render_text_comparison
from structure_comparator.task_display import render_identical_comparison
from structure_comparator.generated_editor import (
    ensure_generated_editor_ids,
    render_modified_generated_download,
)


def render_evaluator_page():

    initialize_session_state()

    st.title("Structure Comparison")

    render_file_management()

    if st.session_state.gen_data is not None:
        ensure_generated_editor_ids(st.session_state.gen_data)
        render_modified_generated_download()

    st.divider()

    if st.session_state.gt_data or st.session_state.gt_text_data:
        tabs = st.tabs(
            [
                "Process Comparison",
                "Identical Tasks",
                "Identical Transitions",
                "Text Comparison",
            ]
        )

        with tabs[0]:
            if st.session_state.gt_data and st.session_state.gen_data:
                render_process_comparison()
            else:
                st.info("Upload process JSON files to begin evaluation.")

        with tabs[1]:
            if st.session_state.gt_data and st.session_state.gen_data:
                gt_recipe, gen_recipe = get_current_recipe_pair()

                gt_tasks = (
                    gt_recipe.get("tasks", []) if isinstance(gt_recipe, dict) else []
                )
                gen_tasks = (
                    gen_recipe.get("tasks", []) if isinstance(gen_recipe, dict) else []
                )

                render_identical_comparison(
                    gt_tasks,
                    gen_tasks,
                    gt_tasks,
                    gen_tasks,
                    "",
                    item_type="tasks",
                )
            else:
                st.info("Upload process JSON files to compare identical tasks.")

        with tabs[2]:
            if st.session_state.gt_data and st.session_state.gen_data:
                gt_recipe, gen_recipe = get_current_recipe_pair()

                gt_transitions = (
                    gt_recipe.get("transitions", [])
                    if isinstance(gt_recipe, dict)
                    else []
                )
                gen_transitions = (
                    gen_recipe.get("transitions", [])
                    if isinstance(gen_recipe, dict)
                    else []
                )

                render_identical_comparison(
                    gt_transitions,
                    gen_transitions,
                    gt_transitions,
                    gen_transitions,
                    "",
                    item_type="transitions",
                )
            else:
                st.info("Upload process JSON files to compare identical transitions.")

        with tabs[3]:
            if st.session_state.gt_text_data and st.session_state.gen_text_data:
                render_text_comparison()
            else:
                st.info("Upload text JSON files to begin comparison.")

    else:
        st.info("Upload files to begin evaluation")


def initialize_session_state():
    if "evaluations" not in st.session_state:
        st.session_state.evaluations = {}

    if "current_recipe_idx" not in st.session_state:
        st.session_state.current_recipe_idx = 0

    if "scores" not in st.session_state:
        st.session_state.scores = {}

    if "gt_data" not in st.session_state:
        st.session_state.gt_data = None

    if "gen_data" not in st.session_state:
        st.session_state.gen_data = None

    if "recipes_list" not in st.session_state:
        st.session_state.recipes_list = []

    if "gt_text_data" not in st.session_state:
        st.session_state.gt_text_data = None

    if "gen_text_data" not in st.session_state:
        st.session_state.gen_text_data = None

    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "Process"


def get_current_recipe_pair():
    gt_data = st.session_state.gt_data
    gen_data = st.session_state.gen_data

    if isinstance(gt_data, dict) and ("tasks" in gt_data or "transitions" in gt_data):
        return gt_data, gen_data

    if isinstance(gt_data, dict):
        recipes = st.session_state.get("recipes_list", [])

        if recipes:
            recipe_name = recipes[0]
        else:
            recipe_name = next(iter(gt_data.keys()))

        return gt_data.get(recipe_name, {}), gen_data.get(recipe_name, {})

    if isinstance(gt_data, list) and gt_data:
        return gt_data[0], gen_data[0]

    return {}, {}
