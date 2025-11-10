from contextvars import ContextVar

correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_cid() -> str | None:
    return correlation_id_var.get()


def set_cid(value: str | None) -> None:
    correlation_id_var.set(value)
