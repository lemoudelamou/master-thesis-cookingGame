import streamlit as st
import re
from typing import Dict, Any, List, Tuple
from config.config import (
    TASKS_TEXT_KEY_PATTERNS,
    TASKS_TEXT_KEY_EXAMPLES,
)


def _compute_valid(checks: Dict[str, bool], file_type: str) -> bool:

    if file_type == "taskstext":
        applicable = {
            k: v
            for k, v in checks.items()
            if k
            not in (
                "transitionsParentChildValid",
                "transitionsDuplicateValid",
            )
        }
        return all(applicable.values())
    return all(checks.values())


def _validate_taskstext_key_patterns(
    data: Any,
    errors: List[str],
    error_details: Dict[str, List[str]],
) -> bool:

    valid = True

    for array_name, pattern in TASKS_TEXT_KEY_PATTERNS.items():
        examples = TASKS_TEXT_KEY_EXAMPLES.get(array_name, "")
        compiled = re.compile(pattern)

        arr = data.get(array_name, [])
        if not isinstance(arr, list):
            continue

        for idx, item in enumerate(arr):
            if not isinstance(item, dict):
                continue

            key = item.get("key", "")
            if not isinstance(key, str):
                continue

            if not compiled.fullmatch(key):
                item_label = f"{array_name}[{idx}]"
                if isinstance(item.get("key"), str):
                    item_label = f"{array_name}[{idx}] ({item['key']!r})"

                msg = (
                    f"{item_label}: key {repr(key)} does not match "
                    f'expected pattern "{pattern}" '
                    f"(examples: {examples})"
                )
                if msg not in errors:
                    errors.append(msg)
                if msg not in error_details["schema_errors"]:
                    error_details["schema_errors"].append(msg)
                valid = False

    return valid


def _validate_transitions_parent_child(
    data: Any,
    errors: List[str],
    error_details: Dict[str, List[str]],
) -> bool:
    valid = True

    transitions = data.get("transitions", [])
    if not isinstance(transitions, list):
        return True

    for idx, transition in enumerate(transitions):
        if not isinstance(transition, dict):
            continue

        name = transition.get("name", f"index {idx}")
        parent = transition.get("parent")
        child = transition.get("child")
        if parent is not None and child is not None and parent == child:
            msg = (
                f"In {repr(name)}: 'parent' and 'child' must differ "
                f"(both are {repr(parent)})"
            )
            errors.append(msg)
            error_details["parent_child_errors"].append(msg)
            valid = False
    return valid


def _validate_transitions_no_duplicates(
    data: Any,
    errors: List[str],
    error_details: Dict[str, List[str]],
) -> bool:
    seen_pairs: Dict[Tuple[Any, Any], int] = {}
    valid = True

    transitions = data.get("transitions", [])
    if not isinstance(transitions, list):
        return True

    for idx, transition in enumerate(transitions):
        if not isinstance(transition, dict):
            continue

        name = transition.get("name", f"index {idx}")
        parent = transition.get("parent")
        child = transition.get("child")
        if parent is not None and child is not None:
            pair = (parent, child)
            if pair in seen_pairs:
                first_transition = transitions[seen_pairs[pair]]
                first_name = (
                    first_transition.get("name", f"index {seen_pairs[pair]}")
                    if isinstance(first_transition, dict)
                    else f"index {seen_pairs[pair]}"
                )
                msg = (
                    f"The {repr(name)} duplicate of {repr(first_name)} "
                    f"(parent={repr(parent)}, child={repr(child)})"
                )
                errors.append(msg)
                error_details["duplicate_transition_errors"].append(msg)
                valid = False
            else:
                seen_pairs[pair] = idx

    return valid


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


def _effective_checks(filename: str, checks: dict, both_files_present: bool) -> dict:
    excluded = set()

    if filename == "tasksText.json":
        excluded.update(
            {
                "transitionsParentChildValid",
                "transitionsDuplicateValid",
            }
        )

    if not both_files_present:
        excluded.add("referenceValid")

    return {k: v for k, v in checks.items() if k not in excluded}


def _compute_sv_score(
    results: dict, both_files_present: bool
) -> tuple[float, int, int]:
    """
    Compute SV Score by treating every check as equal weight.
    Shared checks (referenceValid) are counted once, not twice.

    Returns (score_percent, passed, total).

    Check inventory (both files present = 7 total):
      process-exclusive (4): parseable, schemaCompliant,
                              transitionsParentChildValid,
                              transitionsDuplicateValid
      taskstext-exclusive (2): parseable, schemaCompliant
      shared (1):              referenceValid
    """
    passed = 0
    total = 0

    if "process.json" in results:
        p_checks = results["process.json"]["checks"]
        for key in (
            "parseable",
            "schemaCompliant",
            "transitionsParentChildValid",
            "transitionsDuplicateValid",
        ):
            total += 1
            if p_checks.get(key, False):
                passed += 1

    if "tasksText.json" in results:
        t_checks = results["tasksText.json"]["checks"]
        for key in ("parseable", "schemaCompliant"):
            total += 1
            if t_checks.get(key, False):
                passed += 1

    if both_files_present:
        # Count referenceValid once — both files must pass
        ref_process = results["process.json"]["checks"].get("referenceValid", True)
        ref_taskstext = results["tasksText.json"]["checks"].get("referenceValid", True)
        total += 1
        if ref_process and ref_taskstext:
            passed += 1

    score = (passed / total * 100) if total else 0.0
    return score, passed, total


def _display_results(results: dict):
    """Display validation statistics and details."""
    st.markdown("---")
    st.header("Validation Statistics")

    both_files_present = "process.json" in results and "tasksText.json" in results

    total_files = len(results)
    valid_files = 0

    for filename, result in results.items():
        effective_checks = _effective_checks(
            filename, result["checks"], both_files_present
        )
        passed = sum(1 for v in effective_checks.values() if v)
        applicable = len(effective_checks)
        if applicable > 0 and passed == applicable:
            valid_files += 1

    sv_score, passed_checks, total_checks = _compute_sv_score(
        results, both_files_present
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Files", total_files)
    with col2:
        st.metric("Valid Files", valid_files)
    with col3:
        if both_files_present:
            st.metric(
                "SV Score",
                f"{sv_score:.1f}%",
                help=f"{passed_checks}/{total_checks} checks passed",
            )
        else:
            st.metric("SV Score", "N/A")
            st.caption(" Upload both files for a complete SV Score")

    _display_check_rates(results, both_files_present)

    st.markdown("---")
    st.header("Detailed Results")

    for filename, result in results.items():
        _display_file_result(filename, result, both_files_present)


def _display_check_rates(results: dict, both_files_present: bool):
    st.subheader("Check Pass Rates")

    # --- process.json exclusive ---
    if "process.json" in results:
        st.caption("process.json")
        p_checks = results["process.json"]["checks"]
        process_check_labels = {
            "parseable": "1. JSON Parsability",
            "schemaCompliant": "2. Schema Compliance",
            "transitionsParentChildValid": "3. Parent ≠ Child",
            "transitionsDuplicateValid": "4. No Duplicate Transitions",
        }
        for key, label in process_check_labels.items():
            passed = float(p_checks.get(key, False))
            st.progress(
                passed,
                text=f"{label}: {'✓' if passed else '✗'} ({100 * passed:.0f}%)",
            )

    if "tasksText.json" in results:
        st.caption("tasksText.json")
        t_checks = results["tasksText.json"]["checks"]
        taskstext_check_labels = {
            "parseable": "1. JSON Parsability",
            "schemaCompliant": "2. Schema Compliance",
        }
        for key, label in taskstext_check_labels.items():
            passed = float(t_checks.get(key, False))
            st.progress(
                passed,
                text=f"{label}: {'✓' if passed else '✗'} ({100 * passed:.0f}%)",
            )

    if both_files_present:
        st.caption("Shared (both files)")
        ref_process = results["process.json"]["checks"].get("referenceValid", True)
        ref_taskstext = results["tasksText.json"]["checks"].get("referenceValid", True)
        both_pass = ref_process and ref_taskstext
        st.progress(
            float(both_pass),
            text=f"5. Reference Validity: {'✓' if both_pass else '✗'} ({100 * float(both_pass):.0f}%)",
        )


def _display_file_result(filename: str, result: dict, both_files_present: bool):
    """Display validation result for a single file."""
    check_labels = {
        "parseable": "Parsability",
        "schemaCompliant": "Schema",
        "referenceValid": "Reference Validity",
    }

    if filename == "process.json":
        check_labels.update(
            {
                "transitionsParentChildValid": "Parent ≠ Child",
                "transitionsDuplicateValid": "No Duplicate Transitions",
            }
        )

    if not both_files_present:
        check_labels.pop("referenceValid", None)

    effective_checks = {key: result["checks"].get(key, False) for key in check_labels}
    file_valid = bool(effective_checks) and all(effective_checks.values())

    with st.expander(f" {filename}", expanded=not file_valid):
        if file_valid:
            st.markdown(
                _color_badge("All validation checks passed!", "#27ae60"),
                unsafe_allow_html=True,
            )
            st.write("")
        else:
            failed = sum(1 for v in effective_checks.values() if not v)
            st.markdown(
                _color_badge(f"Failed {failed} validation check(s)", "#c0392b"),
                unsafe_allow_html=True,
            )
            st.write("")

        st.subheader("Validation Checks")
        cols = st.columns(len(check_labels))
        for idx, (key, label) in enumerate(check_labels.items()):
            with cols[idx]:
                if effective_checks.get(key, False):
                    st.success(f"✓\n{label}")
                else:
                    st.error(f"✗\n{label}")

        if result.get("error_details"):
            _display_categorized_errors(
                result["error_details"], filename, both_files_present
            )
        elif result.get("errors"):
            st.subheader(f"Validation Errors ({len(result['errors'])})")
            for i, error in enumerate(result["errors"], 1):
                st.markdown(f"**{i}.** {error}")


def _display_categorized_errors(
    error_details: dict, filename: str, both_files_present: bool
):
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
        ("reference_errors", "Cross-file references, uniqueness"),
    ]

    total_errors = 0
    for error_key, _ in error_categories:
        if filename == "tasksText.json" and error_key in (
            "parent_child_errors",
            "duplicate_transition_errors",
        ):
            continue
        if error_key == "reference_errors" and not both_files_present:
            continue
        total_errors += len(error_details.get(error_key, []))

    if total_errors == 0:
        return

    st.subheader(f"Validation Errors ({total_errors} total)")

    for error_key, description in error_categories:
        if filename == "tasksText.json" and error_key in (
            "parent_child_errors",
            "duplicate_transition_errors",
        ):
            continue

        if error_key == "reference_errors" and not both_files_present:
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


def _display_schema_info():
    with st.expander("Schema Information & Validation Criteria"):
        st.markdown(
            """
### Validation Checks

#### 1. JSON Parsability
- File must be valid JSON
- **Error Type:** Parse Errors

#### 2. Schema Compliance
- Required fields must exist
- Structure must match the defined schema
- Unexpected fields are not allowed
- Types must match the schema
- String patterns and enum constraints must match the schema
- **Error Type:** Schema Errors

#### 3. Transitions Parent ≠ Child (**process.json only**)
- `parent` and `child` cannot be the same value
- **Error Type:** Parent-Child Errors

#### 4. No Duplicate Transitions (**process.json only**)
- No two transitions can share the same `parent` and `child`
- **Error Type:** Duplicate Transition Errors

#### 5. Reference Validity (**requires both files**)
- Transition `parent` and `child` must reference existing task names
- `task.info` must exist in `tasksText.json -> descriptions`
- `task.description` must exist in `tasksText.json -> titles`
- `task.feedback` must exist in `tasksText.json -> feedbacks`
- `task.additional` must exist in `tasksText.json -> additionals`
- Duplicate task names are not allowed
- Duplicate transition names are not allowed
- Duplicate keys inside tasksText sections are not allowed
- **Error Type:** Reference Errors

> Cross-file reference validation runs only when **both** files are uploaded.
        """
        )
