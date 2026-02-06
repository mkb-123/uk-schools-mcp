"""Client for Postcodes.io - free UK postcode geocoding API.

No authentication required. Docs: https://postcodes.io/
"""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.postcodes.io"


class PostcodesClient:
    """Client for geocoding UK postcodes via postcodes.io."""

    def __init__(self):
        self._http = httpx.AsyncClient(timeout=15.0, base_url=BASE_URL)

    async def close(self):
        await self._http.aclose()

    async def lookup(self, postcode: str) -> dict[str, Any]:
        """Look up a UK postcode and return location data.

        Returns dict with keys: postcode, latitude, longitude, admin_district,
        parish, parliamentary_constituency, region, country, etc.

        Raises ValueError if postcode is not found.
        """
        response = await self._http.get(f"/postcodes/{postcode.strip()}")
        data = response.json()
        if data.get("status") != 200 or data.get("result") is None:
            raise ValueError(f"Postcode not found: {postcode}")
        return data["result"]

    async def geocode(self, postcode: str) -> tuple[float, float]:
        """Convert a postcode to (latitude, longitude) tuple."""
        result = await self.lookup(postcode)
        return result["latitude"], result["longitude"]

    async def reverse_geocode(self, lat: float, lng: float) -> list[dict[str, Any]]:
        """Find postcodes near a lat/lng coordinate."""
        response = await self._http.get(
            "/postcodes",
            params={"lat": lat, "lon": lng, "limit": 5},
        )
        data = response.json()
        if data.get("status") != 200 or data.get("result") is None:
            return []
        return data["result"]

    async def validate(self, postcode: str) -> bool:
        """Check if a postcode is valid."""
        response = await self._http.get(f"/postcodes/{postcode.strip()}/validate")
        data = response.json()
        return data.get("result", False)
