import pytest
from consumerdost.database.engine import AsyncSessionLocal, init_db
from consumerdost.database.repository import DisputeRepository


@pytest.mark.asyncio
async def test_repository_user_and_case_lifecycle():
    await init_db()
    async with AsyncSessionLocal() as session:
        repo = DisputeRepository(session)

        # 1. Create User
        user = await repo.get_or_create_user("test_user_999", "chat_999", "en-IN")
        assert user.telegram_user_id == "test_user_999"

        # 2. Update Profile
        updated = await repo.update_user_profile(
            "test_user_999",
            legal_full_name="Vikram Seth",
            contact_detail="vikram@example.com",
        )
        assert updated.legal_full_name == "Vikram Seth"

        # 3. Create Case
        case = await repo.create_dispute_case(
            telegram_user_id="test_user_999",
            complainant_name="Vikram Seth",
            complainant_contact="vikram@example.com",
            brand_name="Flipkart",
            brand_corporate_name="Flipkart Internet Private Limited",
            registered_address="Embassy Tech Village",
            nodal_email="grievance@flipkart.com",
            order_id="OD9988776655",
            incident_date="2026-10-25",
            category="E_COMMERCE",
            issue_type="ECOMMERCE_DEFECTIVE_GOODS",
            principal_paise=1499900,
            interest_paise=3329,
            statutory_penalty_paise=0,
            damages_demanded_paise=500000,
            total_demanded_paise=2003229,
            narrative_facts_en="Defective item delivered.",
            legal_clauses=["Section 2(10)", "Section 2(47)"],
        )
        assert case.id.startswith("CD-")
        assert case.order_id == "OD9988776655"

        # 4. Add Artifact
        art = await repo.add_artifact(
            dispute_case_id=case.id,
            artifact_type="LEGAL_NOTICE_PDF",
            file_path="/tmp/notice.pdf",
        )
        assert art.dispute_case_id == case.id

        # 5. List Cases
        cases = await repo.get_user_cases("test_user_999")
        assert len(cases) >= 1

        # 6. Delete User Data (/privacy test)
        deleted_count = await repo.delete_user_data("test_user_999")
        assert deleted_count >= 1

        # Verify cases gone
        cases_after = await repo.get_user_cases("test_user_999")
        assert len(cases_after) == 0


@pytest.mark.asyncio
async def test_repository_session_persistence():
    await init_db()
    async with AsyncSessionLocal() as session:
        repo = DisputeRepository(session)
        user_id = "test_user_session_123"

        # 1. Initially no session
        initial = await repo.load_session_state(user_id)
        assert initial is None

        # 2. Save session
        test_state = {
            "telegram_user_id": user_id,
            "status": "AWAITING_CONFIRMATION",
            "amount_paid_inr": 14999.0,
            "brand_raw": "Flipkart",
            "missing_fields": [],
        }
        await repo.save_session_state(user_id, test_state)

        # 3. Load session and verify
        loaded = await repo.load_session_state(user_id)
        assert loaded is not None
        assert loaded["status"] == "AWAITING_CONFIRMATION"
        assert loaded["brand_raw"] == "Flipkart"
        assert loaded["amount_paid_inr"] == 14999.0

        # 4. Update session
        test_state["status"] = "GENERATED"
        await repo.save_session_state(user_id, test_state)
        updated = await repo.load_session_state(user_id)
        assert updated["status"] == "GENERATED"

        # 5. Clear session
        await repo.clear_session_state(user_id)
        cleared = await repo.load_session_state(user_id)
        assert cleared is None

