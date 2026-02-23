from typing import Any

def validate_field(
    data: dict[str, Any],
    field: str,
    expected_type: type,
    required: bool = True
) -> tuple[Any, dict[str, Any]]:
    """
    Validate a single field
    Returns: (value, errors_dict)
    """
    errors = {}

    if required and field not in data:
        errors[field] = "This field is required."
        return None, errors

    if field in data:
        value = data[field]

        if expected_type is bool:
            if type(value) is not bool:
                errors[field] = "Must be of type boolean"
                return None, errors
        elif expected_type is int:
            if type(value) is not int:
                errors[field] = "Must be of type integer"
                return None, errors
        elif not isinstance(value, expected_type):
            errors[field] = f"Must be of type {expected_type.__name__}"
            return None, errors

        return value, {}

    return None, {}