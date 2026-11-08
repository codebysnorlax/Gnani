import pytest
import inspect
import saarthi.agent.llm_router as router_mod
import saarthi.speech.gnani_stt as stt_mod
from tests.fixtures.synthetic_cases import SYNTHETIC_TEST_FIXTURES


def test_production_modules_do_not_contain_demo_fixtures():
    # Production LLM router must not define or import GOLDEN_FIXTURES
    assert not hasattr(router_mod, "GOLDEN_FIXTURES"), "GOLDEN_FIXTURES must not be present in llm_router"

    # Production STT must not define or import GOLDEN_DEMO_TRANSCRIPTS
    assert not hasattr(stt_mod, "GOLDEN_DEMO_TRANSCRIPTS"), "GOLDEN_DEMO_TRANSCRIPTS must not be present in gnani_stt"
    assert not hasattr(stt_mod, "GOLDEN_DEMO_TRANSCRIPT"), "GOLDEN_DEMO_TRANSCRIPT must not be present in gnani_stt"


def test_synthetic_test_fixtures_isolated_in_tests():
    assert len(SYNTHETIC_TEST_FIXTURES) == 3
    for fix in SYNTHETIC_TEST_FIXTURES:
        assert "keywords" in fix
        assert "draft" in fix
