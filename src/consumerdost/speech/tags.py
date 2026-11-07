import re
from typing import Sequence

SUPPORTED_AUDIO_TAGS: frozenset[str] = frozenset({
    "<coughs>",
    "<excited>",
    "<exhales>",
    "<giggle>",
    "<laugh>",
    "<pauses>",
    "<shouting>",
    "<sigh>",
    "<slow>",
    "<sniffles>",
    "<whispers>",
    "<yawns>",
    "<clears throat>",
})

# Matches any bracketed tag <...>
TAG_REGEX = re.compile(r"<([^>]+)>")


def extract_tags(text: str) -> list[str]:
    """Extract all <tag> strings from the text in order."""
    if not text:
        return []
    return [f"<{match.group(1).strip()}>" for match in TAG_REGEX.finditer(text)]


def is_valid_tag(tag: str) -> bool:
    """Check if tag is one of the 13 supported lower-case Timbre v3.0 tags."""
    return tag.lower() in SUPPORTED_AUDIO_TAGS


def validate_tags(text: str) -> tuple[bool, list[str]]:
    """Validate all tags in text.
    
    Returns (is_valid, list_of_invalid_tags).
    """
    found = extract_tags(text)
    invalid = [t for t in found if t.lower() not in SUPPORTED_AUDIO_TAGS]
    return len(invalid) == 0, invalid


def sanitize_tags_for_tts(text: str) -> str:
    """Normalize supported tags to lower case and remove unsupported tags.
    
    Timbre v3.0 tags must be exact lower-case match.
    Unknown tags are stripped silently.
    """
    if not text:
        return ""

    def replace_tag(match: re.Match) -> str:
        tag_content = match.group(1).strip().lower()
        full_tag = f"<{tag_content}>"
        if full_tag in SUPPORTED_AUDIO_TAGS:
            return full_tag
        return ""  # strip unsupported tag

    cleaned = TAG_REGEX.sub(replace_tag, text)
    # Collapse multiple spaces while keeping tag spacing clean
    return re.sub(r" +", " ", cleaned).strip()


def strip_audio_tags(text: str) -> str:
    """Strip all audio tags from text for clean visual/text-only display.
    
    Collapses excess spaces and trims edges.
    """
    if not text:
        return ""
    stripped = TAG_REGEX.sub("", text)
    cleaned = re.sub(r"\s+", " ", stripped).strip()
    return cleaned
