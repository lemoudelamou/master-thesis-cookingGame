from typing import Set, Dict, Any, List, Tuple, Optional, Union
from collections import defaultdict


def extract_keys_from_fields_with_sources(
    data: Any, field_names: List[str], extract_filename: bool = False
) -> Dict[str, List[Dict[str, str]]]:

    asset_sources = defaultdict(list)

    def process_item(item: Any, parent_name: str = ""):
        if isinstance(item, dict):
            item_name = item.get("name", parent_name or "unknown")

            for field in field_names:
                if field in item and item[field]:
                    original_value = item[field]
                    value = original_value

                    if extract_filename and isinstance(value, str) and "/" in value:
                        value = value.split("/")[-1]

                    if value:
                        asset_sources[value].append(
                            {
                                "field": field,
                                "json_key": item_name,
                                "original_value": original_value,
                                "parent": item.get("parent", ""),
                                "child": item.get("child", ""),
                            }
                        )

            for v in item.values():
                if isinstance(v, (dict, list)):
                    process_item(v, item_name)

        elif isinstance(item, list):
            for element in item:
                process_item(element, parent_name)

    process_item(data)
    return dict(asset_sources)


def extract_keys_from_fields(
    data: Any, field_names: List[str], extract_filename: bool = False
) -> Set[str]:
    sources = extract_keys_from_fields_with_sources(data, field_names, extract_filename)
    return set(sources.keys())


def extract_image_keys(data: Any, image_fields: List[str]) -> Set[str]:
    return extract_keys_from_fields(data, image_fields, extract_filename=True)


def extract_image_keys_with_sources(
    data: Any, image_fields: List[str]
) -> Dict[str, List[Dict[str, str]]]:
    return extract_keys_from_fields_with_sources(
        data, image_fields, extract_filename=True
    )


def extract_sound_keys(data: Any, sound_fields: List[str]) -> Set[str]:
    return extract_keys_from_fields(data, sound_fields, extract_filename=False)


def extract_sound_keys_with_sources(
    data: Any, sound_fields: List[str]
) -> Dict[str, List[Dict[str, str]]]:
    return extract_keys_from_fields_with_sources(
        data, sound_fields, extract_filename=False
    )


def extract_tool_keys(data: Any, tool_fields: List[str]) -> Set[str]:
    return extract_keys_from_fields(data, tool_fields, extract_filename=False)


def extract_tool_keys_with_sources(
    data: Any, tool_fields: List[str]
) -> Dict[str, List[Dict[str, str]]]:
    return extract_keys_from_fields_with_sources(
        data, tool_fields, extract_filename=False
    )


def extract_transitions(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    return data.get("transitions", [])


def filter_images_by_folder(
    images_dict: Dict[str, str], allowed_folders: Optional[List[str]] = None
) -> Set[str]:
    if not allowed_folders:
        return set(images_dict.keys())

    filtered_keys = set()

    for key, path in images_dict.items():
        if "/" in path:
            folder = path.split("/")[0]
            if folder in allowed_folders:
                filtered_keys.add(key)
        else:
            if "root" in allowed_folders or "" in allowed_folders:
                filtered_keys.add(key)

    return filtered_keys


def compare_assets(
    json_assets: Set[str],
    reference_assets: Union[Set[str], Dict[str, Union[str, List[str]]]],
    flexible_matching: bool = True,
) -> Dict[str, Dict[str, Set[str]]]:
    if isinstance(reference_assets, dict):
        reference_set = set(reference_assets.keys())
    else:
        reference_set = reference_assets

    results = {
        "found": {},
        "missing": set(),
    }

    ref_lower = {r.lower(): r for r in reference_set}

    base_map = defaultdict(set)
    for ref in reference_set:
        ref_l = ref.lower()
        base_map[ref_l].add(ref)

        if flexible_matching and "_" in ref_l:
            base_map[ref_l.rsplit("_", 1)[0]].add(ref)

    for asset in json_assets:
        asset_l = asset.lower()
        matches = set()

        if asset_l in ref_lower:
            matches.add(ref_lower[asset_l])

        if flexible_matching:
            if asset_l in base_map:
                matches.update(base_map[asset_l])

            if "_" in asset_l:
                base = asset_l.rsplit("_", 1)[0]
                matches.update(base_map.get(base, set()))

        if matches:
            results["found"][asset] = matches
        else:
            results["missing"].add(asset)

    return results


def compare_assets_with_sources(
    asset_sources: Dict[str, List[Dict[str, str]]], reference_assets: Set[str]
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, List[Dict[str, str]]]]:

    found = {}
    missing = {}

    ref_lower_map = defaultdict(list)
    for ref in reference_assets:
        ref_lower_map[ref.lower()].append(ref)

    reference_base_names = defaultdict(list)

    for asset in reference_assets:
        asset_lower = asset.lower()

        reference_base_names[asset_lower].append(asset)

        if "_" in asset_lower:
            parts = asset_lower.rsplit("_", 1)
            if len(parts) == 2 and parts[1].isdigit():
                base = parts[0]
                reference_base_names[base].append(asset)

        for suffix in ["_small", "_hover", "_cursor"]:
            if asset_lower.endswith(suffix):
                base = asset_lower[: -len(suffix)]
                reference_base_names[base].append(asset)
                break

    for asset, sources in asset_sources.items():
        asset_lower = asset.lower()
        matched_variants = []

        if asset_lower in ref_lower_map:
            matched_variants.extend(ref_lower_map[asset_lower])

        if "_" in asset_lower:
            parts = asset_lower.rsplit("_", 1)

            if len(parts) == 2 and parts[1].isdigit():
                base = parts[0]
                if base in ref_lower_map:
                    matched_variants.extend(ref_lower_map[base])
                if base in reference_base_names:
                    matched_variants.extend(reference_base_names[base])

            for suffix in ["_small", "_hover", "_cursor"]:
                if asset_lower.endswith(suffix):
                    base = asset_lower[: -len(suffix)]
                    if base in ref_lower_map:
                        matched_variants.extend(ref_lower_map[base])
                    if base in reference_base_names:
                        matched_variants.extend(reference_base_names[base])
                    break

        if asset_lower in reference_base_names:
            matched_variants.extend(reference_base_names[asset_lower])

        seen = set()
        unique_variants = []
        for variant in matched_variants:
            if variant not in seen:
                seen.add(variant)
                unique_variants.append(variant)

        if unique_variants:
            found[asset] = {"sources": sources, "matched_variants": unique_variants}
        else:
            missing[asset] = sources

    return found, missing


def get_available_folders(images_dict: Dict[str, str]) -> List[str]:
    folders = set()

    for path in images_dict.values():
        if "/" in path:
            folder = path.split("/")[0]
            folders.add(folder)

    return sorted(folders)


def group_by_folder(keys: Set[str], paths_dict: Dict[str, str]) -> Dict[str, List[str]]:

    grouped = defaultdict(list)

    for key in keys:
        if key in paths_dict:
            path = paths_dict[key]
            folder = path.split("/")[0] if "/" in path else "root"
            grouped[folder].append(key)

    return dict(grouped)


def format_as_python_dict(keys: Set[str], template: str = "Path/{}") -> str:

    lines = []
    for key in sorted(keys):
        path = template.format(key)
        lines.append(f'    "{key}": "{path}"')

    return ",\n".join(lines)


def format_as_python_set(keys: Set[str]) -> str:

    lines = [f'    "{key}"' for key in sorted(keys)]
    return ",\n".join(lines)


def count_items_with_fields(
    data: Dict[str, Any], array_key: str, field_names: List[str]
) -> int:

    items = data.get(array_key, [])
    return sum(1 for item in items if any(field in item for field in field_names))
