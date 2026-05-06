from typing import Any, Dict, List, Optional, Set
import streamlit as st


def render_statistics_row(stats: List[Dict[str, Any]]):
    cols = st.columns(len(stats))
    for col, stat in zip(cols, stats):
        with col:
            st.metric(
                stat["label"],
                stat["value"],
                delta=stat.get("delta"),
                delta_color=stat.get("delta_color", "normal"),
            )


def render_progress_section(title: str, progress: float, description: str):
    st.subheader(title)
    st.progress(progress)
    st.write(description)


def render_info_box(title: str):
    st.info(f"{title}\n")


def render_asset_grid(
    assets: Set[str],
    asset_type: str = "item",
    columns: int = 3,
    show_success: bool = True,
    extra_info: Optional[Dict[str, str]] = None,
):

    cols = st.columns(columns)
    for idx, asset in enumerate(sorted(assets)):
        with cols[idx % columns]:
            if show_success:
                st.success(f"✓ {asset}")
            else:
                st.error(f"✗ {asset}")
            if extra_info and asset in extra_info:
                st.caption(extra_info[asset])


def render_grouped_assets(
    grouped: Dict[str, List[str]],
    show_success: bool = True,
    extra_info: Optional[Dict[str, str]] = None,
):
    for group_name in sorted(grouped.keys()):
        assets_in_group = grouped[group_name]
        with st.expander(f" {group_name} ({len(assets_in_group)} files)"):
            cols = st.columns(2)
            for idx, asset in enumerate(sorted(assets_in_group)):
                with cols[idx % 2]:
                    if show_success:
                        st.success(f"✓ {asset}")
                    else:
                        st.error(f"✗ {asset}")
                    if extra_info and asset in extra_info:
                        st.caption(extra_info[asset])


def render_search_filter(assets: Set[str], key: str, label: str = "Search") -> Set[str]:
    search_term = st.text_input(label, key=key)
    if search_term:
        filtered = {asset for asset in assets if search_term.lower() in asset.lower()}
        st.write(f"Showing {len(filtered)} of {len(assets)} items")
        return filtered
    st.write(f"Showing {len(assets)} items")
    return assets


def render_download_buttons(downloads: List[Dict[str, str]], columns: int = 2):
    cols = st.columns(columns)
    for idx, download in enumerate(downloads):
        with cols[idx % columns]:
            st.download_button(
                label=download["label"],
                data=download["data"],
                file_name=download["filename"],
                mime=download.get("mime", "text/plain"),
            )
