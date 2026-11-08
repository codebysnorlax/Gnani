from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id = Column(String(64), unique=True, nullable=False, index=True)
    telegram_chat_id = Column(String(64), nullable=False)
    legal_full_name = Column(String(255), nullable=True)
    contact_detail = Column(String(255), nullable=True)
    preferred_language = Column(String(32), nullable=False, default="hi-IN")
    created_at = Column(String(64), nullable=False, default=utcnow_iso)
    updated_at = Column(String(64), nullable=False, default=utcnow_iso, onupdate=utcnow_iso)


class ProcessedUpdate(Base):
    __tablename__ = "processed_updates"

    update_id = Column(String(64), primary_key=True)
    telegram_user_id = Column(String(64), nullable=False)
    processed_at = Column(String(64), nullable=False, default=utcnow_iso)


class BrandDirectoryModel(Base):
    __tablename__ = "brand_directory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_name = Column(String(128), unique=True, nullable=False, index=True)
    aliases_json = Column(Text, nullable=False)
    corporate_name = Column(String(255), nullable=False)
    registered_address = Column(Text, nullable=False)
    nodal_officer_name = Column(String(255), nullable=True)
    nodal_email = Column(String(255), nullable=False)
    twitter_handle = Column(String(128), nullable=True)
    category = Column(String(64), nullable=False)


class DisputeCase(Base):
    __tablename__ = "dispute_cases"

    id = Column(String(64), primary_key=True)  # e.g. CD-YYYY-XXXX
    telegram_user_id = Column(String(64), nullable=False, index=True)
    complainant_name = Column(String(255), nullable=False)
    complainant_contact = Column(String(255), nullable=False)
    brand_name = Column(String(128), nullable=False)
    brand_corporate_name = Column(String(255), nullable=False)
    registered_address = Column(Text, nullable=False)
    nodal_email = Column(String(255), nullable=False)
    order_id = Column(String(128), nullable=False)
    incident_date = Column(String(32), nullable=False)
    category = Column(String(64), nullable=False)
    issue_type = Column(String(128), nullable=False)
    principal_paise = Column(Integer, nullable=False)
    interest_paise = Column(Integer, nullable=False, default=0)
    statutory_penalty_paise = Column(Integer, nullable=False, default=0)
    damages_demanded_paise = Column(Integer, nullable=False, default=0)
    total_demanded_paise = Column(Integer, nullable=False)
    narrative_facts_en = Column(Text, nullable=False)
    legal_clauses_json = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="DRAFT")
    created_at = Column(String(64), nullable=False, default=utcnow_iso)
    updated_at = Column(String(64), nullable=False, default=utcnow_iso, onupdate=utcnow_iso)

    artifacts = relationship(
        "GeneratedArtifact",
        back_populates="dispute_case",
        cascade="all, delete-orphan",
    )


class GeneratedArtifact(Base):
    __tablename__ = "generated_artifacts"

    id = Column(String(64), primary_key=True)  # UUID
    dispute_case_id = Column(
        String(64),
        ForeignKey("dispute_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_type = Column(String(64), nullable=False)
    file_path = Column(Text, nullable=True)
    content_text = Column(Text, nullable=True)
    created_at = Column(String(64), nullable=False, default=utcnow_iso)

    dispute_case = relationship("DisputeCase", back_populates="artifacts")


class UserSession(Base):
    __tablename__ = "user_sessions"

    telegram_user_id = Column(String(64), primary_key=True, index=True)
    state_json = Column(Text, nullable=False)
    status = Column(String(64), nullable=False, default="INIT")
    updated_at = Column(String(64), nullable=False, default=utcnow_iso, onupdate=utcnow_iso)

