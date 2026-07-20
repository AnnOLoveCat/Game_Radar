import unittest

from app.error_service import (
    AppHTTPException,
    BadGatewayError,
    BadRequestError,
    ExternalServiceConfigurationError,
    ExternalServiceRequestError,
    InternalServerError,
    InvalidUpdateFrequencyError,
    NotFoundError,
    QueryJsonValidationError,
    RunExecutionError,
    TrackerNotFoundError,
    UnsupportedSourceError,
)


class TestErrorService(unittest.TestCase):
    def test_error_class_status_codes_and_inheritance(self):
        test_cases = [
            {
                "name": "Tracker not found",
                "error": TrackerNotFoundError(),
                "parent_class": NotFoundError,
                "expected_status_code": 404,
                "expected_detail": "Tracker not found",
            },
            {
                "name": "Query JSON validation",
                "error": QueryJsonValidationError("regions must be a list"),
                "parent_class": BadRequestError,
                "expected_status_code": 400,
                "expected_detail": "regions must be a list",
            },
            {
                "name": "Invalid update frequency",
                "error": InvalidUpdateFrequencyError(
                    "update_frequency must be one of ['daily', 'manual', 'weekly']"
                ),
                "parent_class": BadRequestError,
                "expected_status_code": 400,
                "expected_detail": "update_frequency must be one of ['daily', 'manual', 'weekly']",
            },
            {
                "name": "Unsupported source",
                "error": UnsupportedSourceError("Unsupported source: steam"),
                "parent_class": BadRequestError,
                "expected_status_code": 400,
                "expected_detail": "Unsupported source: steam",
            },
            {
                "name": "External service configuration",
                "error": ExternalServiceConfigurationError("RAWG_API_KEY is not configured"),
                "parent_class": InternalServerError,
                "expected_status_code": 500,
                "expected_detail": "RAWG_API_KEY is not configured",
            },
            {
                "name": "External service request",
                "error": ExternalServiceRequestError("RAWG request failed: timeout"),
                "parent_class": BadGatewayError,
                "expected_status_code": 502,
                "expected_detail": "RAWG request failed: timeout",
            },
            {
                "name": "Run execution",
                "error": RunExecutionError("Run failed: database error"),
                "parent_class": InternalServerError,
                "expected_status_code": 500,
                "expected_detail": "Run failed: database error",
            },
        ]

        for case in test_cases:
            with self.subTest(case=case["name"]):
                error = case["error"]

                assert isinstance(error, AppHTTPException)
                assert isinstance(error, case["parent_class"])
                assert error.status_code == case["expected_status_code"]
                assert error.detail == case["expected_detail"]


if __name__ == "__main__":
    unittest.main()