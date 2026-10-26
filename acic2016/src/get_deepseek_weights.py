"""Elicit ACIC 2016 field weights from DeepSeek and save a complete run record."""

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
PROMPT_PATH = ROOT / "docs" / "llm_matching" / "weight_prompt.md"
OUTPUT_ROOT = ROOT / "results" / "llm_weights" / "deepseek_api"
API_URL = "https://api.deepseek.com/chat/completions"
EXPECTED_KEYS = {f"x_{i}" for i in range(1, 59)}


def read_prompt(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^---\s*\n(.*?)\n---\s*$", text)
    if not match:
        raise ValueError(f"Could not find standalone prompt delimiters in {path}")
    prompt = match.group(1).strip()
    if not prompt:
        raise ValueError("Standalone prompt is empty")
    return prompt


def validate_weights(content: str) -> dict[str, int]:
    parsed = json.loads(content)
    if not isinstance(parsed, dict) or set(parsed) != EXPECTED_KEYS:
        raise ValueError("Response must contain exactly the keys x_1 through x_58")
    if any(type(value) is not int or not 0 <= value <= 10 for value in parsed.values()):
        raise ValueError("Every score must be an integer from 0 through 10")
    if not any(parsed.values()):
        raise ValueError("At least one score must be positive")
    return parsed


def request_completion(api_key: str, prompt: str, model: str, timeout: int) -> dict[str, Any]:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "thinking": {"type": "disabled"},
        "temperature": 0,
        "max_tokens": 2048,
        "stream": False,
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(body).encode("utf-8"),
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
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("DEEPSEEK_API_KEY is not set in this PowerShell session.", file=sys.stderr)
        return 2
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    run_time = datetime.now(timezone.utc)
    run_id = run_time.strftime("%Y%m%dT%H%M%SZ")
    run_dir = OUTPUT_ROOT / run_id
    if run_dir.exists():
        raise FileExistsError(f"Refusing to overwrite existing run: {run_dir}")

    prompt = read_prompt(PROMPT_PATH)
    response = request_completion(api_key, prompt, args.model, args.timeout)
    choices = response.get("choices") or []
    if not choices:
        raise ValueError("API response contains no choices")
    message = choices[0].get("message") or {}
    raw_text = message.get("content")
    if not isinstance(raw_text, str):
        raise ValueError("API response has no text content")

    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    (run_dir / "raw_response.json").write_text(
        json.dumps(response, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (run_dir / "raw_model_text.txt").write_text(raw_text + "\n", encoding="utf-8")

    try:
        weights = validate_weights(raw_text)
    except (json.JSONDecodeError, ValueError) as exc:
        record = {
            "status": "validation_failed",
            "timestamp_utc": run_time.isoformat(),
            "provider": "DeepSeek",
            "requested_model": args.model,
            "returned_model": response.get("model"),
            "prompt_path": str(PROMPT_PATH),
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "temperature": 0,
            "thinking": "disabled",
            "max_tokens": 2048,
            "error": str(exc),
        }
        (run_dir / "record.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"Response failed validation; raw output saved to: {run_dir}", file=sys.stderr)
        return 1

    (run_dir / "weights.json").write_text(
        json.dumps(weights, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    record = {
        "status": "success",
        "timestamp_utc": run_time.isoformat(),
        "provider": "DeepSeek",
        "requested_model": args.model,
        "returned_model": response.get("model"),
        "prompt_path": str(PROMPT_PATH),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "temperature": 0,
        "thinking": "disabled",
        "max_tokens": 2048,
        "stream": False,
        "response_format": "json_object",
        "usage": response.get("usage"),
    }
    (run_dir / "record.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Validated weights and elicitation record saved to: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
