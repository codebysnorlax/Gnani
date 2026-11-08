import json
from pathlib import Path
from typing import TypedDict
from rapidfuzz import process, fuzz
from consumerdost.config import settings


class BrandInfo(TypedDict):
    canonical_name: str
    aliases: list[str]
    corporate_name: str
    registered_address: str
    nodal_officer_name: str | None
    nodal_email: str
    twitter_handle: str | None
    category: str


class BrandDirectory:
    def __init__(self, json_path: Path | None = None):
        self.json_path = json_path or (settings.data_dir / "brands.json")
        self.brands: list[BrandInfo] = []
        self.alias_to_brand: dict[str, BrandInfo] = {}
        self.all_aliases: list[str] = []
        self._load()

    def _load(self) -> None:
        if not self.json_path.exists():
            return
        with open(self.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.brands = data

        for brand in self.brands:
            canonical = brand["canonical_name"].lower()
            self.alias_to_brand[canonical] = brand
            if canonical not in self.all_aliases:
                self.all_aliases.append(canonical)

            for alias in brand.get("aliases", []):
                alias_clean = alias.strip().lower()
                self.alias_to_brand[alias_clean] = brand
                if alias_clean not in self.all_aliases:
                    self.all_aliases.append(alias_clean)

    def resolve(
        self,
        query: str | None,
        threshold: float = 85.0,
        fallback_if_unknown: bool = False,
        custom_email: str | None = None,
        custom_address: str | None = None,
    ) -> BrandInfo | None:
        if not query:
            if fallback_if_unknown:
                return create_fallback_brand("Unknown Vendor", nodal_email=custom_email, registered_address=custom_address)
            return None
        q = query.strip().lower()
        if not q:
            if fallback_if_unknown:
                return create_fallback_brand("Unknown Vendor", nodal_email=custom_email, registered_address=custom_address)
            return None

        # 1. Exact match
        if q in self.alias_to_brand:
            return self.alias_to_brand[q]

        # 2. RapidFuzz match against all aliases
        if self.all_aliases:
            match = process.extractOne(
                q,
                self.all_aliases,
                scorer=fuzz.WRatio,
                score_cutoff=threshold,
            )
            if match:
                matched_alias, score, _ = match
                return self.alias_to_brand[matched_alias]

        if fallback_if_unknown:
            return create_fallback_brand(query, nodal_email=custom_email, registered_address=custom_address)

        return None


def create_fallback_brand(
    name: str,
    nodal_email: str | None = None,
    registered_address: str | None = None,
    category: str = "OTHER",
) -> BrandInfo:
    """Create a structured BrandInfo for an unindexed or local vendor."""
    clean_name = name.strip() if name else "Unknown Vendor"
    slug = clean_name.lower().replace(" ", "")
    return {
        "canonical_name": clean_name.upper(),
        "aliases": [clean_name.lower()],
        "corporate_name": clean_name,
        "registered_address": registered_address or "Registered Office, India",
        "nodal_officer_name": "Nodal Grievance Officer",
        "nodal_email": nodal_email or f"grievance@{slug}.com",
        "twitter_handle": f"@{clean_name.replace(' ', '')}",
        "category": category,
    }


# Global singleton instance
brand_directory = BrandDirectory()


def resolve_brand(
    query: str | None,
    threshold: float = 85.0,
    fallback_if_unknown: bool = False,
    custom_email: str | None = None,
    custom_address: str | None = None,
) -> BrandInfo | None:
    return brand_directory.resolve(
        query,
        threshold=threshold,
        fallback_if_unknown=fallback_if_unknown,
        custom_email=custom_email,
        custom_address=custom_address,
    )
