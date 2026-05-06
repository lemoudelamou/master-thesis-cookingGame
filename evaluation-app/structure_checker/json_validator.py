import json
import re
from jsonschema import Draft7Validator
from typing import Dict, Any, List, Set, Tuple

from .helpers import (
    _validate_transitions_parent_child,
    _validate_transitions_no_duplicates,
    _validate_taskstext_key_patterns,
    _compute_valid,
)


def validate_json_file(
    content: str, schema: Dict[str, Any], file_type: str
) -> Dict[str, Any]:

    checks = {
        "parseable": False,
        "schemaCompliant": False,
        "transitionsParentChildValid": False,
        "transitionsDuplicateValid": False,
        "ReferencesValid": True,
    }

    errors: List[str] = []
    error_details: Dict[str, List[str]] = {
        "parse_errors": [],
        "schema_errors": [],
        "parent_child_errors": [],
        "duplicate_transition_errors": [],
        "reference_errors": [],
    }
    data: Any = None

    try:
        data = json.loads(content)
        checks["parseable"] = True
    except json.JSONDecodeError as e:
        error_msg = f"Parse Error: {str(e)}"
        errors.append(error_msg)
        error_details["parse_errors"].append(error_msg)
        return {
            "checks": checks,
            "errors": errors,
            "error_details": error_details,
            "valid": False,
            "parsed_json": None,
        }

    validator = Draft7Validator(schema)
    raw_schema_errors = list(validator.iter_errors(data))

    checks["schemaCompliant"] = len(raw_schema_errors) == 0

    for error in raw_schema_errors:
        path = _format_error_path(error, data)
        error_msg = f"[{path}] {error.message}"
        errors.append(error_msg)
        error_details["schema_errors"].append(error_msg)

    if file_type == "process":
        checks["transitionsParentChildValid"] = _validate_transitions_parent_child(
            data, errors, error_details
        )
        checks["transitionsDuplicateValid"] = _validate_transitions_no_duplicates(
            data, errors, error_details
        )
    else:
        checks["transitionsParentChildValid"] = True
        checks["transitionsDuplicateValid"] = True

        key_patterns_valid = _validate_taskstext_key_patterns(
            data, errors, error_details
        )
        if not key_patterns_valid:
            checks["schemaCompliant"] = False

    return {
        "checks": checks,
        "errors": errors,
        "error_details": error_details,
        "valid": _compute_valid(checks, file_type),
        "parsed_json": data,
    }


def validate_cross_file_references(
    process_validation: Dict[str, Any],
    taskstext_validation: Dict[str, Any],
) -> None:

    _ensure_reference_bucket(process_validation)
    _ensure_reference_bucket(taskstext_validation)

    process_data = process_validation.get("parsed_json")
    tasktexts_data = taskstext_validation.get("parsed_json")

    if not isinstance(process_data, dict) or not isinstance(tasktexts_data, dict):
        process_validation["valid"] = _compute_valid(
            process_validation["checks"], "process"
        )
        taskstext_validation["valid"] = _compute_valid(
            taskstext_validation["checks"], "taskstext"
        )
        return

    tasks = process_data.get("tasks", [])
    transitions = process_data.get("transitions", [])

    if not isinstance(tasks, list):
        tasks = []
    if not isinstance(transitions, list):
        transitions = []

    titles_keys = _collect_key_set(tasktexts_data.get("titles", []))
    descriptions_keys = _collect_key_set(tasktexts_data.get("descriptions", []))
    feedbacks_keys = _collect_key_set(tasktexts_data.get("feedbacks", []))
    additionals_keys = _collect_key_set(tasktexts_data.get("additionals", []))

    # 1. duplicate task names -> process.json
    task_name_to_indexes: Dict[str, List[int]] = {}
    for i, task in enumerate(tasks):
        if isinstance(task, dict) and isinstance(task.get("name"), str):
            task_name_to_indexes.setdefault(task["name"], []).append(i)

    for name, indexes in task_name_to_indexes.items():
        if len(indexes) > 1:
            msg = f"Duplicate task name {name!r} found at task indexes {indexes}"
            _append_reference_error(process_validation, msg)

    task_names = set(task_name_to_indexes.keys())

    # 2. duplicate transition names -> process.json
    transition_name_to_indexes: Dict[str, List[int]] = {}
    for i, transition in enumerate(transitions):
        if isinstance(transition, dict) and isinstance(transition.get("name"), str):
            transition_name_to_indexes.setdefault(transition["name"], []).append(i)

    for name, indexes in transition_name_to_indexes.items():
        if len(indexes) > 1:
            msg = f"Duplicate transition name {name!r} found at transition indexes {indexes}"
            _append_reference_error(process_validation, msg)

    # 3. bad transition refs -> process.json
    for i, transition in enumerate(transitions):
        if not isinstance(transition, dict):
            continue

        parent = transition.get("parent")
        child = transition.get("child")

        if isinstance(parent, str) and parent not in task_names:
            msg = f"transitions[{i}].parent: {parent!r} does not reference an existing task name"
            _append_reference_error(process_validation, msg)

        if isinstance(child, str) and child not in task_names:
            msg = f"transitions[{i}].child: {child!r} does not reference an existing task name"
            _append_reference_error(process_validation, msg)

    # 4. missing task text refs -> taskTexts.json
    for i, task in enumerate(tasks):
        if not isinstance(task, dict):
            continue

        info_key = task.get("info")
        desc_key = task.get("description")
        feedback_key = task.get("feedback")
        additional_key = task.get("additional")

        if isinstance(info_key, str) and info_key not in descriptions_keys:
            msg = f"tasks[{i}].info: {info_key!r} not found in taskTexts.json -> descriptions"
            _append_reference_error(taskstext_validation, msg)

        if isinstance(desc_key, str) and desc_key not in titles_keys:
            msg = f"tasks[{i}].description: {desc_key!r} not found in taskTexts.json -> titles"
            _append_reference_error(taskstext_validation, msg)

        if isinstance(feedback_key, str) and feedback_key not in feedbacks_keys:
            msg = f"tasks[{i}].feedback: {feedback_key!r} not found in taskTexts.json -> feedbacks"
            _append_reference_error(taskstext_validation, msg)

        if isinstance(additional_key, str) and additional_key not in additionals_keys:
            msg = f"tasks[{i}].additional: {additional_key!r} not found in taskTexts.json -> additionals"
            _append_reference_error(taskstext_validation, msg)

    # 5. duplicate keys inside taskTexts -> taskTexts.json
    for section_name in [
        "titles",
        "descriptions",
        "informations",
        "feedbacks",
        "additionals",
    ]:
        arr = tasktexts_data.get(section_name, [])
        if not isinstance(arr, list):
            continue

        key_to_indexes: Dict[str, List[int]] = {}
        for i, item in enumerate(arr):
            if isinstance(item, dict) and isinstance(item.get("key"), str):
                key_to_indexes.setdefault(item["key"], []).append(i)

        for key, indexes in key_to_indexes.items():
            if len(indexes) > 1:
                msg = (
                    f"{section_name}: duplicate key {key!r} found at indexes {indexes}"
                )
                _append_reference_error(taskstext_validation, msg)

    process_validation["valid"] = _compute_valid(
        process_validation["checks"], "process"
    )
    taskstext_validation["valid"] = _compute_valid(
        taskstext_validation["checks"], "taskstext"
    )


def _ensure_reference_bucket(result: Dict[str, Any]) -> None:
    result.setdefault("checks", {})
    result.setdefault("errors", [])
    result.setdefault("error_details", {})
    result["checks"].setdefault("referenceValid", True)
    result["error_details"].setdefault("reference_errors", [])


def _append_reference_error(result: Dict[str, Any], message: str) -> None:
    result["checks"]["referenceValid"] = False

    if message not in result["errors"]:
        result["errors"].append(message)

    reference_errors = result["error_details"].setdefault("reference_errors", [])
    if message not in reference_errors:
        reference_errors.append(message)


def _collect_key_set(arr: Any) -> Set[str]:
    if not isinstance(arr, list):
        return set()
    keys = set()
    for item in arr:
        if isinstance(item, dict) and isinstance(item.get("key"), str):
            keys.add(item.get("key"))
    return keys


def _format_error_path(error, data: Any) -> str:

    if not error.path:
        return "root"

    parts = list(error.path)
    rendered: List[str] = []
    i = 0

    tasktext_sections = {
        "titles",
        "descriptions",
        "informations",
        "feedbacks",
        "additionals",
    }

    while i < len(parts):
        part = parts[i]

        if part == "tasks":
            rendered.append("tasks")
            if i + 1 < len(parts) and isinstance(parts[i + 1], int):
                idx = parts[i + 1]
                label = str(idx)
                tasks = data.get("tasks", [])
                if isinstance(tasks, list) and 0 <= idx < len(tasks):
                    task = tasks[idx]
                    if isinstance(task, dict) and isinstance(task.get("name"), str):
                        label = f"{idx} ({task['name']!r})"
                rendered.append(label)
                i += 2
                continue

        elif part == "transitions":
            rendered.append("transitions")
            if i + 1 < len(parts) and isinstance(parts[i + 1], int):
                idx = parts[i + 1]
                label = str(idx)
                transitions = data.get("transitions", [])
                if isinstance(transitions, list) and 0 <= idx < len(transitions):
                    transition = transitions[idx]
                    if isinstance(transition, dict) and isinstance(
                        transition.get("name"), str
                    ):
                        label = f"{idx} ({transition['name']!r})"
                rendered.append(label)
                i += 2
                continue

        elif part in tasktext_sections:
            rendered.append(str(part))
            if i + 1 < len(parts) and isinstance(parts[i + 1], int):
                idx = parts[i + 1]
                label = str(idx)
                arr = data.get(part, [])
                if isinstance(arr, list) and 0 <= idx < len(arr):
                    item = arr[idx]
                    if isinstance(item, dict) and isinstance(item.get("key"), str):
                        label = f"{idx} ({item['key']!r})"
                rendered.append(label)
                i += 2
                continue

        else:
            rendered.append(str(part))
            i += 1
            continue

        i += 1

    return " → ".join(rendered)
