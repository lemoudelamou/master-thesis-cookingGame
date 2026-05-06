import streamlit as st
import json
from typing import Dict, Any

from assets_checker.library.png_files_dict import png_files
from assets_checker.library.sounds_dict import sound_names
from assets_checker.library.tool_names import tools as tool_names

from config.config import APP_CONFIG, IMAGE_FIELDS, SOUND_FIELDS, TOOL_FIELDS
from structure_checker.validator import render_validator_page
from assets_checker.utils import (
    extract_image_keys_with_sources,
    extract_sound_keys_with_sources,
    extract_tool_keys_with_sources,
    compare_assets_with_sources,
    format_as_python_dict,
    format_as_python_set,
    count_items_with_fields,
    filter_images_by_folder,
    get_available_folders,
)
from assets_checker.checker import (
    render_statistics_row,
    render_progress_section,
    render_info_box,
    render_found_tab,
    render_found_tools_tab,
    render_found_tab_with_sources,
    render_missing_tab_with_sources,
)

from structure_generator.generator import render_recipe_converter_page
from structure_comparator.evaluator import render_evaluator_page


def render_found_tab_with_variants(
    found_assets_with_info: Dict[str, Dict[str, Any]],
    asset_type: str,
    asset_paths: Dict[str, str] = None,
    search_key: str = "search",
):
    """
    Render the found assets tab showing ALL matched variants with their paths.
    Used for images and sounds. For tools, use render_found_tools_tab instead.
    """
    if not found_assets_with_info:
        st.info(f"No {asset_type} found in JSON file.")
        return

    st.success(f"Found **{len(found_assets_with_info)}** {asset_type}")

    search = st.text_input(
        f"🔍 Search {asset_type}", key=search_key, placeholder="Type to filter..."
    )

    if search:
        filtered = {
            k: v
            for k, v in found_assets_with_info.items()
            if search.lower() in k.lower()
        }
    else:
        filtered = found_assets_with_info

    st.write(f"Showing {len(filtered)} of {len(found_assets_with_info)} {asset_type}")

    for asset_key in sorted(filtered.keys()):
        info = filtered[asset_key]
        sources = info["sources"]
        matched_variants = info["matched_variants"]

        with st.expander(f"**{asset_key}** → {len(matched_variants)} variant(s) found"):
            st.markdown("**Matched Variants:**")
            for variant in matched_variants:
                if asset_paths and variant in asset_paths:
                    st.code(f"{variant} → {asset_paths[variant]}", language="")
                else:
                    st.code(variant, language="")
            st.divider()
            st.markdown("**Used in JSON:**")
            for source in sources:
                st.caption(f"• Field: `{source['field']}` in `{source['json_key']}`")
                if source["original_value"] != asset_key:
                    st.caption(f"  Original value: `{source['original_value']}`")


def render_overall_summary(
    json_images, present_images, json_sounds, present_sounds, json_tools, present_tools
):
    st.header("Overall Summary")
    col1, col2 = st.columns(2)
    with col1:
        stats = [
            {"label": " Images in JSON", "value": len(json_images)},
            {
                "label": " Images Found",
                "value": len(present_images),
                "delta": (
                    f"{len(present_images)/len(json_images)*100:.1f}%"
                    if json_images
                    else "0%"
                ),
            },
        ]
        render_statistics_row(stats)
    with col2:
        stats = [
            {"label": " Sounds in JSON", "value": len(json_sounds)},
            {
                "label": "Sounds Found",
                "value": len(present_sounds),
                "delta": (
                    f"{len(present_sounds)/len(json_sounds)*100:.1f}%"
                    if json_sounds
                    else "0%"
                ),
            },
        ]
        render_statistics_row(stats)

    stats = [
        {"label": " Tools in JSON", "value": len(json_tools)},
        {
            "label": " Tools Found",
            "value": len(present_tools),
            "delta": (
                f"{len(present_tools)/len(json_tools)*100:.1f}%" if json_tools else "0%"
            ),
        },
    ]
    render_statistics_row(stats)


def render_image_summary(json_data, json_images, present_images):
    progress = len(present_images) / len(json_images) if json_images else 0
    render_progress_section(
        "Image Statistics",
        progress,
        f"**{progress*100:.2f}%** of images in your JSON are found in the library",
    )
    render_info_box(
        " **Analyzed Fields**: openIcon, cursorBitmap, additiveOpenIcon, activeIcon"
    )
    num_tasks = len(json_data.get("tasks", []))
    num_transitions = len(json_data.get("transitions", []))
    render_statistics_row(
        [
            {"label": "Tasks Found", "value": num_tasks},
            {"label": "Transitions Found", "value": num_transitions},
        ]
    )


def render_sound_summary(json_data, json_sounds, present_sounds):
    progress = len(present_sounds) / len(json_sounds) if json_sounds else 0
    render_progress_section(
        "Sound Statistics",
        progress,
        f"**{progress*100:.2f}%** of sounds in your JSON are found in the library",
    )
    render_info_box(" **Analyzed Fields**: sound, activeSound, doneSound, openSound")
    render_statistics_row(
        [
            {
                "label": "Tasks with Sounds",
                "value": count_items_with_fields(json_data, "tasks", SOUND_FIELDS),
            },
            {
                "label": "Transitions with Sounds",
                "value": count_items_with_fields(
                    json_data, "transitions", SOUND_FIELDS
                ),
            },
        ]
    )


def render_tool_summary(json_data, json_tools, present_tools):
    progress = len(present_tools) / len(json_tools) if json_tools else 0
    render_progress_section(
        "Tool Statistics",
        progress,
        f"**{progress*100:.2f}%** of tools in your JSON are found in the library. ",
    )
    render_info_box(
        " **Analyzed Fields**: tool",
    )
    render_statistics_row(
        [
            {
                "label": "Tasks with Tools",
                "value": count_items_with_fields(json_data, "tasks", TOOL_FIELDS),
            },
            {
                "label": "Transitions with Tools",
                "value": count_items_with_fields(json_data, "transitions", TOOL_FIELDS),
            },
        ]
    )


def process_json_file(json_data: Dict[str, Any]):
    available_folders = get_available_folders(png_files)

    with st.expander("Filter Images by Folder (Optional)", expanded=False):
        st.write(
            "Select specific folders to check, or leave all unchecked to check everything."
        )
        cols = st.columns(4)
        selected_folders = []
        for idx, folder in enumerate(sorted(available_folders)):
            with cols[idx % 4]:
                count = sum(
                    1 for k, path in png_files.items() if path.startswith(f"{folder}/")
                )
                if st.checkbox(f"{folder} ({count})", key=f"folder_{folder}"):
                    selected_folders.append(folder)
        if selected_folders:
            st.success(f"Checking {len(selected_folders)} selected folder(s)")
        else:
            st.info(
                f"No folders selected - checking all {len(available_folders)} folders"
            )

    st.divider()

    reference_images = (
        filter_images_by_folder(png_files, selected_folders)
        if selected_folders
        else set(png_files.keys())
    )
    reference_sounds = sound_names
    reference_tools = set(tool_names)

    image_sources = extract_image_keys_with_sources(json_data, IMAGE_FIELDS)
    sound_sources = extract_sound_keys_with_sources(json_data, SOUND_FIELDS)
    tool_sources = extract_tool_keys_with_sources(json_data, TOOL_FIELDS)

    json_images = set(image_sources.keys())
    json_sounds = set(sound_sources.keys())
    json_tools = set(tool_sources.keys())

    found_images, missing_images_with_sources = compare_assets_with_sources(
        image_sources, reference_images
    )
    found_sounds, missing_sounds_with_sources = compare_assets_with_sources(
        sound_sources, reference_sounds
    )
    found_tools, missing_tools_with_sources = compare_assets_with_sources(
        tool_sources, reference_tools
    )

    present_images = set(found_images.keys())
    missing_images = set(missing_images_with_sources.keys())
    present_sounds = set(found_sounds.keys())
    missing_sounds = set(missing_sounds_with_sources.keys())
    present_tools = set(found_tools.keys())
    missing_tools = set(missing_tools_with_sources.keys())

    render_overall_summary(
        json_images,
        present_images,
        json_sounds,
        present_sounds,
        json_tools,
        present_tools,
    )

    if missing_images or missing_sounds or missing_tools:
        st.error(
            f"""
         **Missing Assets Found!**
        - {len(missing_images)} images missing 
        - {len(missing_sounds)} sounds missing 
        - {len(missing_tools)} tools missing 
        """
        )
    else:
        st.success("All assets found in dictionaries!")

    st.divider()

    tab1, tab2, tab3 = st.tabs([" Images", " Sounds", " Tools"])

    with tab1:
        img_tab1, img_tab2, img_tab3 = st.tabs([" Summary", " Found", " Missing"])
        with img_tab1:
            render_image_summary(json_data, json_images, present_images)
        with img_tab2:
            render_found_tab_with_sources(
                found_images,
                "images",
                format_func=format_as_python_dict,
                original_json=json_data,
                asset_fields=set(IMAGE_FIELDS),
                all_asset_fields=set(IMAGE_FIELDS)
                | set(SOUND_FIELDS)
                | set(TOOL_FIELDS),
                asset_paths=png_files,
                search_key="search_present_img",
            )
        with img_tab3:
            render_missing_tab_with_sources(
                missing_images_with_sources,
                "images",
                format_func=format_as_python_dict,
                original_json=json_data,
                asset_fields=set(IMAGE_FIELDS) | set(SOUND_FIELDS) | set(TOOL_FIELDS),
                search_key="search_missing_img",
            )

    with tab2:
        snd_tab1, snd_tab2, snd_tab3 = st.tabs([" Summary", " Found", " Missing"])
        with snd_tab1:
            render_sound_summary(json_data, json_sounds, present_sounds)
        with snd_tab2:
            render_found_tab_with_sources(
                found_sounds,
                "sounds",
                format_func=format_as_python_set,
                original_json=json_data,
                asset_fields=set(SOUND_FIELDS),
                all_asset_fields=set(IMAGE_FIELDS)
                | set(SOUND_FIELDS)
                | set(TOOL_FIELDS),
                search_key="search_present_snd",
            )
        with snd_tab3:
            render_missing_tab_with_sources(
                missing_sounds_with_sources,
                "sounds",
                format_func=format_as_python_set,
                original_json=json_data,
                asset_fields=set(IMAGE_FIELDS) | set(SOUND_FIELDS) | set(TOOL_FIELDS),
                search_key="search_missing_snd",
            )

    with tab3:
        tool_tab1, tool_tab2, tool_tab3 = st.tabs([" Summary", " Found", " Missing"])
        with tool_tab1:
            render_tool_summary(json_data, json_tools, present_tools)
        with tool_tab2:
            render_found_tab_with_sources(
                found_tools,
                "tools",
                format_func=format_as_python_set,
                original_json=json_data,
                asset_fields=set(TOOL_FIELDS),
                all_asset_fields=set(IMAGE_FIELDS)
                | set(SOUND_FIELDS)
                | set(TOOL_FIELDS),
                search_key="search_present_tool",
                show_transition_context=True,
            )
        with tool_tab3:
            # show_transition_context=True renders parent → child per usage line
            render_missing_tab_with_sources(
                missing_tools_with_sources,
                "tools",
                format_func=format_as_python_set,
                original_json=json_data,
                asset_fields=set(IMAGE_FIELDS) | set(SOUND_FIELDS) | set(TOOL_FIELDS),
                search_key="search_missing_tool",
                show_transition_context=True,
            )

    with st.expander("View Full JSON Structure"):
        st.json(json_data)


def render_welcome_screen():
    st.info("Please upload a JSON file to begin checking.")
    available_folders = get_available_folders(png_files)
    st.subheader("Available Image Folders")
    st.write(f"Found **{len(available_folders)}** folders in image assets library:")
    cols = st.columns(5)
    for idx, folder in enumerate(sorted(available_folders)):
        with cols[idx % 5]:
            count = sum(
                1 for path in png_files.values() if path.startswith(f"{folder}/")
            )
            st.metric(folder, f"{count} imgs")
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        with st.expander("Reference Stats"):
            st.metric("Total Images", len(png_files))
            st.metric("Total Sounds", len(sound_names))
            st.metric("Total Tools", len(tool_names))
            st.metric("Image Folders", len(available_folders))
    with col2:
        with st.expander("Sample Assets"):
            st.write("**Sample images:**")
            for key in list(png_files.keys())[:5]:
                st.code(f"{key}: {png_files[key]}")
            st.write("**Sample sounds:**")
            for sound in sorted(list(sound_names))[:5]:
                st.code(sound)


def render_asset_checker_page():
    st.title("Asset Checker")
    st.markdown(
        "Upload a JSON file to check which **images**, **sounds**, and **tools** are missing."
    )
    uploaded_file = st.file_uploader(
        "Choose a JSON file", type=["json"], key="asset_checker_upload"
    )
    if uploaded_file is not None:
        try:
            json_data = json.load(uploaded_file)
            process_json_file(json_data)
        except json.JSONDecodeError as e:
            st.error(f"Error parsing JSON file: {e}")
        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.exception(e)
    else:
        render_welcome_screen()


def render_statistics_page():
    render_validator_page()


def render_navigation_sidebar():
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] {
                min-width: 200px !important;
                max-width: 300px !important;
            }
            [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
                padding: 1rem 0.75rem;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.title("Cooking Game")
        st.markdown("---")
        st.subheader("Navigation")

        if "current_page" not in st.session_state:
            st.session_state.current_page = "JSON Conversion"

        pages = [
            "JSON Conversion",
            "Schema Validator",
            "Asset Checker",
            "Structure Comparison",
        ]
        for page in pages:
            btn_type = (
                "primary" if st.session_state.current_page == page else "secondary"
            )
            if st.button(page, use_container_width=True, type=btn_type):
                st.session_state.current_page = page
                st.rerun()

    return st.session_state.current_page


def main():
    st.set_page_config(**APP_CONFIG)
    selected_page = render_navigation_sidebar()
    if selected_page == "JSON Conversion":
        render_recipe_converter_page()
    elif selected_page == "Asset Checker":
        render_asset_checker_page()
    elif selected_page == "Schema Validator":
        render_statistics_page()
    elif selected_page == "Structure Comparison":
        render_evaluator_page()


if __name__ == "__main__":
    main()
