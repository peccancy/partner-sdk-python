class PartnerApiError(Exception):
    """Raised when the API responds with a non-2xx status (or the request fails)."""

    def __init__(self, message: str, status_code: int, body: str):
        super().__init__(message)
        self.status_code = status_code
        self.body = body
