class BaseValidator:
    def __init__(self):
        self._errors: list[dict] = []

    @property
    def errors(self):
        return self._errors

    def validate(self) -> None:
        self._validate_payload()
        return not self._errors

    def _validate_payload(self):
        raise NotImplementedError
