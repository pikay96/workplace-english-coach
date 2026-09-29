"""Only allowlisted numeric/identifier fields reach service logs."""

import json
import logging
import time
import traceback

ALLOWED = {
    "operation_id",
    "phase",
    "category",
    "duration_ms",
    "input_tokens",
    "output_tokens",
    "audio_seconds",
    "count",
    "model",
    "error_type",
    "location",
}


def configure_logs():
    # SDK diagnostics can include transcripts, prompts and exception response bodies.
    # Keep them off; the application emits redacted categories at service boundaries.
    logging.basicConfig(level=logging.CRITICAL, format="%(message)s", force=True)
    for name in ("livekit", "openai", "httpx", "httpcore", "aiohttp", "uvicorn.access"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    logger = logging.getLogger("workplace")
    logger.setLevel(logging.INFO)


def metric(category: str, **fields):
    fields["category"] = category
    fields = {key: value for key, value in fields.items() if key in ALLOWED}
    logging.getLogger("workplace").info(json.dumps({"time": round(time.time()), **fields}))


def failure(category: str, error: BaseException):
    frames = traceback.extract_tb(error.__traceback__)
    frame = frames[-1] if frames else None
    metric(
        category,
        error_type=type(error).__name__,
        location=f"{frame.name}:{frame.lineno}" if frame else "unknown",
    )
