"""Client for GIAS (Get Information About Schools) data.

Downloads the daily bulk CSV from the GIAS Azure endpoint and provides
search/lookup functionality over the cached data using polars.

Data source: https://get-information-schools.service.gov.uk/
"""

import io
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx
import polars as pl

logger = logging.getLogger(__name__)

GIAS_CSV_URL = "https://ea-edubase-api-prod.azurewebsites.net/edubase/downloads/public/edubasealldata{date}.csv"
GIAS_DETAIL_URL = "https://get-information-schools.service.gov.uk/Establishments/Establishment/Details/{urn}"

# Key columns to keep for search results (the full CSV has 120+ columns)
SEARCH_COLUMNS = [
    "URN",
    "EstablishmentName",
    "TypeOfEstablishment (name)",
    "EstablishmentStatus (name)",
    "PhaseOfEducation (name)",
    "StatutoryLowAge",
    "StatutoryHighAge",
    "SchoolCapacity",
    "NumberOfPupils",
    "Gender (name)",
    "ReligiousCharacter (name)",
    "AdmissionsPolicy (name)",
    "Street",
    "Locality",
    "Town",
    "County (name)",
    "Postcode",
    "SchoolWebsite",
    "TelephoneNum",
    "HeadFirstName",
    "HeadLastName",
    "HeadPreferredJobTitle",
    "OfstedLastInsp",
    "LA (name)",
    "PercentageFSM",
    "Latitude",
    "Longitude",
]


class GIASClient:
    """Client for searching and retrieving UK school data from GIAS."""

    def __init__(self, cache_dir: Path | None = None):
        self._df: pl.DataFrame | None = None
        self._cache_dir = cache_dir or Path.home() / ".cache" / "uk-schools-mcp"
        self._http = httpx.AsyncClient(timeout=120.0)

    async def close(self):
        await self._http.aclose()

    async def _ensure_data(self) -> pl.DataFrame:
        """Load GIAS data, downloading if not cached today."""
        if self._df is not None:
            return self._df

        cache_file = self._cache_dir / f"gias_{date.today().isoformat()}.csv"

        if cache_file.exists():
            logger.info("Loading GIAS data from cache: %s", cache_file)
            self._df = pl.read_csv(cache_file, infer_schema_length=0, encoding="utf8-lossy")
            return self._df

        # Download fresh data - try today and previous days
        csv_bytes = await self._download_csv()
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_bytes(csv_bytes)

        self._df = pl.read_csv(io.BytesIO(csv_bytes), infer_schema_length=0, encoding="utf8-lossy")
        logger.info("Loaded %d establishments from GIAS", len(self._df))
        return self._df

    async def _download_csv(self) -> bytes:
        """Download the GIAS bulk CSV, trying recent dates."""
        for days_back in range(5):
            target_date = date.today() - timedelta(days=days_back)
            url = GIAS_CSV_URL.format(date=target_date.strftime("%Y%m%d"))
            logger.info("Trying GIAS download: %s", url)
            try:
                response = await self._http.get(url)
                if response.status_code == 200:
                    return response.content
            except httpx.HTTPError:
                continue
        raise RuntimeError("Could not download GIAS data for any recent date")

    def _select_columns(self, df: pl.DataFrame) -> pl.DataFrame:
        """Select only the key columns that exist in the dataframe."""
        available = [c for c in SEARCH_COLUMNS if c in df.columns]
        return df.select(available)

    def _row_to_dict(self, df: pl.DataFrame) -> list[dict[str, Any]]:
        """Convert a polars dataframe to a list of dicts with clean keys."""
        records = df.to_dicts()
        clean = []
        for row in records:
            clean_row = {}
            for k, v in row.items():
                key = k.replace(" (name)", "").replace(" (code)", "")
                key = key.replace("EstablishmentName", "name")
                key = key.replace("TypeOfEstablishment", "type")
                key = key.replace("EstablishmentStatus", "status")
                key = key.replace("PhaseOfEducation", "phase")
                key = key.replace("ReligiousCharacter", "religious_character")
                key = key.replace("AdmissionsPolicy", "admissions_policy")
                key = key.replace("HeadFirstName", "head_first_name")
                key = key.replace("HeadLastName", "head_last_name")
                key = key.replace("HeadPreferredJobTitle", "head_job_title")
                key = key.replace("OfstedLastInsp", "ofsted_last_inspection")
                key = key.replace("LA", "local_authority")
                key = key.replace("TelephoneNum", "telephone")
                key = key.replace("SchoolWebsite", "website")
                key = key.replace("SchoolCapacity", "capacity")
                key = key.replace("NumberOfPupils", "number_of_pupils")
                key = key.replace("StatutoryLowAge", "age_low")
                key = key.replace("StatutoryHighAge", "age_high")
                key = key.replace("PercentageFSM", "fsm_percentage")
                key = key.replace("Gender", "gender")
                key = key.replace("County", "county")
                if v is not None and v != "":
                    clean_row[key] = v
            clean.append(clean_row)
        return clean

    async def search_schools(
        self,
        query: str | None = None,
        local_authority: str | None = None,
        phase: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search for schools by name, postcode, or local authority."""
        df = await self._ensure_data()

        # Only open schools
        if "EstablishmentStatus (name)" in df.columns:
            df = df.filter(pl.col("EstablishmentStatus (name)") == "Open")

        if query:
            q = query.strip().upper()
            # Check if it looks like a postcode
            if any(c.isdigit() for c in q):
                df = df.filter(
                    pl.col("Postcode").str.to_uppercase().str.contains(q, literal=True)
                    | pl.col("EstablishmentName").str.to_uppercase().str.contains(q, literal=True)
                )
            else:
                df = df.filter(
                    pl.col("EstablishmentName").str.to_uppercase().str.contains(q, literal=True)
                )

        if local_authority:
            df = df.filter(
                pl.col("LA (name)").str.to_uppercase().str.contains(local_authority.upper(), literal=True)
            )

        if phase:
            df = df.filter(
                pl.col("PhaseOfEducation (name)").str.to_uppercase().str.contains(phase.upper(), literal=True)
            )

        df = self._select_columns(df.head(limit))
        return self._row_to_dict(df)

    async def get_school_by_urn(self, urn: int) -> dict[str, Any] | None:
        """Get full details for a school by URN."""
        df = await self._ensure_data()
        result = df.filter(pl.col("URN") == str(urn))
        if len(result) == 0:
            return None
        records = result.to_dicts()
        if not records:
            return None
        # Return all non-empty fields
        row = records[0]
        clean = {}
        for k, v in row.items():
            if v is not None and v != "":
                clean[k] = v
        clean["gias_url"] = GIAS_DETAIL_URL.format(urn=urn)
        return clean

    async def find_schools_near(
        self,
        lat: float,
        lng: float,
        radius_km: float = 3.0,
        phase: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Find schools within a radius of a lat/lng coordinate."""
        df = await self._ensure_data()

        # Only open schools
        if "EstablishmentStatus (name)" in df.columns:
            df = df.filter(pl.col("EstablishmentStatus (name)") == "Open")

        if phase:
            df = df.filter(
                pl.col("PhaseOfEducation (name)").str.to_uppercase().str.contains(phase.upper(), literal=True)
            )

        # Filter to schools with coordinates
        df = df.filter(pl.col("Latitude").is_not_null() & (pl.col("Latitude") != ""))

        # Calculate approximate distance using Haversine-like formula
        # At UK latitudes, 1 degree lat ≈ 111km, 1 degree lng ≈ 65km
        lat_col = pl.col("Latitude").cast(pl.Float64)
        lng_col = pl.col("Longitude").cast(pl.Float64)
        dlat = (lat_col - lat) * 111.0
        dlng = (lng_col - lng) * 65.0
        dist = (dlat.pow(2) + dlng.pow(2)).sqrt()

        df = df.with_columns(dist.alias("_distance_km"))
        df = df.filter(pl.col("_distance_km") <= radius_km)
        df = df.sort("_distance_km")
        df = df.head(limit)

        # Get the distance column before selecting
        distances = df.get_column("_distance_km").to_list()
        result = self._row_to_dict(self._select_columns(df))
        for i, row in enumerate(result):
            row["distance_km"] = round(distances[i], 2)
        return result
