import copy
import csv
import io
import json as json_lib
from typing import Any, Dict, List, Optional, Set

import streamlit as st

from assets_checker.utils import group_by_folder
from config.config import IMAGE_FIELDS, SOUND_FIELDS, TOOL_FIELDS
from assets_checker.helpers import (
    render_statistics_row,
    render_progress_section,
    render_info_box,
    render_asset_grid,
    render_grouped_assets,
    render_search_filter,
    render_download_buttons,
)


DEFAULT_PATCH_ASSET_FIELDS: Set[str] = set(IMAGE_FIELDS + SOUND_FIELDS + TOOL_FIELDS)


def render_found_tab(
    assets: Set[str],
    asset_type: str,
    asset_paths: Optional[Dict[str, str]] = None,
    allow_grouping: bool = False,
    search_key: str = "search",
):
    st.subheader(f"Found {asset_type.title()} ({len(assets)})")

    if assets:
        filtered = render_search_filter(
            assets,
            key=search_key,
            label=f"Search found {asset_type}",
        )

        if allow_grouping and asset_paths:
            use_grouping = st.checkbox(
                "Group by folder", value=False, key=f"{search_key}_group"
            )
            if use_grouping:
                grouped = group_by_folder(filtered, asset_paths)
                extra_info = {
                    k: f"`{asset_paths[k]}`" for k in filtered if k in asset_paths
                }
                render_grouped_assets(grouped, show_success=True, extra_info=extra_info)
            else:
                extra_info = {
                    k: f"Path: `{asset_paths[k]}`" for k in filtered if k in asset_paths
                }
                render_asset_grid(
                    filtered,
                    asset_type,
                    columns=3,
                    show_success=True,
                    extra_info=extra_info,
                )
        else:
            render_asset_grid(filtered, asset_type, columns=4, show_success=True)

        st.download_button(
            label=f" Download Found {asset_type.title()} (TXT)",
            data="\n".join(sorted(assets)),
            file_name=f"found_{asset_type}.txt",
            mime="text/plain",
        )
    else:
        st.info(f"No {asset_type} from your JSON were found in the reference.")


def render_missing_tab(
    assets: Set[str],
    asset_type: str,
    format_func,
    search_key: str = "search_missing",
):
    st.subheader(f"Missing {asset_type.title()} ({len(assets)})")

    if assets:
        st.warning(
            f"**These {len(assets)} {asset_type} are referenced in your JSON "
            f"but NOT found in the reference.**\n\nYou may need to add them!"
        )
        filtered = render_search_filter(
            assets, key=search_key, label=f"Search missing {asset_type}"
        )
        render_asset_grid(
            filtered,
            asset_type,
            columns=3 if asset_type == "images" else 4,
            show_success=False,
        )
        render_download_buttons(
            [
                {
                    "label": f"Download Missing {asset_type.title()} (TXT)",
                    "data": "\n".join(sorted(assets)),
                    "filename": f"missing_{asset_type}.txt",
                },
                {
                    "label": "Download as Python Format",
                    "data": format_func(assets),
                    "filename": f"missing_{asset_type}_python.txt",
                },
            ]
        )
    else:
        st.success(f"All {asset_type} in your JSON are found in the reference!")


def _apply_replacements(
    obj: Any, replacements: Dict[str, str], asset_fields: Set[str]
) -> Any:

    if isinstance(obj, dict):
        return {
            key: (
                replacements.get(value, value)
                if key in asset_fields and isinstance(value, str)
                else _apply_replacements(value, replacements, asset_fields)
            )
            for key, value in obj.items()
        }
    if isinstance(obj, list):
        return [_apply_replacements(item, replacements, asset_fields) for item in obj]
    return obj


def _build_detailed_csv(
    assets_with_sources: Dict[str, List[Dict[str, str]]],
    replacements: Dict[str, str],
) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Asset Key",
            "Original Value",
            "Replacement",
            "JSON Key",
            "Field",
            "Parent",
            "Child",
        ]
    )
    for asset in sorted(assets_with_sources.keys()):
        for source in assets_with_sources[asset]:
            original_value = source["original_value"]
            writer.writerow(
                [
                    asset,
                    original_value,
                    replacements.get(original_value, original_value),
                    source["json_key"],
                    source["field"],
                    source.get("parent", ""),
                    source.get("child", ""),
                ]
            )
    return output.getvalue()


def _render_replacement_input(
    original_value: str,
    used_fields: List[str],
    replacements: Dict[str, str],
    widget_key: str,
    reset_key: str,
    help_text: str,
):

    current_value = st.session_state.get(
        widget_key, replacements.get(original_value, original_value)
    )

    col_input, col_reset = st.columns([5, 1])
    with col_input:
        new_value = st.text_input(
            "Replace with",
            value=current_value,
            key=widget_key,
            help=help_text + f" Affects fields: {', '.join(used_fields)}.",
        )
    with col_reset:
        st.write("")
        if st.button("↺", key=reset_key, help="Reset to original"):
            replacements.pop(original_value, None)
            if widget_key in st.session_state:
                del st.session_state[widget_key]
            st.rerun()

    cleaned = new_value.strip()
    if cleaned and cleaned != original_value:
        replacements[original_value] = cleaned
    elif original_value in replacements and cleaned == original_value:
        del replacements[original_value]

    if replacements.get(original_value, original_value) != original_value:
        st.success(f"`{original_value}` → `{replacements[original_value]}`")


def _render_usages(sources: List[Dict[str, str]], show_transition_context: bool):
    st.markdown(f"**Used {len(sources)} time(s) in your JSON:**")
    for idx, source in enumerate(sources, 1):
        parent = source.get("parent", "")
        child = source.get("child", "")
        base = (
            f"#{idx} — key: `{source['json_key']}` · "
            f"field: `{source['field']}` · "
            f"value: `{source['original_value']}`"
        )
        if show_transition_context and (parent or child):
            col_caption, col_transition = st.columns([2, 3])
            with col_caption:
                st.caption(base)
            with col_transition:
                st.caption(f" `{parent or '—'}` → `{child or '—'}`")
        else:
            suffix = (
                f" ·  `{parent or '—'}` → `{child or '—'}`"
                if show_transition_context
                else ""
            )
            st.caption(base + suffix)


def _render_patch_preview_and_downloads(
    original_json: dict,
    replacements: Dict[str, str],
    fields_to_patch: Set[str],
    asset_type: str,
    assets_for_lists,
    format_func,
    search_key: str,
    tab_kind: str,
):

    active_replacements = {ov: rep for ov, rep in replacements.items() if rep != ov}
    patched = _apply_replacements(
        copy.deepcopy(original_json), active_replacements, fields_to_patch
    )
    patched_json_str = json_lib.dumps(patched, indent=2, ensure_ascii=False)

    total_modified = sum(1 for rep in replacements.values() if rep != "")

    st.divider()
    st.subheader("Live preview")

    if active_replacements:
        st.success(
            f"**{len(active_replacements)} total replacement(s)** active across all tabs — "
            "only asset field values are changed. Task and transition names are untouched."
        )
    else:
        st.info("Edit replacement values above — the JSON will update here instantly.")

    with st.expander("Raw JSON zum Kopieren"):
        st.code(patched_json_str, language="json")

    st.divider()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            label="Patched JSON",
            data=patched_json_str,
            file_name="patched_output.json",
            mime="application/json",
            key=f"{search_key}_dl_patched",
            help="Full JSON with replacement asset values applied.",
        )
    with col2:
        label_kind = "Found" if tab_kind == "found" else "Missing"
        st.download_button(
            label=f"{label_kind} List (TXT)",
            data="\n".join(sorted(assets_for_lists)),
            file_name=f"{tab_kind}_{asset_type}.txt",
            mime="text/plain",
            key=f"{search_key}_dl_txt",
        )
    with col3:
        st.download_button(
            label=" Python Format",
            data=format_func(set(assets_for_lists)),
            file_name=f"{tab_kind}_{asset_type}_python.txt",
            mime="text/plain",
            key=f"{search_key}_dl_py",
        )

    st.divider()

    if isinstance(assets_for_lists, dict):
        sources_for_csv = {
            k: v["sources"] if isinstance(v, dict) else v
            for k, v in assets_for_lists.items()
        }
    else:
        sources_for_csv = {a: [] for a in assets_for_lists}

    st.download_button(
        label=" Detailed Report (CSV)",
        data=_build_detailed_csv(sources_for_csv, replacements),
        file_name=f"{tab_kind}_{asset_type}_detailed.csv",
        mime="text/csv",
        key=f"{search_key}_dl_csv",
        help="Includes Original Value, Replacement, Parent, and Child columns.",
    )


def _render_assets_with_sources_tab(
    assets_data: Dict[str, Any],
    asset_type: str,
    format_func,
    original_json: dict,
    asset_fields: Set[str],
    all_asset_fields: Optional[Set[str]],
    asset_paths: Optional[Dict[str, str]],
    search_key: str,
    show_transition_context: bool,
    tab_kind: str,
):

    fields_to_patch = all_asset_fields or DEFAULT_PATCH_ASSET_FIELDS

    is_found = tab_kind == "found"
    label_title = "Found" if is_found else "Missing"
    empty_icon = "✓" if is_found else "⚠️"

    st.subheader(f"{label_title} {asset_type.title()} ({len(assets_data)})")

    if not assets_data:
        if is_found:
            st.info(f"No {asset_type} from your JSON were found in the reference.")
        else:
            st.success(f"All {asset_type} in your JSON are found in the reference!")
        return

    if is_found:
        st.info(
            f"**{len(assets_data)} {asset_type}** were found in the reference. "
            f"You can optionally remap any of them below."
        )
    else:
        st.warning(
            f"**{len(assets_data)} {asset_type}** are referenced in your JSON "
            f"but NOT found in the reference. Edit replacement values below, then "
            f"download the patched JSON."
        )

    if "global_replacements" not in st.session_state:
        st.session_state["global_replacements"] = {}
    replacements: Dict[str, str] = st.session_state["global_replacements"]

    def _normalise(data: Dict[str, Any]) -> Dict[str, Dict]:
        result = {}
        for k, v in data.items():
            if isinstance(v, list):
                result[k] = {"sources": v, "matched_variants": []}
            else:
                result[k] = v
        return result

    normalised = _normalise(assets_data)

    search_term = st.text_input(f"Search {tab_kind} {asset_type}", key=search_key)
    filtered = {
        k: v
        for k, v in normalised.items()
        if not search_term or search_term.lower() in k.lower()
    }

    all_original_values = {
        source["original_value"]
        for info in normalised.values()
        for source in info["sources"]
    }
    modified_count = sum(
        1 for ov in all_original_values if replacements.get(ov, ov) != ov
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.caption(f"Showing {len(filtered)} of {len(normalised)} {asset_type}")
    with col_b:
        verb = "remapped" if is_found else "modified"
        st.caption(
            f"✏️ {modified_count} {verb}"
            if modified_count
            else f"No {'remaps' if is_found else 'edits'} yet"
        )

    help_text = (
        "Optionally remap this asset to a different value. Leave unchanged to keep the original."
        if is_found
        else "Enter only the raw asset value, e.g. `common/new_asset`, not a full JSON line. "
        "This value will replace the original everywhere it appears in these fields."
    )

    for asset in sorted(filtered.keys()):
        info = filtered[asset]
        sources: List[Dict[str, str]] = info["sources"]
        matched_variants: List[str] = info.get("matched_variants", [])

        original_values = list(dict.fromkeys(s["original_value"] for s in sources))
        is_modified = any(replacements.get(ov, ov) != ov for ov in original_values)
        label_icon = "✏️" if is_modified else empty_icon

        with st.expander(
            f"{label_icon} {asset} — {len(sources)} usage(s)", expanded=False
        ):
            if matched_variants:
                st.markdown("**Matched reference variant(s):**")
                for v in matched_variants:
                    if asset_paths and v in asset_paths:
                        st.code(f"{v} → {asset_paths[v]}", language="")
                    else:
                        st.code(v, language="")
                st.divider()

            for i, original_value in enumerate(original_values):
                st.markdown(f"**Original value in JSON:** `{original_value}`")
                used_fields = sorted(
                    {
                        s["field"]
                        for s in sources
                        if s["original_value"] == original_value
                    }
                )
                _render_replacement_input(
                    original_value=original_value,
                    used_fields=used_fields,
                    replacements=replacements,
                    widget_key=f"{search_key}_input_{original_value}",
                    reset_key=f"{search_key}_reset_{original_value}",
                    help_text=help_text,
                )
                if i < len(original_values) - 1:
                    st.divider()

            _render_usages(sources, show_transition_context)

    _render_patch_preview_and_downloads(
        original_json=original_json,
        replacements=replacements,
        fields_to_patch=fields_to_patch,
        asset_type=asset_type,
        assets_for_lists=assets_data,
        format_func=format_func,
        search_key=search_key,
        tab_kind=tab_kind,
    )


def render_found_tab_with_sources(
    found_assets: Dict[str, Dict[str, Any]],
    asset_type: str,
    format_func,
    original_json: dict,
    asset_fields: Set[str],
    all_asset_fields: Optional[Set[str]] = None,
    asset_paths: Optional[Dict[str, str]] = None,
    search_key: str = "search_found",
    show_transition_context: bool = False,
):
    _render_assets_with_sources_tab(
        assets_data=found_assets,
        asset_type=asset_type,
        format_func=format_func,
        original_json=original_json,
        asset_fields=asset_fields,
        all_asset_fields=all_asset_fields,
        asset_paths=asset_paths,
        search_key=search_key,
        show_transition_context=show_transition_context,
        tab_kind="found",
    )


def render_missing_tab_with_sources(
    assets_with_sources: Dict[str, List[Dict[str, str]]],
    asset_type: str,
    format_func,
    original_json: dict,
    asset_fields: Set[str],
    all_asset_fields: Optional[Set[str]] = None,
    search_key: str = "search_missing",
    show_transition_context: bool = False,
):
    _render_assets_with_sources_tab(
        assets_data=assets_with_sources,
        asset_type=asset_type,
        format_func=format_func,
        original_json=original_json,
        asset_fields=asset_fields,
        all_asset_fields=all_asset_fields,
        asset_paths=None,
        search_key=search_key,
        show_transition_context=show_transition_context,
        tab_kind="missing",
    )


def render_found_tools_tab(
    found_assets: Dict[str, Dict[str, Any]],
    search_key: str = "search_found_tools",
):

    st.subheader(f"Found Tools ({len(found_assets)})")

    if not found_assets:
        st.info("No tools from your JSON were found in the reference.")
        return

    search_term = st.text_input("Search found tools", key=search_key)
    filtered = {
        tool: info
        for tool, info in found_assets.items()
        if not search_term or search_term.lower() in tool.lower()
    }
    st.caption(f"Showing {len(filtered)} of {len(found_assets)} tools")

    for tool in sorted(filtered.keys()):
        info = filtered[tool]
        sources: List[Dict[str, str]] = info.get("sources", [])
        matched_variants: List[str] = info.get("matched_variants", [])

        with st.expander(f"✓ {tool} — {len(sources)} usage(s)", expanded=False):
            if matched_variants:
                st.markdown("**Matched reference variant(s):**")
                for v in matched_variants:
                    st.code(v, language="")

            _render_usages(sources, show_transition_context=True)

    st.download_button(
        label=" Download Found Tools (TXT)",
        data="\n".join(sorted(found_assets.keys())),
        file_name="found_tools.txt",
        mime="text/plain",
        key=f"{search_key}_dl",
    )


def render_transitions_tab(transitions: List[Dict[str, Any]]):
    st.subheader(f"Transitions ({len(transitions)})")

    if not transitions:
        st.info("No transitions found in the JSON.")
        return

    search_term = st.text_input("Search transitions", key="search_transitions")
    filtered = [
        t
        for t in transitions
        if not search_term
        or search_term.lower() in t.get("name", "").lower()
        or search_term.lower() in t.get("parent", "").lower()
        or search_term.lower() in t.get("child", "").lower()
    ]
    st.caption(f"Showing {len(filtered)} of {len(transitions)} transitions")

    for transition in filtered:
        with st.expander(f" {transition.get('name', 'unnamed')}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Parent**")
                st.code(transition.get("parent", "—"))
            with col2:
                st.markdown("**Child**")
                st.code(transition.get("child", "—"))
