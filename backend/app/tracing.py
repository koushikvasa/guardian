"""Arize Phoenix tracing. One trace per case; each step is a span.

If Phoenix isn't configured, span() is a no-op so nothing else changes.
"""
import contextlib

from . import config

_tracer = None


def init():
    global _tracer
    if not config.live(config.PHOENIX_COLLECTOR_ENDPOINT):
        return
    try:
        from phoenix.otel import register

        provider = register(
            project_name=config.PHOENIX_PROJECT,
            endpoint=config.PHOENIX_COLLECTOR_ENDPOINT.rstrip("/") + "/v1/traces",
            auto_instrument=True,  # picks up boto3/bedrock if openinference-instrumentation-bedrock is installed
        )
        _tracer = provider.get_tracer("guardian")
        print("[tracing] Phoenix on", config.PHOENIX_COLLECTOR_ENDPOINT)
    except Exception as e:
        print("[tracing] Phoenix unavailable:", e)


class _Span:
    def __init__(self, real=None):
        self.real = real
        self.attrs: dict = {}

    def set(self, key: str, value):
        self.attrs[key] = value
        if self.real is not None:
            if not isinstance(value, (str, int, float, bool)):
                value = str(value)
            self.real.set_attribute(key, value)


@contextlib.contextmanager
def span(name: str, **attrs):
    if _tracer is None:
        s = _Span()
        for k, v in attrs.items():
            s.set(k, v)
        yield s
        return
    with _tracer.start_as_current_span(name) as real:
        s = _Span(real)
        for k, v in attrs.items():
            s.set(k, v)
        yield s
