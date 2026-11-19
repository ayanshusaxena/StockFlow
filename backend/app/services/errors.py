class DomainError(Exception):
    status_code = 400
    code = "domain_error"

    def __init__(self, message: str, *, details: list[dict[str, object]] | None = None):
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"


class InsufficientStockError(ConflictError):
    code = "insufficient_stock"


class DatabaseOperationError(DomainError):
    status_code = 500
    code = "database_operation_failed"

    def __init__(self):
        super().__init__("The database operation could not be completed.")
