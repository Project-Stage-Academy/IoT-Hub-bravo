class BaseValidator:
    def __init__(self):
        self._errors: list[dict] = []

    @property
    def errors(self):
        return self._errors

    def is_valid(self) -> bool:
        self._validate()
        return not self._errors

    def _validate(self):
        raise NotImplementedError
