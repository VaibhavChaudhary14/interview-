from fastapi import HTTPException


class AppException(HTTPException):
    def __init__(self, status_code: int, error_code: str, message: str, details: dict | None = None):
        super().__init__(status_code=status_code, detail={
            "error_code": error_code,
            "message": message,
            "details": details or {},
        })


class NotFoundException(AppException):
    def __init__(self, entity: str, entity_id: str):
        super().__init__(404, f"{entity.upper()}_NOT_FOUND", f"No {entity} found with the given id.")


class InvalidStateTransition(AppException):
    def __init__(self, message: str):
        super().__init__(409, "INVALID_STATE_TRANSITION", message)


class ValidationError(AppException):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(400, "VALIDATION_ERROR", message, details)


class UpstreamFailure(AppException):
    def __init__(self, service: str, message: str = ""):
        super().__init__(502, f"{service.upper()}_FAILURE", f"Upstream {service} failed after retries." + (f" {message}" if message else ""))
