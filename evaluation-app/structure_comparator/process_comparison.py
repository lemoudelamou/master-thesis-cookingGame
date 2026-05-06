import streamlit as st

from structure_comparator.filters import filter_tasks, filter_transitions
from structure_comparator.task_display import (
    render_task_comparison,
    render_transition_comparison,
)


def render_process_comparison():

    recipe_name, gt_recipe, gen_recipe = get_current_recipe_data()

    if not gt_recipe and not gen_recipe:
        st.error("No recipes available")
        return

    st.header(f"{recipe_name}")
    st.divider()

    gt_tasks = gt_recipe.get("tasks", []) if isinstance(gt_recipe, dict) else []
    gen_tasks = gen_recipe.get("tasks", []) if isinstance(gen_recipe, dict) else []

    gt_transitions = (
        gt_recipe.get("transitions", []) if isinstance(gt_recipe, dict) else []
    )
    gen_transitions = (
        gen_recipe.get("transitions", []) if isinstance(gen_recipe, dict) else []
    )

    search_col1, search_col2 = st.columns(2)

    with search_col1:
        task_search = st.text_input(
            "Search tasks by name",
            placeholder="e.g., knoblauch, aubergine",
            key="task_search",
        )

    with search_col2:
        transition_search = st.text_input(
            "Search transitions by parent",
            placeholder="e.g., knoblauch, aubergine",
            key="trans_search",
        )

    filtered_gt_tasks, filtered_gen_tasks = filter_tasks(
        gt_tasks,
        gen_tasks,
        task_search,
    )

    render_task_comparison(
        filtered_gt_tasks,
        filtered_gen_tasks,
        gt_tasks,
        gen_tasks,
        task_search,
    )

    if gt_transitions or gen_transitions:
        filtered_gt_trans, filtered_gen_trans = filter_transitions(
            gt_transitions,
            gen_transitions,
            transition_search,
        )

        render_transition_comparison(
            filtered_gt_trans,
            filtered_gen_trans,
            gt_transitions,
            gen_transitions,
            transition_search,
        )

    st.divider()


def get_current_recipe_data():
    gt_data = st.session_state.gt_data
    gen_data = st.session_state.gen_data
    recipes = st.session_state.get("recipes_list", [])

    if isinstance(gt_data, dict) and ("tasks" in gt_data or "transitions" in gt_data):
        return "Uploaded Recipe", gt_data, gen_data

    if isinstance(gt_data, dict):
        if recipes:
            recipe_name = recipes[0]
        else:
            recipe_name = next(iter(gt_data.keys()))

        return recipe_name, gt_data.get(recipe_name, {}), gen_data.get(recipe_name, {})

    if isinstance(gt_data, list) and gt_data:
        return "Recipe 1", gt_data[0], gen_data[0]

    return "No Recipe", {}, {}
