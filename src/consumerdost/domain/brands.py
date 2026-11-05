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

    def resolve(self, query: str | None, threshold: float = 85.0) -> BrandInfo | None:
        if not query:
            return None
        q = query.strip().lower()
        if not q:
            return None

        # 1. Exact match
        if q in self.alias_to_brand:
            return self.alias_to_brand[q]

        # 2. RapidFuzz match against all aliases
        if not self.all_aliases:
            return None

        match = process.extractOne(
            q,
            self.all_aliases,
            scorer=fuzz.WRatio,
            score_cutoff=threshold,
        )
        if match:
            matched_alias, score, _ = match
            return self.alias_to_brand[matched_alias]

        return None


# Global singleton instance
brand_directory = BrandDirectory()


def resolve_brand(query: str | None, threshold: float = 85.0) -> BrandInfo | None:
    return brand_directory.resolve(query, threshold=threshold)
