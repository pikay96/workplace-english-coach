"""No credentials, services or model calls are needed to export HTTP contracts."""

import json
from pathlib import Path

from app.api.main import app

Path(__file__).with_name("openapi.json").write_text(
    json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8"
)
