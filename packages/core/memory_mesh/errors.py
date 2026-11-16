class MeshError(Exception):
    status = 400
    code = "bad_request"

    def __init__(self, message: str, **detail):
        super().__init__(message)
        self.message, self.detail = message, detail


class NotFound(MeshError):
    status, code = 404, "not_found"


class Forbidden(MeshError):
    status, code = 403, "forbidden"


class Unauthorized(MeshError):
    status, code = 401, "unauthorized"


class Unavailable(MeshError):
    """Feature requires a capability that is not configured (e.g. an LLM key)."""
    status, code = 503, "capability_unavailable"
