import copy
import json
import uuid
import streamlit as st

EDITOR_ID = "_editor_id"


def ensure_generated_editor_ids(gen_data):

    for recipe in _iter_recipe_dicts(gen_data):
        for section_name in ("tasks", "transitions"):
            section = recipe.get(section_name)

            if not isinstance(section, list):
                continue

            for idx, item in enumerate(section):
                if isinstance(item, dict):
                    item.setdefault(EDITOR_ID, str(uuid.uuid4()))
                else:
                    section[idx] = {
                        EDITOR_ID: str(uuid.uuid4()),
                        "value": item,
                    }


def _iter_recipe_dicts(data):
    if isinstance(data, dict):
        if "tasks" in data or "transitions" in data:
            yield data
        else:
            for value in data.values():
                yield from _iter_recipe_dicts(value)

    elif isinstance(data, list):
        for item in data:
            yield from _iter_recipe_dicts(item)


def clean_generated_data_for_download(data):
    data_copy = copy.deepcopy(data)
    return _remove_editor_ids(data_copy)


def _remove_editor_ids(value):
    if isinstance(value, list):
        return [_remove_editor_ids(item) for item in value]

    if isinstance(value, dict):
        return {
            key: _remove_editor_ids(item)
            for key, item in value.items()
            if key != EDITOR_ID
        }

    return value


def render_modified_generated_download():
    if st.session_state.get("gen_data") is None:
        return

    cleaned_data = clean_generated_data_for_download(st.session_state.gen_data)

    st.download_button(
        label="Download modified generated file",
        data=json.dumps(cleaned_data, indent=2, ensure_ascii=False),
        file_name="modified_generated_structure.json",
        mime="application/json",
        key="download_modified_generated_structure",
    )


def render_generated_item_editor(item, key_prefix):

    if not isinstance(item, dict):
        st.write(item)
        return

    rows = [
        {
            "property": key,
            "value": value_to_text(value),
        }
        for key, value in item.items()
        if key != EDITOR_ID
    ]

    edited_rows = st.data_editor(
        rows,
        key=f"{key_prefix}_property_editor",
        hide_index=True,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "property": st.column_config.TextColumn(
                "Property",
                required=True,
                help="Edit existing property names or add new ones.",
            ),
            "value": st.column_config.TextColumn(
                "Value",
                help='Plain text or JSON: true, 5, null, ["a"], {"key": "value"}',
            ),
        },
    )

    editor_id = item.get(EDITOR_ID, str(uuid.uuid4()))
    updated_item = {EDITOR_ID: editor_id}

    for row in rows_to_records(edited_rows):
        prop = str(row.get("property", "")).strip()

        if not prop:
            continue

        if prop == EDITOR_ID:
            continue

        updated_item[prop] = parse_value(row.get("value", ""))

    item.clear()
    item.update(updated_item)


def value_to_text(value):
    if isinstance(value, (dict, list, int, float, bool)) or value is None:
        return json.dumps(value, ensure_ascii=False, indent=2)

    return str(value)


def parse_value(value):
    text = "" if value is None else str(value).strip()

    if text == "":
        return ""

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def rows_to_records(rows):
    if hasattr(rows, "to_dict"):
        return rows.to_dict("records")

    return rows
