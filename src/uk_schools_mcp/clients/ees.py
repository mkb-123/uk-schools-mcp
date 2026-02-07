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

# Registry of known EES topics with search terms and descriptions.
# Each entry maps a short topic key to its search query and a human description
# of what data is available.
EES_TOPICS: dict[str, dict[str, str]] = {
    "absence": {
        "search": "pupil absence in schools in England",
        "title": "Pupil Absence",
        "description": (
            "Overall and persistent absence rates, authorised vs unauthorised absence, "
            "breakdown by reason, school type, and pupil characteristics. "
            "Available at national, regional, LA, and school level."
        ),
    },
    "exclusions": {
        "search": "permanent exclusions and suspensions in England",
        "title": "Exclusions and Suspensions",
        "description": (
            "Permanent exclusion rates, suspension (fixed-period exclusion) rates, "
            "breakdown by reason, ethnicity, SEN status, FSM eligibility, gender. "
            "Available at national, regional, LA, and school level."
        ),
    },
    "ks2_performance": {
        "search": "key stage 2 attainment",
        "title": "KS2 Performance (Primary SATs)",
        "description": (
            "Key Stage 2 attainment: reading, writing, maths scores, "
            "expected standard %, higher standard %, combined measures. "
            "Breakdowns by pupil characteristics, school type."
        ),
    },
    "gcse_performance": {
        "search": "key stage 4 performance GCSE",
        "title": "KS4 Performance (GCSEs)",
        "description": (
            "GCSE results: Attainment 8, Progress 8, EBacc entry and achievement, "
            "Grade 5+ in English and maths, average grade. "
            "Breakdowns by pupil characteristics, school type."
        ),
    },
    "a_level_performance": {
        "search": "key stage 5 A level performance",
        "title": "KS5 Performance (A-levels)",
        "description": (
            "A-level and equivalent results: average point score, A*-B %, "
            "value added measures, tech level and applied general results."
        ),
    },
    "applications_offers": {
        "search": "secondary and primary school applications and offers",
        "title": "School Applications and Offers",
        "description": (
            "School admissions data: first, second, third preference applications, "
            "offers made by preference rank, National Offer Day statistics. "
            "Historical data back to 2014."
        ),
    },
    "workforce": {
        "search": "school workforce in England",
        "title": "School Workforce",
        "description": (
            "Teacher numbers, pupil-teacher ratios, teacher qualifications, "
            "staff turnover and vacancy rates, support staff numbers, "
            "teacher pay, demographics."
        ),
    },
    "sen": {
        "search": "special educational needs in England",
        "title": "Special Educational Needs (SEND)",
        "description": (
            "Pupils with EHC plans, SEN support numbers, type of primary need, "
            "placement type, demographic breakdowns (ethnicity, FSM, language). "
            "Available at national, regional, LA, and school level."
        ),
    },
    "school_pupils_characteristics": {
        "search": "school pupils and their characteristics",
        "title": "Schools, Pupils and Their Characteristics",
        "description": (
            "Per-school pupil headcount by year group, age, sex, FSM eligibility, "
            "ethnicity, English as additional language, young carers, class sizes. "
            "Comprehensive school-level demographics."
        ),
    },
    "free_school_meals": {
        "search": "free school meals",
        "title": "Free School Meals",
        "description": (
            "FSM eligibility rates at school, LA, regional, and national levels. "
            "Includes take-up rates and Universal Infant FSM data."
        ),
    },
    "school_capacity": {
        "search": "school capacity",
        "title": "School Capacity (SCAP)",
        "description": (
            "School capacity by LA, pupil forecasts, planned place changes, "
            "SEN provision capacity. Based on annual statutory SCAP survey."
        ),
    },
    "admission_appeals": {
        "search": "admission appeals in England",
        "title": "Admission Appeals",
        "description": (
            "Number of appeals lodged, heard, and upheld by LA, school phase, "
            "and governance type."
        ),
    },
    "destinations": {
        "search": "16-18 destination measures",
        "title": "16-18 Destination Measures",
        "description": (
            "Post-16 progression rates to higher education, apprenticeships, "
            "employment. Includes Russell Group and Oxbridge destination rates. "
            "Breakdowns by student characteristics, provider type."
        ),
    },
    "children_looked_after": {
        "search": "children looked after in England including adoptions",
        "title": "Children Looked After",
        "description": (
            "Data on children in care: numbers, placement types, duration in care, "
            "outcomes, adoption, care leavers. Breakdowns by LA."
        ),
    },
    "children_in_need": {
        "search": "outcomes for children in need including children looked after",
        "title": "Children in Need Outcomes",
        "description": (
            "Educational outcomes (KS2, KS4) for children in need and children "
            "looked after, including SEN status, absence, exclusions, attainment."
        ),
    },
    "mat_performance": {
        "search": "multi-academy trust performance measures",
        "title": "Multi-Academy Trust Performance",
        "description": (
            "KS2, KS4, KS5 performance measures at MAT level: Progress 8, "
            "Attainment 8, EBacc entry, breakdowns by pupil characteristics."
        ),
    },
    "school_funding": {
        "search": "school funding statistics",
        "title": "School Funding",
        "description": (
            "Per-pupil funding allocations to LAs and state-funded schools, "
            "including Dedicated Schools Grant (DSG), pupil premium, "
            "Universal Infant Free School Meals grant."
        ),
    },
    "la_school_expenditure": {
        "search": "LA and school expenditure",
        "title": "LA and School Expenditure",
        "description": (
            "Income and expenditure data for LA-maintained schools via "
            "Consistent Financial Reporting (CFR). Note: does not include "
            "academy data."
        ),
    },
    "further_education": {
        "search": "further education and skills",
        "title": "Further Education and Skills",
        "description": (
            "FE learner numbers, apprenticeship starts and achievements, "
            "adult skills participation, qualification achievement rates."
        ),
    },
    "early_years": {
        "search": "childcare and early years provider survey",
        "title": "Early Years and Childcare",
        "description": (
            "Childcare provider numbers, types, costs, workforce, places, "
            "by region and provider type."
        ),
    },
    "early_years_foundation": {
        "search": "early years foundation stage profile",
        "title": "Early Years Foundation Stage Profile",
        "description": (
            "Reception year assessment outcomes: good level of development, "
            "communication and language, physical development, personal/social/emotional, "
            "literacy, mathematics. Breakdowns by pupil characteristics."
        ),
    },
    "neet": {
        "search": "NEET and participation",
        "title": "NEET and Participation (16-24)",
        "description": (
            "Young people not in education, employment or training (NEET): "
            "rates by age, region, and characteristics. Participation in "
            "education and training."
        ),
    },
    "elective_home_education": {
        "search": "elective home education",
        "title": "Elective Home Education",
        "description": (
            "Numbers of children registered for elective home education by LA, "
            "including new registrations and de-registrations."
        ),
    },
}


class EESClient:
    """Client for DfE Explore Education Statistics API."""

    def __init__(self):
        self._http = httpx.AsyncClient(timeout=30.0, base_url=BASE_URL)
        self._topic_cache: dict[str, dict[str, Any]] = {}

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

    async def discover_topic_datasets(self, topic_key: str) -> dict[str, Any]:
        """Discover publications and datasets for a known EES topic.

        Combines search → list datasets into a single call, with caching.
        Returns a dict with topic info, publications found, and their datasets.
        """
        # Check cache first
        if topic_key in self._topic_cache:
            return self._topic_cache[topic_key]

        topic = EES_TOPICS.get(topic_key)
        if topic is None:
            raise ValueError(
                f"Unknown topic '{topic_key}'. "
                f"Available topics: {', '.join(sorted(EES_TOPICS.keys()))}"
            )

        search_term = topic["search"]
        publications = await self.search_publications_for_topic(search_term)

        result: dict[str, Any] = {
            "topic_key": topic_key,
            "title": topic["title"],
            "description": topic["description"],
            "search_term": search_term,
            "publications": [],
        }

        for pub in publications[:5]:  # Limit to top 5 matches
            pub_info: dict[str, Any] = {
                "id": pub["id"],
                "title": pub["title"],
                "summary": pub.get("summary", ""),
                "datasets": [],
            }

            # Fetch datasets for this publication
            try:
                ds_data = await self.list_data_sets(pub["id"])
                for ds in ds_data.get("results", []):
                    ds_info = {
                        "id": ds.get("id"),
                        "title": ds.get("title"),
                        "summary": ds.get("summary", ""),
                    }
                    if ds.get("latestVersion"):
                        ver = ds["latestVersion"]
                        ds_info["version"] = ver.get("number")
                        ds_info["published"] = ver.get("published")
                    pub_info["datasets"].append(ds_info)
            except Exception as e:
                logger.warning("Could not list datasets for publication %s: %s", pub["id"], e)

            result["publications"].append(pub_info)

        # Cache the result
        self._topic_cache[topic_key] = result
        return result
