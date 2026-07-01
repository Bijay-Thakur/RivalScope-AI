import json
import re


def extract_json_from_text(text: str) -> dict | list:
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    fence = re.search(r"```(?:json)?\s*\n?([\s\S]*?)\n?```", text)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except json.JSONDecodeError:
            pass

    match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    raise ValueError(
        f"No valid JSON found in text (first 120 chars): {text[:120]!r}"
    )


def safe_get_message_text(response) -> str:
    if hasattr(response, "content"):
        return response.content
    if isinstance(response, str):
        return response
    return str(response)
