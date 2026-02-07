"""Client for Ofsted inspection data.

Provides URL generation, rating formatting, and full inspection data
by downloading the Ofsted Management Information files from GOV.UK.

The MI dataset contains detailed inspection outcomes for all state-funded schools:
- Overall effectiveness grade (1-4)
- Grades for each inspection judgement area
- Inspection date and type
- Previous inspection results

Data source: https://www.gov.uk/government/statistical-data-sets/monthly-management-information-ofsteds-school-inspections-outcomes
"""

import io
import logging
import re
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import polars as pl

logger = logging.getLogger(__name__)

OFSTED_MI_PAGE = (
    "https://www.gov.uk/government/statistical-data-sets/"
    "monthly-management-information-ofsteds-school-inspections-outcomes"
)

# GOV.UK Content API endpoint for structured data
GOVUK_CONTENT_API = (
    "https://www.gov.uk/api/content/government/statistical-data-sets/"
    "monthly-management-information-ofsteds-school-inspections-outcomes"
)

RATINGS = {
    "1": "Outstanding",
    "2": "Good",
    "3": "Requires Improvement",
    "4": "Inadequate",
    "8": "Does not apply",
    "9": "No judgement",
}

# Column mappings from Ofsted MI Excel to cleaner names
MI_COLUMN_MAP = {
    "URN": "urn",
    "LAESTAB": "laestab",
    "School name": "school_name",
    "Ofsted phase": "ofsted_phase",
    "Type of education": "type_of_education",
    "Local authority": "local_authority",
    "Region": "region",
    "Overall effectiveness": "overall_effectiveness",
    "Quality of education": "quality_of_education",
    "Behaviour and attitudes": "behaviour_and_attitudes",
    "Personal development": "personal_development",
    "Leadership and management": "leadership_and_management",
    "Early years provision (where applicable)": "early_years_provision",
    "Sixth form provision (where applicable)": "sixth_form_provision",
    "Previous overall effectiveness": "previous_overall_effectiveness",
    "Previous quality of education": "previous_quality_of_education",
    "Previous behaviour and attitudes": "previous_behaviour_and_attitudes",
    "Previous personal development": "previous_personal_development",
    "Previous leadership and management": "previous_leadership_and_management",
    "Inspection start date": "inspection_start_date",
    "Inspection end date": "inspection_end_date",
    "Inspection type": "inspection_type",
    "Publication date": "publication_date",
    "Does the latest full inspection relate to the URN of the current school?": "relates_to_current_urn",
    "Category of concern": "category_of_concern",
    "Number of previous inspections": "number_of_previous_inspections",
    "Previous inspection start date": "previous_inspection_start_date",
    "Previous publication date": "previous_publication_date",
}


class OfstedClient:
    """Client for Ofsted inspection data and report URLs.

    Downloads the Ofsted Management Information Excel file from GOV.UK,
    caches it locally, and provides lookup by URN for inspection grades.
    """

    def __init__(self, cache_dir: Path | None = None):
        self._df: pl.DataFrame | None = None
        self._cache_dir = cache_dir or Path.home() / ".cache" / "uk-schools-mcp"
        self._http = httpx.AsyncClient(timeout=60.0, follow_redirects=True)

    async def close(self):
        await self._http.aclose()

    @staticmethod
    def ofsted_report_url(urn: int) -> str:
        """Generate the Ofsted report URL for a school."""
        return f"https://reports.ofsted.gov.uk/provider/17/{urn}"

    @staticmethod
    def format_rating(rating_code: str | int | None) -> str:
        """Convert Ofsted rating code to human-readable string."""
        if rating_code is None:
            return "Not yet inspected"
        return RATINGS.get(str(rating_code).strip(), f"Unknown ({rating_code})")

    async def _find_download_url(self) -> str:
        """Find the state-funded schools MI Excel download URL from GOV.UK Content API."""
        try:
            response = await self._http.get(GOVUK_CONTENT_API)
            response.raise_for_status()
            data = response.json()

            # Navigate the GOV.UK content structure to find attachments
            for detail_doc in data.get("details", {}).get("documents", []):
                # Documents in GOV.UK content API are HTML snippets
                # containing links to attachments
                if "state-funded" in detail_doc.lower() and ".xlsx" in detail_doc.lower():
                    # Extract URL from the HTML
                    match = re.search(r'href="([^"]*\.xlsx[^"]*)"', detail_doc)
                    if match:
                        return match.group(1)

            # Try alternate structure - attachments directly
            for attachment in data.get("details", {}).get("attachments", []):
                title = attachment.get("title", "").lower()
                url = attachment.get("url", "")
                if "state-funded" in title and url.endswith(".xlsx"):
                    return url
                if "state_funded" in url and url.endswith(".xlsx"):
                    return url

        except Exception as e:
            logger.warning("Could not find MI download URL via Content API: %s", e)

        # Fallback: try fetching the HTML page directly
        try:
            response = await self._http.get(OFSTED_MI_PAGE)
            response.raise_for_status()
            text = response.text
            # Look for state-funded schools Excel link
            matches = re.findall(r'href="([^"]*state.funded[^"]*\.xlsx)"', text, re.IGNORECASE)
            if not matches:
                matches = re.findall(r'href="([^"]*state_funded[^"]*\.xlsx)"', text, re.IGNORECASE)
            if not matches:
                # Broader search for any xlsx on assets.publishing.service.gov.uk
                matches = re.findall(
                    r'href="(https://assets\.publishing\.service\.gov\.uk/[^"]*\.xlsx)"',
                    text,
                    re.IGNORECASE,
                )
            if matches:
                # Prefer the one with "state" in the name
                for m in matches:
                    if "state" in m.lower():
                        return m
                return matches[0]
        except Exception as e:
            logger.warning("Could not find MI download URL via HTML scrape: %s", e)

        raise RuntimeError(
            "Could not find Ofsted MI download URL. "
            "The GOV.UK page structure may have changed. "
            f"Check manually: {OFSTED_MI_PAGE}"
        )

    async def _download_mi_data(self) -> bytes:
        """Download the Ofsted MI Excel file."""
        url = await self._find_download_url()
        logger.info("Downloading Ofsted MI data from: %s", url)

        response = await self._http.get(url)
        response.raise_for_status()

        if len(response.content) < 1000:
            raise RuntimeError(f"Downloaded file too small ({len(response.content)} bytes), likely an error page")

        return response.content

    async def _ensure_data(self) -> pl.DataFrame:
        """Load Ofsted MI data, downloading if not cached this month."""
        if self._df is not None:
            return self._df

        today = date.today()
        cache_file = self._cache_dir / f"ofsted_mi_{today.strftime('%Y-%m')}.parquet"

        if cache_file.exists():
            logger.info("Loading Ofsted MI data from cache: %s", cache_file)
            self._df = pl.read_parquet(cache_file)
            return self._df

        # Download and parse
        xlsx_bytes = await self._download_mi_data()
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # Parse Excel - the state-funded schools sheet
        try:
            df = pl.read_excel(io.BytesIO(xlsx_bytes), sheet_id=1, infer_schema_length=0)
        except Exception:
            # Try with sheet name patterns
            df = pl.read_excel(io.BytesIO(xlsx_bytes), sheet_name=None, infer_schema_length=0)
            if isinstance(df, dict):
                # Multiple sheets - find the right one
                for sheet_name, sheet_df in df.items():
                    if "urn" in sheet_name.lower() or "school" in sheet_name.lower() or len(sheet_df) > 100:
                        df = sheet_df
                        break
                else:
                    # Use the first sheet with the most rows
                    df = max(df.values(), key=len)

        # Rename columns where possible
        renames = {}
        for col in df.columns:
            col_stripped = col.strip()
            if col_stripped in MI_COLUMN_MAP:
                renames[col] = MI_COLUMN_MAP[col_stripped]
            elif col != col_stripped:
                renames[col] = col_stripped
        if renames:
            df = df.rename(renames)

        # Ensure URN column exists (try case-insensitive match)
        if "urn" not in df.columns:
            for col in df.columns:
                if col.upper() == "URN":
                    df = df.rename({col: "urn"})
                    break

        # Cache as parquet for faster subsequent loads
        df.write_parquet(cache_file)
        self._df = df
        logger.info("Loaded %d Ofsted inspection records", len(df))
        return df

    async def get_inspection(self, urn: int) -> dict[str, Any] | None:
        """Get the latest Ofsted inspection data for a school by URN.

        Returns a dict with inspection grades and dates, or None if not found.
        """
        df = await self._ensure_data()

        urn_str = str(urn)
        result = df.filter(pl.col("urn") == urn_str)

        if len(result) == 0:
            # Try as integer
            try:
                result = df.filter(pl.col("urn").cast(pl.Int64, strict=False) == urn)
            except Exception:
                pass

        if len(result) == 0:
            return None

        # Take the most recent inspection (last row for this URN)
        row = result.to_dicts()[-1]

        # Build clean result
        inspection: dict[str, Any] = {"urn": urn}

        # Map grades to readable strings
        grade_fields = [
            ("overall_effectiveness", "Overall Effectiveness"),
            ("quality_of_education", "Quality of Education"),
            ("behaviour_and_attitudes", "Behaviour and Attitudes"),
            ("personal_development", "Personal Development"),
            ("leadership_and_management", "Leadership and Management"),
            ("early_years_provision", "Early Years Provision"),
            ("sixth_form_provision", "Sixth Form Provision"),
        ]

        for field, label in grade_fields:
            val = row.get(field)
            if val is not None and str(val).strip() and str(val).strip() not in ("", "NULL", "None"):
                code = str(val).strip()
                inspection[field] = code
                inspection[f"{field}_text"] = self.format_rating(code)

        # Previous grades
        prev_grade_fields = [
            ("previous_overall_effectiveness", "Previous Overall Effectiveness"),
            ("previous_quality_of_education", "Previous Quality of Education"),
            ("previous_behaviour_and_attitudes", "Previous Behaviour and Attitudes"),
            ("previous_personal_development", "Previous Personal Development"),
            ("previous_leadership_and_management", "Previous Leadership and Management"),
        ]

        for field, label in prev_grade_fields:
            val = row.get(field)
            if val is not None and str(val).strip() and str(val).strip() not in ("", "NULL", "None"):
                code = str(val).strip()
                inspection[field] = code
                inspection[f"{field}_text"] = self.format_rating(code)

        # Dates and other info
        text_fields = [
            "school_name",
            "ofsted_phase",
            "type_of_education",
            "local_authority",
            "region",
            "inspection_start_date",
            "inspection_end_date",
            "inspection_type",
            "publication_date",
            "category_of_concern",
            "number_of_previous_inspections",
            "previous_inspection_start_date",
            "previous_publication_date",
        ]

        for field in text_fields:
            val = row.get(field)
            if val is not None and str(val).strip() and str(val).strip() not in ("", "NULL", "None"):
                inspection[field] = str(val).strip()

        inspection["report_url"] = self.ofsted_report_url(urn)
        return inspection

    async def get_inspections_batch(self, urns: list[int]) -> dict[int, dict[str, Any]]:
        """Get Ofsted inspection data for multiple schools by URN.

        Returns a dict mapping URN to inspection data.
        """
        df = await self._ensure_data()
        results = {}

        urn_strs = [str(u) for u in urns]
        matched = df.filter(pl.col("urn").is_in(urn_strs))

        if len(matched) == 0:
            # Try integer comparison
            try:
                matched = df.filter(pl.col("urn").cast(pl.Int64, strict=False).is_in(urns))
            except Exception:
                pass

        for row in matched.to_dicts():
            urn_val = row.get("urn")
            if urn_val is not None:
                try:
                    urn_int = int(urn_val)
                except (ValueError, TypeError):
                    continue
                # Keep the latest entry per URN (last one wins)
                results[urn_int] = row

        # Format each result
        formatted = {}
        for urn_int, row in results.items():
            inspection = await self.get_inspection(urn_int)
            if inspection:
                formatted[urn_int] = inspection

        return formatted
