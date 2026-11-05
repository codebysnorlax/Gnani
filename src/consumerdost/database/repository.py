import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from consumerdost.database.models import (
    User,
    ProcessedUpdate,
    BrandDirectoryModel,
    DisputeCase,
    GeneratedArtifact,
)


def generate_case_ref() -> str:
    year = datetime.now().year
    suffix = uuid.uuid4().hex[:4].upper()
    return f"CD-{year}-{suffix}"


class DisputeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_user(
        self,
        telegram_user_id: str,
        telegram_chat_id: str,
        preferred_language: str = "hi-IN",
    ) -> User:
        stmt = select(User).where(User.telegram_user_id == telegram_user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                telegram_user_id=telegram_user_id,
                telegram_chat_id=telegram_chat_id,
                preferred_language=preferred_language,
            )
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
        return user

    async def update_user_profile(
        self,
        telegram_user_id: str,
        legal_full_name: str | None = None,
        contact_detail: str | None = None,
        preferred_language: str | None = None,
    ) -> User | None:
        stmt = select(User).where(User.telegram_user_id == telegram_user_id)
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            if legal_full_name is not None:
                user.legal_full_name = legal_full_name
            if contact_detail is not None:
                user.contact_detail = contact_detail
            if preferred_language is not None:
                user.preferred_language = preferred_language
            await self.session.commit()
            await self.session.refresh(user)
        return user

    async def is_update_processed(self, update_id: str) -> bool:
        stmt = select(ProcessedUpdate).where(ProcessedUpdate.update_id == update_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def mark_update_processed(self, update_id: str, telegram_user_id: str) -> None:
        record = ProcessedUpdate(update_id=update_id, telegram_user_id=telegram_user_id)
        self.session.add(record)
        await self.session.commit()

    async def create_dispute_case(
        self,
        telegram_user_id: str,
        complainant_name: str,
        complainant_contact: str,
        brand_name: str,
        brand_corporate_name: str,
        registered_address: str,
        nodal_email: str,
        order_id: str,
        incident_date: str,
        category: str,
        issue_type: str,
        principal_paise: int,
        interest_paise: int,
        statutory_penalty_paise: int,
        damages_demanded_paise: int,
        total_demanded_paise: int,
        narrative_facts_en: str,
        legal_clauses: list[str],
        status: str = "ASSESSED",
        case_id: str | None = None,
    ) -> DisputeCase:
        cid = case_id or generate_case_ref()
        dispute = DisputeCase(
            id=cid,
            telegram_user_id=telegram_user_id,
            complainant_name=complainant_name,
            complainant_contact=complainant_contact,
            brand_name=brand_name,
            brand_corporate_name=brand_corporate_name,
            registered_address=registered_address,
            nodal_email=nodal_email,
            order_id=order_id,
            incident_date=incident_date,
            category=category,
            issue_type=issue_type,
            principal_paise=principal_paise,
            interest_paise=interest_paise,
            statutory_penalty_paise=statutory_penalty_paise,
            damages_demanded_paise=damages_demanded_paise,
            total_demanded_paise=total_demanded_paise,
            narrative_facts_en=narrative_facts_en,
            legal_clauses_json=json.dumps(legal_clauses),
            status=status,
        )
        self.session.add(dispute)
        await self.session.commit()
        await self.session.refresh(dispute)
        return dispute

    async def add_artifact(
        self,
        dispute_case_id: str,
        artifact_type: str,
        file_path: str | None = None,
        content_text: str | None = None,
    ) -> GeneratedArtifact:
        art_id = str(uuid.uuid4())
        art = GeneratedArtifact(
            id=art_id,
            dispute_case_id=dispute_case_id,
            artifact_type=artifact_type,
            file_path=file_path,
            content_text=content_text,
        )
        self.session.add(art)
        await self.session.commit()
        await self.session.refresh(art)
        return art

    async def get_user_cases(self, telegram_user_id: str) -> list[DisputeCase]:
        stmt = (
            select(DisputeCase)
            .where(DisputeCase.telegram_user_id == telegram_user_id)
            .order_by(DisputeCase.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_user_data(self, telegram_user_id: str) -> int:
        """Purge all user disputes, artifacts, and account rows for /privacy."""
        # Find cases to delete
        stmt_cases = select(DisputeCase.id).where(DisputeCase.telegram_user_id == telegram_user_id)
        res = await self.session.execute(stmt_cases)
        case_ids = list(res.scalars().all())

        if case_ids:
            # Delete artifacts
            await self.session.execute(
                delete(GeneratedArtifact).where(GeneratedArtifact.dispute_case_id.in_(case_ids))
            )
            # Delete cases
            await self.session.execute(
                delete(DisputeCase).where(DisputeCase.id.in_(case_ids))
            )

        # Delete user
        await self.session.execute(
            delete(User).where(User.telegram_user_id == telegram_user_id)
        )
        await self.session.commit()
        return len(case_ids)

    async def seed_brands(self, brands_json_path: Path) -> int:
        if not brands_json_path.exists():
            return 0
        with open(brands_json_path, "r", encoding="utf-8") as f:
            brands_data = json.load(f)

        count = 0
        for b in brands_data:
            stmt = select(BrandDirectoryModel).where(
                BrandDirectoryModel.canonical_name == b["canonical_name"]
            )
            res = await self.session.execute(stmt)
            existing = res.scalar_one_or_none()
            if not existing:
                bm = BrandDirectoryModel(
                    canonical_name=b["canonical_name"],
                    aliases_json=json.dumps(b.get("aliases", [])),
                    corporate_name=b["corporate_name"],
                    registered_address=b["registered_address"],
                    nodal_officer_name=b.get("nodal_officer_name"),
                    nodal_email=b["nodal_email"],
                    twitter_handle=b.get("twitter_handle"),
                    category=b.get("category", "E_COMMERCE"),
                )
                self.session.add(bm)
                count += 1
        await self.session.commit()
        return count
