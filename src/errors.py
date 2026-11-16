"""Application errors shared by adapters and delivery mechanisms."""


class DatabaseUnavailable(RuntimeError):
    """The database could not be reached or returned a retryable failure."""

    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


class Conflict(RuntimeError):
    """A persistence write broke a uniqueness constraint."""


class InvoiceAlreadyExists(Conflict):
    """The caller already has an invoice with this public number."""
