from typing import Any, Iterable, Mapping

from utils.json import json_equal


def normalize_schema(
    data_raw: Mapping[str, Any],
    *,
    required: Iterable[str],
    optional: Iterable[str] = (),
    strip_strings: bool = True,
    drop_optional_none: bool = True,
    drop_optional_blank_strings: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Normalize input dict to a known schema.

    - Copies required/optional keys into normalized
    - Adds errors for missing required keys
    - Optionally strips string values
    - Optionally drops optional fields with None / blank strings

    Returns:
        (normalized, errors)
    """
    normalized: dict[str, Any] = {}
    errors: dict[str, Any] = {}

    for field in required:
        if field not in data_raw:
            errors[field] = f'{field} is required.'
            continue

        value = data_raw[field]
        if strip_strings and isinstance(value, str):
            value = value.strip()
        normalized[field] = value

    for field in optional:
        if field not in data_raw:
            continue

        value = data_raw[field]
        if strip_strings and isinstance(value, str):
            value = value.strip()

        if drop_optional_none and value is None:
            continue

        if drop_optional_blank_strings and isinstance(value, str) and value == '':
            continue

        normalized[field] = value

    return normalized, errors


def diff_dicts(
    old: dict[str, Any],
    new: dict[str, Any],
) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    """
    Compute a shallow diff between two dictionaries that share the same schema.

    Returns:
        changed: list of top-level keys whose values differ.
        before: dict of {key: old_value} for changed keys.
        after:  dict of {key: new_value} for changed keys.

    Typical usage:
        old_snapshot = {...}
        new_snapshot = {...}
        changed, before, after = diff_dicts(old_snapshot, new_snapshot)
    """
    changed: list[str] = []
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}

    for key in old.keys():
        old_value = old[key]
        new_value = new[key]

        if isinstance(old_value, (dict, list)) or isinstance(new_value, (dict, list)):
            equal = json_equal(old_value, new_value)
        else:
            equal = old_value == new_value

        if not equal:
            changed.append(key)
            before[key] = old_value
            after[key] = new_value

    return changed, before, after
