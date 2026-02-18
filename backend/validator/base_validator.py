class BaseValidator:
    def __init__(self):
        self._errors: dict[str, str] = {}

    @property
    def errors(self):
        return self._errors

    def add_error(self, field: str, message: str):
        self._errors[field] = message

    def is_valid(self) -> bool:
        self._validate()
        return not self._errors

    def _validate(self):
        raise NotImplementedError
