from pydantic import BaseModel, Field


class DisputeCaseDraft(BaseModel):
    brand_raw: str | None = None
    category: str | None = None
    issue_type: str | None = None
    product_name: str | None = None
    order_id: str | None = None
    incident_date: str | None = None  # YYYY-MM-DD
    amount_paid_inr: float | None = None
    complainant_full_name: str | None = None
    complainant_contact: str | None = None
    incident_summary: str | None = None
    missing_critical_fields: list[str] = Field(default_factory=list)

    def check_missing_fields(self) -> list[str]:
        missing = []
        if not self.brand_raw:
            missing.append("brand_raw")
        if self.amount_paid_inr is None or self.amount_paid_inr <= 0:
            missing.append("amount_paid_inr")
        if not self.incident_date:
            missing.append("incident_date")
        if not self.order_id:
            missing.append("order_id")
        if not self.complainant_full_name:
            missing.append("complainant_full_name")
        self.missing_critical_fields = missing
        return missing
