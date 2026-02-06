"""Client for school-finder API at https://school-finder.fly.dev"""

import httpx
from typing import Any


class SchoolFinderClient:
    """Client for fetching school data from the deployed school-finder API."""

    def __init__(self, base_url: str = "https://school-finder.fly.dev"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def search_schools(
        self,
        query: str | None = None,
        council: str | None = None,
        school_type: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for schools by name, postcode, or council.

        Args:
            query: School name or postcode
            council: Local authority name
            school_type: Filter by school type
            limit: Maximum number of results

        Returns:
            List of school dictionaries
        """
        params = {
            "limit": limit,
        }
        if query:
            params["search"] = query
        if council:
            params["council"] = council
        if school_type:
            params["school_type"] = school_type

        response = await self.client.get(f"{self.base_url}/api/schools", params=params)
        response.raise_for_status()
        return response.json()

    async def get_school_by_id(self, school_id: int) -> dict[str, Any]:
        """Get full details for a specific school.

        Args:
            school_id: The school's database ID

        Returns:
            School detail dictionary with all information
        """
        response = await self.client.get(f"{self.base_url}/api/schools/{school_id}")
        response.raise_for_status()
        return response.json()

    async def find_schools_in_catchment(
        self,
        lat: float,
        lng: float,
        radius_km: float = 3.0,
        school_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Find schools within a radius of a location.

        Args:
            lat: Latitude
            lng: Longitude
            radius_km: Search radius in kilometres
            school_type: Optional school type filter

        Returns:
            List of schools sorted by distance
        """
        params = {
            "lat": lat,
            "lng": lng,
            "max_distance_km": radius_km,
            "limit": 50,
        }
        if school_type:
            params["school_type"] = school_type

        response = await self.client.get(f"{self.base_url}/api/schools", params=params)
        response.raise_for_status()
        return response.json()

    async def compare_schools(self, school_ids: list[int]) -> dict[str, Any]:
        """Compare multiple schools side-by-side.

        Args:
            school_ids: List of 2-4 school IDs to compare

        Returns:
            Comparison data dictionary
        """
        ids_param = ",".join(str(id) for id in school_ids)
        response = await self.client.get(
            f"{self.base_url}/api/compare",
            params={"school_ids": ids_param}
        )
        response.raise_for_status()
        return response.json()

    async def geocode_postcode(self, postcode: str) -> dict[str, Any]:
        """Convert UK postcode to lat/lng coordinates.

        Args:
            postcode: UK postcode (e.g., "MK9 3BZ")

        Returns:
            Dictionary with latitude, longitude, and other postcode data
        """
        response = await self.client.get(
            f"{self.base_url}/api/geocode",
            params={"postcode": postcode}
        )
        response.raise_for_status()
        return response.json()
