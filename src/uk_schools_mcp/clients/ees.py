"""Client for the Explore Education Statistics (EES) API.

Provides access to DfE published statistics including school performance,
pupil characteristics, absence, exclusions, and applications/offers data.

API docs: https://api.education.gov.uk/statistics/docs/
Base URL: https://api.education.gov.uk/statistics/v1
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.education.gov.uk/statistics/v1"


class EESClient:
    """Client for DfE Explore Education Statistics API."""

    def __init__(self):
        self._http = httpx.AsyncClient(timeout=30.0, base_url=BASE_URL)

    async def close(self):
        await self._http.aclose()

    async def list_publications(self, search: str | None = None, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        """List available publications, optionally filtered by search term.

        Publications include datasets on school performance, absence,
        exclusions, applications & offers, workforce, etc.
        """
        params: dict[str, Any] = {"page": page, "pageSize": page_size}
        if search:
            params["search"] = search
        response = await self._http.get("/publications", params=params)
        response.raise_for_status()
        return response.json()

    async def get_publication(self, publication_id: str) -> dict[str, Any]:
        """Get details for a specific publication."""
        response = await self._http.get(f"/publications/{publication_id}")
        response.raise_for_status()
        return response.json()

    async def list_data_sets(self, publication_id: str) -> dict[str, Any]:
        """List data sets available for a publication."""
        response = await self._http.get(f"/publications/{publication_id}/data-sets")
        response.raise_for_status()
        return response.json()

    async def get_data_set(self, data_set_id: str) -> dict[str, Any]:
        """Get summary information about a data set."""
        response = await self._http.get(f"/data-sets/{data_set_id}")
        response.raise_for_status()
        return response.json()

    async def get_data_set_meta(self, data_set_id: str) -> dict[str, Any]:
        """Get metadata (available filters, indicators, locations) for a data set."""
        response = await self._http.get(f"/data-sets/{data_set_id}/meta")
        response.raise_for_status()
        return response.json()

    async def query_data_set(
        self,
        data_set_id: str,
        indicators: list[str],
        time_periods: list[str] | None = None,
        geographic_levels: list[str] | None = None,
        locations: list[str] | None = None,
        filters: list[str] | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> dict[str, Any]:
        """Query a data set with filters.

        Args:
            data_set_id: The data set ID
            indicators: List of indicator IDs to include
            time_periods: e.g. ["2024|AY"] for academic year 2024
            geographic_levels: e.g. ["NAT", "REG", "LA"]
            locations: e.g. ["LA|code|123"]
            filters: Filter option IDs
            page: Page number
            page_size: Results per page
        """
        body: dict[str, Any] = {
            "indicators": indicators,
            "page": page,
            "pageSize": page_size,
        }
        criteria: dict[str, Any] = {}
        if time_periods:
            criteria["timePeriods"] = {
                "in": [{"period": tp.split("|")[0], "code": tp.split("|")[1]} for tp in time_periods]
            }
        if geographic_levels:
            criteria["geographicLevels"] = {"in": geographic_levels}
        if locations:
            parsed = []
            for loc in locations:
                parts = loc.split("|")
                if len(parts) == 3:
                    parsed.append({"level": parts[0], parts[1]: parts[2]})
            if parsed:
                criteria["locations"] = {"in": parsed}
        if filters:
            criteria["filters"] = {"in": filters}
        if criteria:
            body["criteria"] = criteria

        response = await self._http.post(f"/data-sets/{data_set_id}/query", json=body)
        response.raise_for_status()
        return response.json()

    async def search_publications_for_topic(self, topic: str) -> list[dict[str, Any]]:
        """Search for publications matching a topic and return simplified results."""
        data = await self.list_publications(search=topic, page_size=10)
        results = []
        for pub in data.get("results", []):
            results.append({
                "id": pub.get("id"),
                "title": pub.get("title"),
                "summary": pub.get("summary"),
                "slug": pub.get("slug"),
            })
        return results
