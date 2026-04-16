class AppException(Exception):
    def __init__(self, message, status_code=400, error_type="AppException", details=None):
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type
        self.details = details

    def to_dict(self):
        return {
            "type": self.error_type,
            "details": self.details
        }

class ErrorService:
    @staticmethod
    def bad_request(message="Bad request", error_type="BadRequest", details=None):
        return AppException(message=message, status_code=400, error_type=error_type, details=details)

    @staticmethod
    def unauthorized(message="You are unauthorized from accessing this resource", error_type="Unauthorized", details=None):
        return AppException(message=message, status_code=401, error_type=error_type, details=details)
    
    @staticmethod
    def forbidden(message="You are forbidden from accessing this resource", error_type="Forbidden", details=None):
        return AppException(message=message, status_code=403, error_type=error_type, details=details)
    
    @staticmethod
    def not_found(message="Resource not found", error_type="NotFound", details=None):
        return AppException(message=message, status_code=404, error_type=error_type, details=details)
    
    @staticmethod
    def conflict(message="Resource conflict", error_type="Conflict", details=None):
        return AppException(message=message, status_code=409, error_type=error_type, details=details)
    @staticmethod
    def unprocessable_entity(message="Unprocessable entity", error_type="UnprocessableEntity", details=None):
        return AppException(message=message, status_code=422, error_type=error_type, details=details)
    
    @staticmethod
    def too_many_requests(message="Too many requests", error_type="TooManyRequests", details=None):
        return AppException(message=message, status_code=429, error_type=error_type, details=details)
    
    @staticmethod
    def service_unavailable(message="Service unavailable", error_type="ServiceUnavailable", details=None):
        return AppException(message=message, status_code=503, error_type=error_type, details=details)
    
    @staticmethod
    def internal_server_error(message="Internal server error", error_type="InternalServerError", details=None):
        return AppException(message=message, status_code=500, error_type=error_type, details=details)
    
    @staticmethod
    def invalid_api_key(message="Invalid API key", error_type="APIKeyInvalid", details=None):
        return AppException(message=message, status_code=401, error_type=error_type, details=details)
    
    @staticmethod
    def custom_http_error(status_code, message, error_type="AppException", details=None):
        return AppException(message=message, status_code=status_code, error_type=error_type, details=details)