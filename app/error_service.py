from fastapi import HTTPException


# =========================
# Base Application Errors
# =========================

class AppHTTPException(HTTPException):
    status_code = 500
    default_detail = "Internal server error"

    def __init__(self, detail=None):
        super().__init__(
            status_code=self.status_code,
            detail=detail or self.default_detail
        )


class BadRequestError(AppHTTPException):
    status_code = 400
    default_detail = "Bad request"


class NotFoundError(AppHTTPException):
    status_code = 404
    default_detail = "Resource not found"


class InternalServerError(AppHTTPException):
    status_code = 500
    default_detail = "Internal server error"


class BadGatewayError(AppHTTPException):
    status_code = 502
    default_detail = "External service request failed"


# =========================
# Tracker Errors
# =========================

class TrackerNotFoundError(NotFoundError):
    default_detail = "Tracker not found"


class InvalidUpdateFrequencyError(BadRequestError):
    default_detail = "Invalid update_frequency"


class UnsupportedSourceError(BadRequestError):
    default_detail = "Unsupported source"


# =========================
# Query JSON Errors
# =========================

class QueryJsonValidationError(BadRequestError):
    default_detail = "Invalid query_json format"


class RunQueryJsonFormatError(BadRequestError):
    default_detail = "Invalid query_json format"


# =========================
# Run Errors
# =========================

class RunExecutionError(InternalServerError):
    default_detail = "Run failed"


# =========================
# External Service Errors
# =========================

class ExternalServiceConfigurationError(InternalServerError):
    default_detail = "External service configuration error"


class ExternalServiceRequestError(BadGatewayError):
    default_detail = "External service request failed"


# =========================
# Common Raise Methods
# =========================

def raise_tracker_not_found():
    raise TrackerNotFoundError()


def raise_invalid_update_frequency(update_frequency: str):
    allowed = ["daily", "manual", "weekly"]
    raise InvalidUpdateFrequencyError(
        f"update_frequency must be one of {allowed}"
    )


def raise_unsupported_source(source: str):
    raise UnsupportedSourceError(
        f"Unsupported source: {source}"
    )


# =========================
# Query JSON Raise Methods
# =========================

def raise_query_json_error(detail: str):
    raise QueryJsonValidationError(detail)


def raise_unsupported_query_json_keys(unexpected_keys):
    raise QueryJsonValidationError(
        f"Unsupported query_json keys: {sorted(unexpected_keys)}"
    )


def raise_expected_object(field_name: str):
    raise QueryJsonValidationError(
        f"{field_name} must be an object"
    )


def raise_expected_list(field_name: str):
    raise QueryJsonValidationError(
        f"{field_name} must be a list"
    )


def raise_expected_boolean(field_name: str):
    raise QueryJsonValidationError(
        f"{field_name} must be a boolean"
    )


# =========================
# Run Raise Methods
# =========================

def raise_run_query_json_format_error():
    raise RunQueryJsonFormatError()


def raise_run_execution_error(error_message: str):
    raise RunExecutionError(
        f"Run failed: {error_message}"
    )


# =========================
# External Service Raise Methods
# =========================

def raise_external_service_config_error(config_name: str):
    raise ExternalServiceConfigurationError(
        f"{config_name} is not configured"
    )


def raise_external_service_request_error(service_name: str, error_message: str):
    raise ExternalServiceRequestError(
        f"{service_name} request failed: {error_message}"
    )