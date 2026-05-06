import streamlit as st


def search_sections(section, gt_section, gen_section, search_term):
    if not search_term:
        return True

    search_term = search_term.lower()

    if search_term in section.lower():
        return True

    if search_in_content(gt_section, search_term):
        return True

    if search_in_content(gen_section, search_term):
        return True

    return False


def search_in_content(content, search_term):
    """Search within section content"""
    search_term = search_term.lower()

    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict):
                for key, value in item.items():
                    if search_term in str(key).lower():
                        return True

                    if search_term in str(value).lower():
                        return True

            elif search_term in str(item).lower():
                return True

    elif isinstance(content, dict):
        for key, value in content.items():
            if search_term in str(key).lower():
                return True

            if search_term in str(value).lower():
                return True

    else:
        if search_term in str(content).lower():
            return True

    return False


def render_section_content(gt_section, gen_section, search_term):
    if isinstance(gt_section, list) or isinstance(gen_section, list):
        render_list_comparison(gt_section, gen_section)

    elif isinstance(gt_section, dict) or isinstance(gen_section, dict):
        render_dict_comparison(gt_section, gen_section, search_term)

    else:
        render_simple_comparison(gt_section, gen_section)


def render_list_comparison(gt_list, gen_list):
    gt_list = gt_list if isinstance(gt_list, list) else []
    gen_list = gen_list if isinstance(gen_list, list) else []

    max_items = max(len(gt_list), len(gen_list))

    for idx in range(max_items):
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Ground Truth**")
            render_list_item(gt_list, idx)

        with col2:
            st.write("**Generated**")
            render_list_item(gen_list, idx)

        st.divider()


def render_list_item(item_list, idx):
    if idx < len(item_list):
        item = item_list[idx]

        if isinstance(item, dict):
            for key, value in item.items():
                st.write(f"- **{key}:** {value}")
        else:
            st.write(item)

    else:
        st.write("_No item_")


def render_dict_comparison(gt_dict, gen_dict, search_term):
    all_keys = set()

    if isinstance(gt_dict, dict):
        all_keys.update(gt_dict.keys())

    if isinstance(gen_dict, dict):
        all_keys.update(gen_dict.keys())

    for key in sorted(all_keys):
        if search_term and search_term.lower() not in key.lower():
            continue

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Ground Truth**")

            if isinstance(gt_dict, dict) and key in gt_dict:
                st.write(f"**{key}:** {gt_dict[key]}")
            else:
                st.write(f"_{key}: Missing_")

        with col2:
            st.write("**Generated**")

            if isinstance(gen_dict, dict) and key in gen_dict:
                st.write(f"**{key}:** {gen_dict[key]}")
            else:
                st.write(f"_{key}: Missing_")

        st.divider()


def render_simple_comparison(gt_content, gen_content):
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Ground Truth**")
        st.write(gt_content)

    with col2:
        st.write("**Generated**")
        st.write(gen_content)

    st.divider()
