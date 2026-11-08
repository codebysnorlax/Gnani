"""Pre-cache high-fidelity Timbre v3.0 audio assets for golden demo scenarios."""

import asyncio
import logging
from pathlib import Path

from consumerdost.config import settings
from consumerdost.speech.gnani_tts import tts_service
from consumerdost.agent.voice_prompts import VoicePromptComposer
from consumerdost.domain.calculator import calculate_claim

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def precache_demo_assets():
    """Synthesize or generate cached audio for golden scenarios."""
    demo_cache_dir = settings.data_dir / "cache" / "demo"
    demo_cache_dir.mkdir(parents=True, exist_ok=True)

    cache_dir = settings.data_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 1. Pre-cache Welcome Audios
    for lang in ["hi-IN", "en-IN", "kn-IN"]:
        welcome_path = cache_dir / f"welcome_{lang}.wav"
        if not welcome_path.exists():
            script = VoicePromptComposer.compose_welcome(lang)
            logger.info(f"Pre-caching welcome audio for {lang} -> {welcome_path}")
            await tts_service.synthesize_speech(
                text=script,
                output_path=welcome_path,
                language=lang,
                persona="empathetic",
                model="timbre-v3.0",
            )
        else:
            logger.info(f"Welcome audio for {lang} already cached: {welcome_path}")

    # 2. Golden Demo Scenarios Definitions
    scenarios = {
        "flipkart": {
            "lang": "hi-IN",
            "amount": 14999.0,
            "date": "2026-10-25",
            "issue_type": "ECOMMERCE_DEFECTIVE_PRODUCT",
        },
        "upi": {
            "lang": "hi-IN",
            "amount": 1200.0,
            "date": "2026-11-01",
            "issue_type": "BANKING_FAILED_UPI_REVERSAL",
        },
        "indigo": {
            "lang": "en-IN",
            "amount": 6500.0,
            "date": "2026-11-01",
            "issue_type": "AIRLINE_CANCELLATION_REFUND",
        },
    }

    for scenario_name, sc in scenarios.items():
        lang = sc["lang"]
        claim = calculate_claim(sc["amount"], sc["date"], issue_type=sc["issue_type"])
        total_inr = claim.total_demanded_paise / 100.0

        # Assessment Walkthrough
        assessment_script = VoicePromptComposer.compose_assessment(total_inr, language=lang)
        assessment_path = demo_cache_dir / f"assessment_{scenario_name}.wav"
        logger.info(f"Pre-caching assessment audio for {scenario_name} -> {assessment_path}")
        await tts_service.synthesize_speech(
            text=assessment_script,
            output_path=assessment_path,
            language=lang,
            persona="empathetic",
            model="timbre-v3.0",
        )

        # Closing Action Summary
        closing_path = demo_cache_dir / f"closing_{scenario_name}.wav"
        logger.info(f"Pre-caching closing summary audio for {scenario_name} -> {closing_path}")
        await tts_service.synthesize_action_summary(
            output_path=closing_path,
            language=lang,
        )

    logger.info("All demo audio assets successfully pre-cached!")


if __name__ == "__main__":
    asyncio.run(precache_demo_assets())
