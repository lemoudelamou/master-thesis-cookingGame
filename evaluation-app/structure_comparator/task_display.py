import uuid
import streamlit as st

from config.config import PROCESS_JSON_SCHEMA
from structure_comparator.generated_editor import (
    EDITOR_ID,
    render_generated_item_editor,
)


_DIALOG = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)


def _get_items_schema(section: str) -> dict:
    return PROCESS_JSON_SCHEMA["properties"][section]["items"]


def _schema_field_to_editor_meta(field_schema: dict) -> dict:
    description = field_schema.get("description", "")
    pattern = field_schema.get("pattern")
    enum_values = field_schema.get("enum")

    if enum_values:
        return {
            "type": "enum",
            "options": enum_values,
            "help": description,
        }

    if pattern == "^[01]$":
        return {
            "type": "enum01",
            "help": description,
        }

    if pattern == "^[0-9]+$":
        return {
            "type": "numeric_string",
            "help": description,
        }

    return {
        "type": "string",
        "help": description,
    }


def _schema_required(section: str) -> set[str]:
    return set(_get_items_schema(section).get("required", []))


def _schema_fields(section: str) -> dict:
    properties = _get_items_schema(section).get("properties", {})
    return {
        field: _schema_field_to_editor_meta(field_schema)
        for field, field_schema in properties.items()
    }


_TASK_REQUIRED = _schema_required("tasks")
_TASK_FIELDS = _schema_fields("tasks")

_TRANSITION_REQUIRED = _schema_required("transitions")
_TRANSITION_FIELDS = _schema_fields("transitions")


def _render_field(field: str, meta: dict, key: str, required: bool = False):
    label = f"{field}{' *' if required else ''}"
    ftype = meta["type"]
    help_text = meta.get("help", "")

    if ftype == "enum":
        options = ["(none)"] + list(meta.get("options", []))
        val = st.selectbox(label, options, key=key, help=help_text)
        return None if val == "(none)" else val

    if ftype == "enum01":
        options = ["(none)", "0", "1"]
        val = st.selectbox(label, options, key=key, help=help_text)
        return None if val == "(none)" else val

    if ftype == "numeric_string":
        val = st.text_input(label, key=key, help=help_text + " (digits only)")
        if val and not val.strip().isdigit():
            st.warning(f"'{field}' must be a numeric string (digits only).")
        return val.strip() or None

    val = st.text_input(label, key=key, help=help_text)
    return val.strip() or None


def _get_gen_recipe_section(section: str) -> list:
    gen_data = st.session_state.get("gen_data")

    if gen_data is None:
        return []

    if isinstance(gen_data, dict) and (
        "tasks" in gen_data or "transitions" in gen_data
    ):
        return gen_data.setdefault(section, [])

    if isinstance(gen_data, dict):
        recipes = st.session_state.get("recipes_list", [])
        recipe_name = recipes[0] if recipes else next(iter(gen_data.keys()), None)

        if recipe_name and isinstance(gen_data.get(recipe_name), dict):
            return gen_data[recipe_name].setdefault(section, [])

    if isinstance(gen_data, list) and gen_data:
        if isinstance(gen_data[0], dict):
            return gen_data[0].setdefault(section, [])

    return []


def _clear_add_task_form_state():
    for field in _TASK_FIELDS:
        st.session_state.pop(f"_add_task_req_{field}", None)
        st.session_state.pop(f"_add_task_opt_{field}", None)


def _clear_add_transition_form_state():
    for field in _TRANSITION_FIELDS:
        st.session_state.pop(f"_add_trans_req_{field}", None)
        st.session_state.pop(f"_add_trans_opt_{field}", None)


if _DIALOG is not None:

    @_DIALOG("➕ Add New Generated Task")
    def _render_add_task_form():
        st.markdown("#### Add New Generated Task")

        required_fields = [f for f in _TASK_FIELDS if f in _TASK_REQUIRED]
        optional_fields = [f for f in _TASK_FIELDS if f not in _TASK_REQUIRED]

        st.markdown("**Required fields**")
        req_values = {}
        req_cols = st.columns(2)

        for i, field in enumerate(required_fields):
            with req_cols[i % 2]:
                val = _render_field(
                    field,
                    _TASK_FIELDS[field],
                    key=f"_add_task_req_{field}",
                    required=True,
                )
                req_values[field] = val

        st.markdown("**Optional fields**")
        opt_values = {}

        with st.expander("Show optional fields", expanded=False):
            opt_cols = st.columns(2)

            for i, field in enumerate(optional_fields):
                with opt_cols[i % 2]:
                    val = _render_field(
                        field,
                        _TASK_FIELDS[field],
                        key=f"_add_task_opt_{field}",
                    )
                    opt_values[field] = val

        submit_col, cancel_col = st.columns(2)

        with submit_col:
            if st.button("Add Task", key="_add_task_btn", type="primary"):
                missing = [f for f in _TASK_REQUIRED if not req_values.get(f)]

                if missing:
                    st.warning(f"Required fields missing: {', '.join(missing)}")
                else:
                    new_task = {EDITOR_ID: str(uuid.uuid4())}

                    for f, v in req_values.items():
                        if v is not None:
                            new_task[f] = v

                    for f, v in opt_values.items():
                        if v is not None:
                            new_task[f] = v

                    _get_gen_recipe_section("tasks").append(new_task)
                    _clear_add_task_form_state()
                    st.rerun()

        with cancel_col:
            if st.button("Cancel", key="_cancel_add_task_btn"):
                _clear_add_task_form_state()
                st.rerun()

    @_DIALOG("➕ Add New Generated Transition")
    def _render_add_transition_form():
        st.markdown("#### Add New Generated Transition")

        required_fields = [f for f in _TRANSITION_FIELDS if f in _TRANSITION_REQUIRED]
        optional_fields = [
            f for f in _TRANSITION_FIELDS if f not in _TRANSITION_REQUIRED
        ]

        st.markdown("**Required fields**")
        req_values = {}
        req_cols = st.columns(2)

        for i, field in enumerate(required_fields):
            with req_cols[i % 2]:
                val = _render_field(
                    field,
                    _TRANSITION_FIELDS[field],
                    key=f"_add_trans_req_{field}",
                    required=True,
                )
                req_values[field] = val

        st.markdown("**Optional fields**")
        opt_values = {}

        with st.expander("Show optional fields", expanded=False):
            opt_cols = st.columns(2)

            for i, field in enumerate(optional_fields):
                with opt_cols[i % 2]:
                    val = _render_field(
                        field,
                        _TRANSITION_FIELDS[field],
                        key=f"_add_trans_opt_{field}",
                    )
                    opt_values[field] = val

        submit_col, cancel_col = st.columns(2)

        with submit_col:
            if st.button("Add Transition", key="_add_trans_btn", type="primary"):
                missing = [f for f in _TRANSITION_REQUIRED if not req_values.get(f)]

                if missing:
                    st.warning(f"Required fields missing: {', '.join(missing)}")
                else:
                    new_trans = {EDITOR_ID: str(uuid.uuid4())}

                    for f, v in req_values.items():
                        if v is not None:
                            new_trans[f] = v

                    for f, v in opt_values.items():
                        if v is not None:
                            new_trans[f] = v

                    _get_gen_recipe_section("transitions").append(new_trans)
                    _clear_add_transition_form_state()
                    st.rerun()

        with cancel_col:
            if st.button("Cancel", key="_cancel_add_trans_btn"):
                _clear_add_transition_form_state()
                st.rerun()

else:

    def _render_add_task_form_fallback():
        st.error(
            "Your Streamlit version does not support st.dialog or "
            "st.experimental_dialog. Please upgrade Streamlit."
        )

    def _render_add_transition_form_fallback():
        st.error(
            "Your Streamlit version does not support st.dialog or "
            "st.experimental_dialog. Please upgrade Streamlit."
        )

    _render_add_task_form = _render_add_task_form_fallback
    _render_add_transition_form = _render_add_transition_form_fallback


def render_task_comparison(filtered_gt, filtered_gen, gt_all, gen_all, search_term):
    st.subheader("Task Comparison")

    live_gen = _get_gen_recipe_section("tasks")
    shown_gen = filtered_gen if search_term else live_gen

    st.caption(
        f"**{'Search Results' if search_term else 'Total'}:** "
        f"{len(filtered_gt)} ground truth tasks | {len(shown_gen)} generated tasks"
    )

    add_col, _ = st.columns([1, 3])
    with add_col:
        if st.button("➕ Add Task", key="open_add_task_dialog", type="primary"):
            _render_add_task_form()

    if not filtered_gt and not live_gen:
        st.info("No tasks to display")
        return

    control_col1, control_col2 = st.columns(2)

    with control_col1:
        st.markdown("##### Ground Truth Controls")
        btn_col1, btn_col2 = st.columns(2)

        with btn_col1:
            if st.button("Expand All GT", key="expand_all_gt_tasks_btn"):
                for idx, item in enumerate(filtered_gt):
                    st.session_state[get_gt_task_toggle_key(item, idx)] = True

        with btn_col2:
            if st.button("Collapse All GT", key="collapse_all_gt_tasks_btn"):
                for idx, item in enumerate(filtered_gt):
                    st.session_state[get_gt_task_toggle_key(item, idx)] = False

    with control_col2:
        st.markdown("##### Generated Controls")
        btn_col1, btn_col2 = st.columns(2)

        with btn_col1:
            if st.button("Expand All Gen", key="expand_all_gen_tasks_btn"):
                for idx, item in enumerate(live_gen):
                    st.session_state[get_gen_task_toggle_key(item, idx)] = True

        with btn_col2:
            if st.button("Collapse All Gen", key="collapse_all_gen_tasks_btn"):
                for idx, item in enumerate(live_gen):
                    st.session_state[get_gen_task_toggle_key(item, idx)] = False

    st.divider()

    gt_col, gen_col = st.columns(2)

    with gt_col:
        st.markdown("#### Ground Truth Tasks")

        for gt_idx, gt_task in enumerate(filtered_gt):
            gt_name = (
                gt_task.get("name", "") if isinstance(gt_task, dict) else str(gt_task)
            )

            is_expanded = st.toggle(
                f"**{gt_idx + 1}. {gt_name}**",
                key=get_gt_task_toggle_key(gt_task, gt_idx),
            )

            if is_expanded:
                render_task_item(filtered_gt, gt_idx, is_gt=True)

            st.markdown("")

    with gen_col:
        st.markdown("#### Generated Tasks")

        to_delete = None

        for gen_idx, gen_task in enumerate(shown_gen):
            gen_name = (
                gen_task.get("name", "")
                if isinstance(gen_task, dict)
                else str(gen_task)
            )

            toggle_id = get_item_id(gen_task, gen_idx)
            toggle_key = get_gen_task_toggle_key(gen_task, gen_idx)

            is_expanded = st.toggle(
                f"**{gen_idx + 1}. {gen_name}**",
                key=toggle_key,
            )

            if is_expanded:
                if isinstance(gen_task, dict):
                    render_generated_item_editor(
                        gen_task,
                        key_prefix=f"gen_task_{toggle_id}",
                    )
                else:
                    render_task_item(shown_gen, gen_idx, is_gt=False)

                if st.button(
                    "🗑️ Delete this task",
                    key=f"del_task_{toggle_id}_{gen_idx}",
                    type="primary",
                ):
                    to_delete = gen_task

            st.markdown("")

        if to_delete is not None:
            live_gen[:] = [t for t in live_gen if t is not to_delete]
            st.rerun()


def render_transition_comparison(
    filtered_gt,
    filtered_gen,
    gt_all,
    gen_all,
    search_term,
):
    st.subheader("Transitions Comparison")

    live_gen = _get_gen_recipe_section("transitions")
    shown_gen = filtered_gen if search_term else live_gen

    st.caption(
        f"**{'Search Results' if search_term else 'Total'}:** "
        f"{len(filtered_gt)} ground truth transitions | "
        f"{len(shown_gen)} generated transitions"
    )

    add_col, _ = st.columns([1, 3])
    with add_col:
        if st.button(
            "➕ Add Transition",
            key="open_add_transition_dialog",
            type="primary",
        ):
            _render_add_transition_form()

    if not filtered_gt and not live_gen:
        st.info("No transitions to display")
        return

    control_col1, control_col2 = st.columns(2)

    with control_col1:
        st.markdown("##### Ground Truth Controls")
        btn_col1, btn_col2 = st.columns(2)

        with btn_col1:
            if st.button("Expand All GT", key="expand_all_gt_trans_btn"):
                for idx, item in enumerate(filtered_gt):
                    st.session_state[get_gt_transition_toggle_key(item, idx)] = True

        with btn_col2:
            if st.button("Collapse All GT", key="collapse_all_gt_trans_btn"):
                for idx, item in enumerate(filtered_gt):
                    st.session_state[get_gt_transition_toggle_key(item, idx)] = False

    with control_col2:
        st.markdown("##### Generated Controls")
        btn_col1, btn_col2 = st.columns(2)

        with btn_col1:
            if st.button("Expand All Gen", key="expand_all_gen_trans_btn"):
                for idx, item in enumerate(live_gen):
                    st.session_state[get_gen_transition_toggle_key(item, idx)] = True

        with btn_col2:
            if st.button("Collapse All Gen", key="collapse_all_gen_trans_btn"):
                for idx, item in enumerate(live_gen):
                    st.session_state[get_gen_transition_toggle_key(item, idx)] = False

    st.divider()

    gt_col, gen_col = st.columns(2)

    with gt_col:
        st.markdown("#### Ground Truth Transitions")

        for gt_idx, gt_trans in enumerate(filtered_gt):
            gt_info = get_transition_label(gt_trans)

            is_expanded = st.toggle(
                f"**{gt_idx + 1}. {gt_info}**",
                key=get_gt_transition_toggle_key(gt_trans, gt_idx),
            )

            if is_expanded:
                render_transition_item(filtered_gt, gt_idx, is_gt=True)

            st.markdown("")

    with gen_col:
        st.markdown("#### Generated Transitions")

        to_delete = None

        for gen_idx, gen_trans in enumerate(shown_gen):
            gen_info = get_transition_label(gen_trans)
            toggle_id = get_item_id(gen_trans, gen_idx)
            toggle_key = get_gen_transition_toggle_key(gen_trans, gen_idx)

            is_expanded = st.toggle(
                f"**{gen_idx + 1}. {gen_info}**",
                key=toggle_key,
            )

            if is_expanded:
                if isinstance(gen_trans, dict):
                    render_generated_item_editor(
                        gen_trans,
                        key_prefix=f"gen_trans_{toggle_id}",
                    )
                else:
                    render_transition_item(shown_gen, gen_idx, is_gt=False)

                if st.button(
                    "🗑️ Delete this transition",
                    key=f"del_trans_{toggle_id}_{gen_idx}",
                    type="primary",
                ):
                    to_delete = gen_trans

            st.markdown("")

        if to_delete is not None:
            live_gen[:] = [t for t in live_gen if t is not to_delete]
            st.rerun()


def render_task_item(task_list, idx, is_gt=True):
    if idx >= len(task_list):
        st.markdown(
            "_<span style='color: #888;'>No data</span>_",
            unsafe_allow_html=True,
        )
        return

    task = task_list[idx]
    bg_color = "#F1F8E9" if is_gt else "#FFF3E0"

    if isinstance(task, dict):
        for key, value in task.items():
            if key == EDITOR_ID:
                continue

            st.markdown(
                f"<div style='background-color: {bg_color}; "
                f"padding: 5px 8px; margin: 3px 0; border-radius: 3px;'>"
                f"<small>**{key}:** `{value}`</small></div>",
                unsafe_allow_html=True,
            )
    else:
        st.write(task)


def render_transition_item(trans_list, idx, is_gt=True):
    if idx >= len(trans_list):
        st.markdown(
            "_<span style='color: #888;'>No data</span>_",
            unsafe_allow_html=True,
        )
        return

    trans = trans_list[idx]
    bg_color = "#F1F8E9" if is_gt else "#FFF3E0"

    if isinstance(trans, dict):
        for key, value in trans.items():
            if key == EDITOR_ID:
                continue

            st.markdown(
                f"<div style='background-color: {bg_color}; "
                f"padding: 5px 8px; margin: 3px 0; border-radius: 3px;'>"
                f"<small>**{key}:** `{value}`</small></div>",
                unsafe_allow_html=True,
            )
    else:
        st.write(trans)


def render_identical_comparison(
    filtered_gt,
    filtered_gen,
    gt_all,
    gen_all,
    search_term,
    item_type="tasks",
):
    st.subheader(f"Identical {item_type.title()}")

    if search_term:
        st.caption(
            f"**Search Results:** {len(filtered_gt)} ground truth {item_type} | "
            f"{len(filtered_gen)} generated {item_type}"
        )
    else:
        st.caption(
            f"**Total:** {len(gt_all)} ground truth {item_type} | "
            f"{len(gen_all)} generated {item_type}"
        )

    def get_item_name(item):
        if isinstance(item, dict):
            if item_type == "transitions":
                parent = item.get("parent", "")
                child = item.get("child", "")
                return f"{parent} → {child}" if parent and child else ""

            return item.get("name", "")

        return str(item)

    gt_names = {
        get_item_name(item): (idx, item) for idx, item in enumerate(filtered_gt)
    }

    gen_names = {
        get_item_name(item): (idx, item) for idx, item in enumerate(filtered_gen)
    }

    identical_names = sorted(set(gt_names.keys()) & set(gen_names.keys()) - {""})

    if not identical_names:
        st.info(
            f"No identical {item_type} found between ground truth and generated data"
        )
        return

    st.success(f"Found {len(identical_names)} identical {item_type}")

    expand_key_prefix = f"identical_{item_type}_toggle"

    btn_col1, btn_col2 = st.columns(2)

    with btn_col1:
        if st.button("Expand All", key=f"expand_all_identical_{item_type}_btn"):
            for i in range(len(identical_names)):
                st.session_state[f"{expand_key_prefix}_{i}"] = True

    with btn_col2:
        if st.button("Collapse All", key=f"collapse_all_identical_{item_type}_btn"):
            for i in range(len(identical_names)):
                st.session_state[f"{expand_key_prefix}_{i}"] = False

    st.divider()

    for idx, name in enumerate(identical_names):
        gt_idx, gt_item = gt_names[name]
        gen_idx, gen_item = gen_names[name]

        is_expanded = st.toggle(
            f"**{idx + 1}. {name}**",
            key=f"{expand_key_prefix}_{idx}",
        )

        if is_expanded:
            gt_col, gen_col = st.columns(2)

            with gt_col:
                st.markdown("##### Ground Truth")
                render_item_details(gt_item, is_gt=True)

            with gen_col:
                st.markdown("##### Generated")

                if isinstance(gen_item, dict):
                    render_generated_item_editor(
                        gen_item,
                        key_prefix=(
                            f"identical_{item_type}_" f"{get_item_id(gen_item, idx)}"
                        ),
                    )
                else:
                    render_item_details(gen_item, is_gt=False)

        st.markdown("")


def render_item_details(item, is_gt=True):
    bg_color = "#F1F8E9" if is_gt else "#FFF3E0"

    if isinstance(item, dict):
        for key, value in item.items():
            if key == EDITOR_ID:
                continue

            st.markdown(
                f"<div style='background-color: {bg_color}; "
                f"padding: 5px 8px; margin: 3px 0; border-radius: 3px;'>"
                f"<small>**{key}:** `{value}`</small></div>",
                unsafe_allow_html=True,
            )
    else:
        st.write(item)


def get_transition_label(trans):
    if isinstance(trans, dict):
        parent = trans.get("parent", "")
        child = trans.get("child", "")

        if parent and child:
            return f"{parent} → {child}"

        clean_trans = {key: value for key, value in trans.items() if key != EDITOR_ID}

        return str(clean_trans)

    return str(trans)


def get_item_id(item, idx):
    if isinstance(item, dict):
        return item.get(EDITOR_ID, idx)

    return idx


def get_gt_task_toggle_key(item, idx):
    return f"gt_task_toggle_{idx}"


def get_gen_task_toggle_key(item, idx):
    return f"gen_task_toggle_{get_item_id(item, idx)}"


def get_gt_transition_toggle_key(item, idx):
    return f"gt_trans_toggle_{idx}"


def get_gen_transition_toggle_key(item, idx):
    return f"gen_trans_toggle_{get_item_id(item, idx)}"
