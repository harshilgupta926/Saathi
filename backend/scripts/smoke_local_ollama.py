#!/usr/bin/env python3
"""Opt-in acceptance probe for a real local Ollama model.

Run only after Ollama is reachable and the configured model has been pulled:
  OLLAMA_BASE_URL=http://127.0.0.1:11434 LLM_MODEL=qwen2.5:7b \
    python backend/scripts/smoke_local_ollama.py

This intentionally tests the live local service (not a mock) and fails if the
model does not select a declared weather tool. It never calls a hosted model.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.provider_adapters import OllamaToolRouter


async def main() -> int:
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model = os.getenv("LLM_MODEL", "qwen2.5:7b")
    timeout = min(60.0, max(1.0, float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "45"))))
    router = OllamaToolRouter(base_url=base_url, model=model, timeout_seconds=timeout)
    prompt = "The farmer asks: what is the weather forecast for tomorrow? Select the appropriate tool."
    started = perf_counter()
    try:
        selected = await router.choose(prompt)
    except Exception as exc:
        print(json.dumps({
            "status": "fail",
            "provider": "ollama-local",
            "model": model,
            "error_type": type(exc).__name__,
            "latency_ms": round((perf_counter() - started) * 1000, 1),
        }, ensure_ascii=False))
        return 1

    latency_ms = round((perf_counter() - started) * 1000, 1)
    report = {
        "status": "pass" if selected is not None and selected.name == "get_weather" else "fail",
        "provider": "ollama-local",
        "model": model,
        "prompt_case": "weather_tool_selection",
        "selected_tool": selected.name if selected else None,
        "arguments_keys": sorted(selected.arguments) if selected else [],
        "latency_ms": latency_ms,
        "timeout_seconds": timeout,
        "hosted_fallback": False,
    }
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
