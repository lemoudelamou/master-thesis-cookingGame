import streamlit as st

from structure_comparator.text_search import search_sections


def render_text_comparison():
    """Render text comparison tab with collapsible sections in columns"""
    st.header("Text Files Comparison")
    st.divider()

    gt_text = st.session_state.gt_text_data
    gen_text = st.session_state.gen_text_data

    all_sections = get_all_sections(gt_text, gen_text)

    if not all_sections:
        st.info("No text sections to display")
        return

    section_search = st.text_input(
        "Search sections or keys",
        placeholder="e.g., titles, descriptions, info_knoblauch",
    )

    control_col1, control_col2, control_col3, control_col4 = st.columns([1, 1, 1, 1])

    with control_col1:
        if st.button("Expand All GT", key="expand_all_gt_sections_btn"):
            for section in all_sections:
                st.session_state[get_section_toggle_key("gt", section)] = True

    with control_col2:
        if st.button("Collapse All GT", key="collapse_all_gt_sections_btn"):
            for section in all_sections:
                st.session_state[get_section_toggle_key("gt", section)] = False

    with control_col3:
        if st.button("Expand All Gen", key="expand_all_gen_sections_btn"):
            for section in all_sections:
                st.session_state[get_section_toggle_key("gen", section)] = True

    with control_col4:
        if st.button("Collapse All Gen", key="collapse_all_gen_sections_btn"):
            for section in all_sections:
                st.session_state[get_section_toggle_key("gen", section)] = False

    st.divider()

    visible_sections = []

    for section in all_sections:
        gt_section = gt_text.get(section, {})
        gen_section = gen_text.get(section, {})

        if search_sections(section, gt_section, gen_section, section_search):
            visible_sections.append(section)

    if not visible_sections:
        st.info("No sections match your search")
        return

    gt_col, gen_col = st.columns(2)

    with gt_col:
        st.markdown("#### Ground Truth Sections")

        for section in visible_sections:
            gt_section = gt_text.get(section, {})
            gt_count = get_section_count(gt_section)

            display_name = section.replace("_", " ").title()
            toggle_key = get_section_toggle_key("gt", section)

            if toggle_key not in st.session_state:
                st.session_state[toggle_key] = False

            is_expanded = st.toggle(
                f"**{display_name} ({gt_count})**",
                key=toggle_key,
            )

            if is_expanded:
                render_section_box(gt_section, bg_color="#F1F8E9")

            st.markdown("")

    with gen_col:
        st.markdown("#### Generated Sections")

        for section in visible_sections:
            gen_section = gen_text.get(section, {})
            gen_count = get_section_count(gen_section)

            display_name = section.replace("_", " ").title()
            toggle_key = get_section_toggle_key("gen", section)

            if toggle_key not in st.session_state:
                st.session_state[toggle_key] = False

            is_expanded = st.toggle(
                f"**{display_name} ({gen_count})**",
                key=toggle_key,
            )

            if is_expanded:
                render_section_box(gen_section, bg_color="#FFF3E0")

            st.markdown("")


def get_section_toggle_key(prefix, section):
    safe_section = str(section).replace(" ", "_").replace("/", "_")
    return f"{prefix}_section_toggle_{safe_section}"


def render_section_box(section_data, bg_color):
    st.markdown(
        f"<div style='background-color: {bg_color}; padding: 8px; border-radius: 4px;'>",
        unsafe_allow_html=True,
    )

    if isinstance(section_data, list):
        for idx, item in enumerate(section_data):
            if idx > 0:
                st.markdown("---")

            if isinstance(item, dict):
                for key, value in item.items():
                    st.markdown(
                        f"<small>**{key}:** {value}</small>",
                        unsafe_allow_html=True,
                    )
            else:
                st.write(item)

    elif isinstance(section_data, dict):
        items = list(section_data.items())

        for idx, (key, value) in enumerate(items):
            if idx > 0:
                st.markdown("---")

            st.markdown(
                f"<small>**{key}:** {value}</small>",
                unsafe_allow_html=True,
            )

    else:
        st.write(section_data)

    st.markdown("</div>", unsafe_allow_html=True)


def get_all_sections(gt_text, gen_text):
    """Get all unique sections from both texts"""
    all_sections = set()

    if isinstance(gt_text, dict):
        all_sections.update(gt_text.keys())

    if isinstance(gen_text, dict):
        all_sections.update(gen_text.keys())

    return sorted(list(all_sections))


def get_section_count(section):
    """Get the count of items in a section"""
    if isinstance(section, list):
        return len(section)

    if isinstance(section, dict):
        return len(section)

    return 0
