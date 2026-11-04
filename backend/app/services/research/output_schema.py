"""The JSON Schema sent to the model for Structured Outputs.

It is generated from the SAME GuideContent model we store, then adjusted
for OpenAI's strict mode:
- the SDK's `to_strict_json_schema` marks every field required and sets
  additionalProperties: false (strict-mode requirements);
- string length keywords are removed, because the official docs we checked
  do not list minLength/maxLength as supported in strict mode.

Removing them is safe: the model's answer is validated against the FULL
GuideContent model (lengths, cross-references, everything) before saving.
"""

from functools import lru_cache
from typing import Any

from openai.lib._pydantic import to_strict_json_schema

from app.schemas.guide import GuideContent

SCHEMA_NAME = "oauth_setup_guide"
_UNSUPPORTED_KEYWORDS = ("minLength", "maxLength")


def _strip_keywords(node: Any) -> Any:
    if isinstance(node, dict):
        return {key: _strip_keywords(value) for key, value in node.items() if key not in _UNSUPPORTED_KEYWORDS}
    if isinstance(node, list):
        return [_strip_keywords(item) for item in node]
    return node


@lru_cache
def guide_json_schema() -> dict[str, Any]:
    return _strip_keywords(to_strict_json_schema(GuideContent))


def text_format_config() -> dict[str, Any]:
    """The `text` parameter for client.responses.stream(...)."""
    return {"format": {"type": "json_schema", "name": SCHEMA_NAME, "schema": guide_json_schema(), "strict": True}}
