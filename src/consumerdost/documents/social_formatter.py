import urllib.parse
from consumerdost.domain.calculator import format_inr


WATCHDOG_HANDLES = "@jagograhakjago @DoCA_GoI"


def format_twitter_escalation(
    brand_handle: str | None,
    order_id: str,
    amount_inr: float,
    issue_snippet: str,
) -> dict[str, str]:
    """Generate public social escalation draft under 280 chars and tweet intent URL."""
    brand_tag = brand_handle if brand_handle else "Support"
    amt_str = format_inr(amount_inr)

    # Core message structure
    # E.g.: "Hey @FlipkartSupport, Order OD3091823901 for ₹14,999.00 has broken item; return denied. Seeking statutory refund under CPA 2019. CC: @jagograhakjago @DoCA_GoI"
    base = f"Hey {brand_tag}, Order {order_id} ({amt_str}): {issue_snippet}. Resolution denied. Demanding statutory refund under CPA 2019. CC: {WATCHDOG_HANDLES}"

    # If exceeding 280 chars, trim snippet
    if len(base) > 280:
        allowed_snippet_len = len(issue_snippet) - (len(base) - 276)
        if allowed_snippet_len > 10:
            trimmed_snippet = issue_snippet[:allowed_snippet_len] + "..."
            base = f"Hey {brand_tag}, Order {order_id} ({amt_str}): {trimmed_snippet}. Resolution denied. Demanding statutory refund under CPA 2019. CC: {WATCHDOG_HANDLES}"
        else:
            base = f"Hey {brand_tag}, Order {order_id} ({amt_str}): Resolution denied under CPA 2019. CC: {WATCHDOG_HANDLES}"

    intent_url = f"https://twitter.com/intent/tweet?text={urllib.parse.quote(base)}"

    return {
        "tweet_text": base,
        "intent_url": intent_url,
    }
