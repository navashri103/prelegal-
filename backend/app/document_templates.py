import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
TEMPLATES_DIR = DATA_DIR / "templates"
MANIFEST_PATH = TEMPLATES_DIR / "index.json"


class TemplateNotFoundError(RuntimeError):
    pass


@lru_cache
def load_manifest() -> list[dict]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["templates"]


@lru_cache
def load_template(template_id: str) -> dict:
    entry = next((e for e in load_manifest() if e["id"] == template_id), None)
    if entry is None:
        raise TemplateNotFoundError(f"Unknown document type: {template_id!r}")
    return json.loads((TEMPLATES_DIR / entry["file"]).read_text(encoding="utf-8"))


def empty_fields(template_id: str) -> dict[str, None]:
    return {field["key"]: None for field in load_template(template_id)["fields"]}
