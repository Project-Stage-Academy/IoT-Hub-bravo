from common.checker.idempotency_store import IdempotencyStore


class DuplicateChecker:
    def __init__(self, store: IdempotencyStore):
        self._store = store

    def process(self, key: str, message: str) -> str:
        """
        Process a message with a given key.

        If the key already exists in the store, it's considered a duplicate.
        Otherwise, the key is saved atomically and the message is considered new.
        """
        if not self._store.save_if_not_exists(key):
            return "duplicate"

        return "ok"
