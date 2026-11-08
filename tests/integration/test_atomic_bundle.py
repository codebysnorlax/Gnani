import pytest
from pathlib import Path

from consumerdost.agent.graph import get_compiled_graph, run_atomic_generation
from consumerdost.agent.state import ConsumerDostState


@pytest.mark.asyncio
async def test_full_flow_intake_to_atomic_generation():
    """Verify end-to-end LangGraph state machine from text/intake to atomic GENERATED state."""
    intake_graph = await get_compiled_graph()

    state: ConsumerDostState = {
        "telegram_user_id": "atomic_test_user",
        "chat_id": "atomic_chat_1",
        "thread_id": "thread_atomic_1",
        "preferred_language": "hi-IN",
        "raw_input_text": (
            "Maine Flipkart se 14999 ka phone 25 October ko mangaya tha. "
            "Order ID OD3091823901. Box khola toh screen tooti hui thi. "
            "Mera naam Rohan Sharma hai aur email rohan@example.com."
        ),
        "demo_type": "flipkart",
        "is_demo": True,
    }

    # 1. Run intake & dispute assessment
    intake_result = await intake_graph.ainvoke(state)
    assert intake_result["status"] == "AWAITING_CONFIRMATION"
    assert intake_result.get("total_claim_paise", 0) > 1499900
    assert intake_result.get("brand_resolved") is not None
    assert intake_result.get("case_reference_id") is not None

    state.update(intake_result)

    # 2. Run atomic generation pipeline (bundle -> tts)
    gen_result = await run_atomic_generation(state)
    state.update(gen_result)

    # 3. Verify atomic state completeness
    assert state.get("status") == "GENERATED"
    assert state.get("pdf_file_path") is not None
    assert Path(state["pdf_file_path"]).exists()
    assert state.get("nch_dossier_text") is not None
    assert "NCH 1915" in state["nch_dossier_text"]
    assert state.get("twitter_draft_text") is not None
    assert len(state["twitter_draft_text"]) <= 280
    assert state.get("tts_audio_path") is not None
    assert Path(state["tts_audio_path"]).exists()
