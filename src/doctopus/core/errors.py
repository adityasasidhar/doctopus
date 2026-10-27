class DoctopusError(Exception):
    """Base class; carries a stable `code` for API/MCP error payloads."""
    code = "doctopus_error"


class BackendUnavailable(DoctopusError):
    code = "backend_unavailable"


class UnsupportedFormat(DoctopusError):
    code = "unsupported_format"


class ExtractionFailed(DoctopusError):
    code = "extraction_failed"


class InputRejected(DoctopusError):
    code = "input_rejected"
