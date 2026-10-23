"""Request outcome-blind covariate-priority weights from the DeepSeek API."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = (
    ROOT
    / "docs"
    / "llm_matching"
    / "weight extraction protocol"
    / "llm_prompt_covariate_weights.md"
)
OUTPUT_ROOT = ROOT / "results" / "matching results" / "deepseek_api"
API_URL = "https://api.deepseek.com/chat/completions"
EXPECTED_KEYS = {
    "MAGER",
    "MRACEHISP",
    "MEDUC",
    "CIG0_R",
    "PRIORLIVE",
    "PRIORDEAD",
    "BMI_R",
    "RF_PDIAB",
    "RF_PHYPE",
    "SEX",
}


def read_standalone_prompt(path: Path) -> str:
    """Return only the delimited prompt body, excluding its documentation wrapper."""
    text = path.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^---\s*\n(.*?)\n---\s*$", text)
    if not match:
        raise ValueError(f"Could not find prompt delimiters in {path}")
    prompt = match.group(1).strip()
    if not prompt or "pilot" in prompt.lower() or "reference-error" in prompt.lower():
        raise ValueError("Prompt is empty or contains a prohibited evaluation-results term")
    return prompt


def validate_weights(content: str) -> dict[str, int]:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Assistant response is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict) or set(parsed) != EXPECTED_KEYS:
        raise ValueError("Response must be an object with exactly the ten prespecified keys")
    if any(type(value) is not int or not 0 <= value <= 10 for value in parsed.values()):
        raise ValueError("Every score must be an integer from 0 through 10")
    if not any(parsed.values()):
        raise ValueError("At least one score must be positive")
    return parsed


def request_completion(api_key: str, prompt: str, model: str, timeout: int) -> dict[str, Any]:
    request_body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "thinking": {"type": "disabled"},
        "temperature": 0,
        "max_tokens": 512,
        "stream": False,
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DeepSeek API returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach DeepSeek API: {exc.reason}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default=os.environ.get("DEEPSEEK_MODEL", "deepseek-flash"),
        help="DeepSeek model name (default: DEEPSEEK_MODEL or deepseek-flash)",
    )
    parser.add_argument("--timeout", type=int, default=120, help="API timeout in seconds")
    args = parser.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print(
            "DEEPSEEK_API_KEY is not set. Set it in this terminal session, then rerun.",
            file=sys.stderr,
        )
        return 2
    if args.timeout <= 0:
        parser.error("--timeout must be a positive number")

    try:
        prompt = read_standalone_prompt(PROMPT_PATH)
        response = request_completion(api_key, prompt, args.model, args.timeout)
    except (OSError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    timestamp = datetime.now(timezone.utc)
    run_dir = OUTPUT_ROOT / timestamp.strftime("%Y%m%dT%H%M%SZ")
    if run_dir.exists():
        print(f"Output directory already exists; refusing to overwrite: {run_dir}", file=sys.stderr)
        return 1
    run_dir.mkdir(parents=True)

    (run_dir / "api_response.json").write_text(
        json.dumps(response, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    choices = response.get("choices") or []
    if not choices or not isinstance(choices[0].get("message", {}).get("content"), str):
        print(f"Saved API response, but it did not contain assistant text: {run_dir}", file=sys.stderr)
        return 1

    content = choices[0]["message"]["content"]
    (run_dir / "raw_model_output.txt").write_text(content + "\n", encoding="utf-8")
    try:
        weights = validate_weights(content)
    except ValueError as exc:
        print(f"Saved raw response, but weight validation failed: {exc}\n{run_dir}", file=sys.stderr)
        return 1

    (run_dir / "weights.json").write_text(
        json.dumps(weights, indent=2) + "\n", encoding="utf-8"
    )
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    (run_dir / "record.md").write_text(
        "# DeepSeek API weight elicitation record\n\n"
        f"- Requested at (UTC): {timestamp.isoformat()}\n"
        f"- Provider: DeepSeek API\n"
        f"- Requested model: `{args.model}`\n"
        f"- Returned model: `{response.get('model', 'not reported')}`\n"
        f"- API response ID: `{response.get('id', 'not reported')}`\n"
        f"- API endpoint: `{API_URL}`\n"
        "- Thinking mode: disabled\n"
        "- Temperature: 0\n"
        "- Maximum output tokens: 512\n"
        "- Response format: JSON object\n"
        f"- Prompt SHA-256: `{prompt_hash}`\n"
        f"- Finish reason: `{choices[0].get('finish_reason', 'not reported')}`\n"
        f"- Token usage: `{json.dumps(response.get('usage', 'not reported'))}`\n"
        "- Validation: passed; exactly ten required integer scores from 0 to 10.\n"
        "- Retries or manual edits: none; this script sends one request and does not edit scores.\n\n"
        "## Exact prompt sent\n\n"
        f"```text\n{prompt}\n```\n\n"
        "## Validated weights\n\n"
        f"```json\n{json.dumps(weights, indent=2)}\n```\n",
        encoding="utf-8",
    )
    print(f"Validated DeepSeek weights and saved run record to: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
