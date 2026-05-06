import streamlit as st


def render_page_title(title, description):
    st.markdown(
        f"""
    <div style="text-align: center; padding: 30px 0;">
        <h1 style="color: #667eea; font-size: 3em; margin-bottom: 10px;">{title}</h1>
        <p style="color: #666; font-size: 1.2em;">{description}</p>
    </div>
    """,
        unsafe_allow_html=True,
    )


def render_file_uploaders():
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Upload process.json")
        process_file = st.file_uploader(
            "Choose process.json",
            type=["json"],
            key="process_upload",
            label_visibility="collapsed",
        )
        if process_file:
            st.success(f"Loaded: {process_file.name}")

    with col2:
        st.markdown("###  Upload tasksText.json")
        taskstext_file = st.file_uploader(
            "Choose tasksText.json",
            type=["json"],
            key="taskstext_upload",
            label_visibility="collapsed",
        )
        if taskstext_file:
            st.success(f"Loaded: {taskstext_file.name}")

    return process_file, taskstext_file
