"""Privacy-aware central Loguru diagnostic logging for SAARTHI.

Routes diagnostic records into:
  - logs/ai-err.log (LLM, STT, TTS errors)
  - logs/system-err.log (database, Telegram, network, and system exceptions)
  - logs/app.log and logs/other.log (operational and general records)

Strictly redacts credentials, API keys, tokens, payment cards, Aadhaar,
phone numbers, and email addresses prior to persistent disk writing.
Interception of Python's standard-library `logging` is handled centrally.
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Any

from loguru import logger

# Regex patterns for credential and PII redaction
TOKEN_PATTERNS = [
    # Telegram Bot Token: e.g. 1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
    (re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,45}\b"), "[REDACTED_TELEGRAM_TOKEN]"),
    # Google AI / Gemini API keys: AIza...
    (re.compile(r"\bAIza[0-9A-Za-z-_]{30,45}\b"), "[REDACTED_GEMINI_KEY]"),
    # Groq / OpenRouter tokens
    (re.compile(r"\bgsk_[A-Za-z0-9]{20,}\b"), "[REDACTED_GROQ_KEY]"),
    (re.compile(r"\bBearer\s+[A-Za-z0-9_\-\.]{20,}\b", re.IGNORECASE), "Bearer [REDACTED_TOKEN]"),
    # Payment cards (13-19 digits with spaces/dashes)
    (re.compile(r"\b\d{4}[ -]\d{4}[ -]\d{4}[ -]\d{4}\b"), "[REDACTED_CARD]"),
    (re.compile(r"\b\d{15,16}\b"), "[REDACTED_CARD]"),
    # 12-digit Indian Aadhaar numbers
    (re.compile(r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b"), "[REDACTED_AADHAAR]"),
    # Email addresses
    (re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"), "[REDACTED_EMAIL]"),
    # Indian 10-digit mobile phone numbers
    (re.compile(r"(?:\+91[\-\s]?)?[6-9]\d{9}\b"), "[REDACTED_PHONE]"),
    # Generic parameter keys
    (re.compile(r"(?i)(api[_-]?key|token|secret)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{8,}['\"]?"), r"\1=[REDACTED]"),
]


def redact_sensitive_text(text: str) -> str:
    """Scrub tokens, keys, card numbers, and PII from log message text."""
    if not text or not isinstance(text, str):
        return text
    redacted = text
    for pattern, replacement in TOKEN_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def redaction_filter(record: dict[str, Any]) -> bool:
    """Loguru patch filter that redacts message content and extra metadata."""
    try:
        record["message"] = redact_sensitive_text(record["message"])
        if "extra" in record and isinstance(record["extra"], dict):
            for k, v in record["extra"].items():
                if isinstance(v, str):
                    record["extra"][k] = redact_sensitive_text(v)
    except Exception:
        pass
    return True


class InterceptHandler(logging.Handler):
    """Intercept standard library logging records and route through Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).bind(
            logger_name=record.name
        ).log(level, record.getMessage())


def is_ai_error(record: dict[str, Any]) -> bool:
    """Classify if log record corresponds to an AI (LLM, STT, TTS) error."""
    if record["level"].no < logger.level("ERROR").no:
        return False
    extra = record.get("extra") or {}
    name = extra.get("logger_name") or record.get("name") or ""
    category = extra.get("category", "")
    if category == "ai":
        return True
    ai_modules = ("saarthi.speech", "saarthi.agent", "google.genai", "groq", "httpx")
    return any(name.startswith(mod) for mod in ai_modules)


def is_system_error(record: dict[str, Any]) -> bool:
    """Classify if log record corresponds to a system/database/telegram error."""
    if record["level"].no < logger.level("ERROR").no:
        return False
    return not is_ai_error(record)


def configure_logging(logs_dir: Path | str | None = None) -> None:
    """Configure centralized Loguru sinks, standard logging interception, and rotation."""
    if logs_dir is None:
        logs_dir = Path("logs")
    else:
        logs_dir = Path(logs_dir)

    logs_dir.mkdir(parents=True, exist_ok=True)

    # Reset loguru sinks to prevent duplicate output
    logger.remove()

    log_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{extra[logger_name]} | {message}"
    )

    # 1. Console Sink (stdout) with redaction
    logger.add(
        sys.stdout,
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        filter=redaction_filter,
        backtrace=True,
        diagnose=False,
    )

    # 2. AI Error Sink (logs/ai-err.log)
    ai_err_path = logs_dir / "ai-err.log"
    logger.add(
        str(ai_err_path),
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
        filter=lambda rec: is_ai_error(rec) and redaction_filter(rec),
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        backtrace=True,
        diagnose=False,
        encoding="utf-8",
    )

    # 3. System Error Sink (logs/system-err.log)
    sys_err_path = logs_dir / "system-err.log"
    logger.add(
        str(sys_err_path),
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
        filter=lambda rec: is_system_error(rec) and redaction_filter(rec),
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        backtrace=True,
        diagnose=False,
        encoding="utf-8",
    )

    # 4. General App Sink (logs/app.log and logs/other.log)
    app_log_path = logs_dir / "app.log"
    logger.add(
        str(app_log_path),
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
        filter=redaction_filter,
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        backtrace=True,
        diagnose=False,
        encoding="utf-8",
    )

    other_log_path = logs_dir / "other.log"
    logger.add(
        str(other_log_path),
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
        filter=redaction_filter,
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        backtrace=True,
        diagnose=False,
        encoding="utf-8",
    )

    # 5. Intercept standard-library logging
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)
    for name in ("aiogram", "uvicorn", "sqlalchemy", "httpx", "saarthi", "consumerdost"):
        log = logging.getLogger(name)
        log.handlers = [InterceptHandler()]
        log.propagate = False
