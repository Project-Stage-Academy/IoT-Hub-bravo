from typing import Any, Iterable, Mapping


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
