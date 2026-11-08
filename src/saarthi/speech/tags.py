"""Speech audio tag validator and sanitizer for Gnani Timbre v3.0.

Restricts tags strictly to the safe conversational allowlist (<pauses>, <slow>)
with a maximum 2-tag limit per response, no leading emotional tags,
and fallback text sanitization.
"""

from __future__ import annotations

import re
from typing import Sequence

# Validated, sparse conversational audio tags allowlist
ALLOWED_AUDIO_TAGS: frozenset[str] = frozenset({
    "<pauses>",
    "<slow>",
})

# Backward compatibility alias
SUPPORTED_AUDIO_TAGS: frozenset[str] = ALLOWED_AUDIO_TAGS

MAX_TAGS_PER_RESPONSE: int = 2

# Matches any bracketed tag <...>
TAG_REGEX = re.compile(r"<([^>]+)>")


def extract_tags(text: str) -> list[str]:
    """Extract all <tag> strings from the text in order."""
    if not text:
        return []
    return [f"<{match.group(1).strip().lower()}>" for match in TAG_REGEX.finditer(text)]


def is_valid_tag(tag: str) -> bool:
    """Check if tag is in the allowed conversational allowlist."""
    return tag.lower() in ALLOWED_AUDIO_TAGS


def validate_tags(text: str, max_tags: int = MAX_TAGS_PER_RESPONSE) -> tuple[bool, list[str]]:
    """Validate that all tags in text are in ALLOWED_AUDIO_TAGS and count <= max_tags.
    
    Returns (is_valid, list_of_violations).
    """
    found = extract_tags(text)
    violations = []
    
    # Check for unsupported tags
    for t in found:
        if t not in ALLOWED_AUDIO_TAGS:
            violations.append(f"unsupported:{t}")

    # Check for tag count cap
    if len(found) > max_tags:
        violations.append(f"tag_count_exceeded:{len(found)}>{max_tags}")

    # Check for leading audio tag
    trimmed = text.strip()
    if trimmed.startswith("<") and any(trimmed.startswith(t) for t in found):
        violations.append("leading_tag_prohibited")

    return len(violations) == 0, violations


def sanitize_tags_for_tts(text: str, max_tags: int = MAX_TAGS_PER_RESPONSE) -> str:
    """Normalize allowed tags to lower case, strip unsupported tags, strip leading tags,
    and enforce maximum tag limit per response.
    """
    if not text:
        return ""

    # 1. Strip any leading audio tag at start of text
    cleaned = re.sub(r"^\s*<[^>]+>\s*", "", text)

    tag_count = 0

    def replace_tag(match: re.Match) -> str:
        nonlocal tag_count
        tag_content = match.group(1).strip().lower()
        full_tag = f"<{tag_content}>"
        if full_tag in ALLOWED_AUDIO_TAGS and tag_count < max_tags:
            tag_count += 1
            return full_tag
        return ""  # strip unsupported or excess tags

    sanitized = TAG_REGEX.sub(replace_tag, cleaned)
    # Collapse multiple spaces while keeping tag spacing clean
    return re.sub(r" +", " ", sanitized).strip()


def strip_audio_tags(text: str) -> str:
    """Strip all audio tags from text for clean visual/text-only display or TTS fallback.
    
    Collapses excess spaces and trims edges.
    """
    if not text:
        return ""
    stripped = TAG_REGEX.sub("", text)
    cleaned = re.sub(r"\s+", " ", stripped).strip()
    return cleaned
