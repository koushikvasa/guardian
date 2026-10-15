"""Arize tracing. One trace per case; each step is a span.

Arize AX (cloud) when ARIZE_SPACE_ID + ARIZE_API_KEY are set; otherwise self-hosted Phoenix when
PHOENIX_COLLECTOR_ENDPOINT is set. With neither, span() is a no-op so nothing else changes.
"""
import contextlib
import contextvars
import time

from . import bus, config

_tracer = None
current_case: contextvars.ContextVar[str | None] = contextvars.ContextVar("guardian_case", default=None)


def set_case(case_id: str | None):
    """Spans opened inside this task (and threads it spawns) are tagged with the case."""
    current_case.set(case_id)


def init():
    global _tracer
    if config.live(config.ARIZE_SPACE_ID, config.ARIZE_API_KEY):
        try:
            from arize.otel import register

            provider = register(  # default gRPC transport; the HTTP exporter path is broken in arize-otel 0.14 + otel 1.45
                space_id=config.ARIZE_SPACE_ID,
                api_key=config.ARIZE_API_KEY,
                project_name=config.ARIZE_PROJECT,
                auto_instrument=True,  # picks up boto3/bedrock if openinference-instrumentation-bedrock is installed
                verbose=False,
            )
            _tracer = provider.get_tracer("guardian")
            print("[tracing] Arize AX project", config.ARIZE_PROJECT)
        except Exception as e:
            print("[tracing] Arize AX unavailable:", e)
        return
    if not config.live(config.PHOENIX_COLLECTOR_ENDPOINT):
        return
    try:
        from phoenix.otel import register

        provider = register(
            project_name=config.PHOENIX_PROJECT,
            endpoint=config.PHOENIX_COLLECTOR_ENDPOINT.rstrip("/") + "/v1/traces",
            auto_instrument=True,
        )
        _tracer = provider.get_tracer("guardian")
        print("[tracing] Phoenix on", config.PHOENIX_COLLECTOR_ENDPOINT)
    except Exception as e:
        print("[tracing] Phoenix unavailable:", e)


def flush():
    """Force-export pending spans (call before a short-lived script exits)."""
    try:
        from opentelemetry import trace

        p = trace.get_tracer_provider()
        if hasattr(p, "force_flush"):
            p.force_flush(timeout_millis=10000)
    except Exception:
        pass


class _Span:
    def __init__(self, real=None):
        self.real = real
        self.attrs: dict = {}

    @property
    def trace_id(self) -> str | None:
        try:
            return format(self.real.get_span_context().trace_id, "032x") if self.real is not None else None
        except Exception:
            return None

    def set(self, key: str, value):
        self.attrs[key] = value
        if self.real is not None:
            if not isinstance(value, (str, int, float, bool)):
                value = str(value)
            self.real.set_attribute(key, value)


def _emit(name: str, s: "_Span", t0: float, attrs: dict):
    case_id = str(attrs.get("case") or current_case.get() or "") or None
    if name == "case" and not case_id:
        return
    public = {k: (v if isinstance(v, (int, float, bool)) else str(v)[:160]) for k, v in s.attrs.items() if k not in ("case", "signals", "data", "url")}
    bus.emit("span", case_id, name=name, t0=round(t0, 3), dur=round(time.time() - t0, 3), attrs=public)


@contextlib.contextmanager
def span(name: str, **attrs):
    t0 = time.time()
    if _tracer is None:
        s = _Span()
        for k, v in attrs.items():
            s.set(k, v)
        try:
            yield s
        finally:
            _emit(name, s, t0, attrs)
        return
    with _tracer.start_as_current_span(name) as real:
        s = _Span(real)
        for k, v in attrs.items():
            s.set(k, v)
        try:
            yield s
        finally:
            _emit(name, s, t0, attrs)
