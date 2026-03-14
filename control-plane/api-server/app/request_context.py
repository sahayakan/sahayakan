"""Request context using contextvars for request-scoped state (e.g., X-Request-ID)."""

import contextvars

_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


def get_request_id() -> str:
    return _request_id_var.get()


def set_request_id(request_id: str) -> contextvars.Token:
    return _request_id_var.set(request_id)
