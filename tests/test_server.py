"""Tests for the UK Schools MCP Server.

Uses mocking to avoid network calls and external data dependencies.
"""

from unittest.mock import AsyncMock, patch

import pytest

from uk_schools_mcp import server  # noqa: I001
from uk_schools_mcp.clients.ofsted import OfstedClient

# --- Helper fixtures ---


@pytest.fixture(autouse=True)
def _reset_globals():
    """Reset lazy-loaded client globals between tests."""
    server._gias = None
    server._postcodes = None
    server._ees = None
    server._ofsted = None
    yield
    server._gias = None
    server._postcodes = None
    server._ees = None
    server._ofsted = None


def _make_school(**overrides):
    """Create a fake GIAS school record."""
    base = {
        "URN": "109825",
        "EstablishmentName": "Test Academy",
        "TypeOfEstablishment (name)": "Academy Sponsor Led",
        "EstablishmentStatus (name)": "Open",
        "PhaseOfEducation (name)": "Secondary",
        "StatutoryLowAge": "11",
        "StatutoryHighAge": "18",
        "SchoolCapacity": "1200",
        "NumberOfPupils": "1100",
        "Gender (name)": "Mixed",
        "ReligiousCharacter (name)": "Does not apply",
        "AdmissionsPolicy (name)": "Non-selective",
        "Street": "1 School Lane",
        "Town": "Testville",
        "Postcode": "TE1 1ST",
        "SchoolWebsite": "https://test.sch.uk",
        "TelephoneNum": "01234567890",
        "HeadTitle (name)": "Mrs",
        "HeadFirstName": "Jane",
        "HeadLastName": "Smith",
        "HeadPreferredJobTitle": "Principal",
        "OfstedLastInsp": "2023-01-15",
        "LA (name)": "Test County",
        "PercentageFSM": "15.3",
        "Trusts (name)": "Test Trust",
        "SEN1": "Yes",
    }
    base.update(overrides)
    return base


# --- Tool listing ---


async def test_list_tools_returns_all_tools():
    tools = await server.list_tools()
    names = [t.name for t in tools]
    assert "search_schools" in names
    assert "get_school_details" in names
    assert "find_schools_near_postcode" in names
    assert "compare_schools" in names
    assert "search_education_statistics" in names
    assert "get_publication_datasets" in names
    assert "get_dataset_metadata" in names
    assert "query_dataset" in names
    assert "get_ofsted_ratings" in names
    assert len(tools) == 9


# --- search_schools ---


async def test_search_schools_returns_results():
    mock_gias = AsyncMock()
    mock_gias.search_schools.return_value = [
        {"name": "Test Primary", "URN": "100001", "type": "Academy", "phase": "Primary"},
        {"name": "Test Secondary", "URN": "100002", "type": "Academy", "phase": "Secondary"},
    ]
    with patch.object(server, "get_gias", return_value=mock_gias):
        result = await server._handle_search_schools({"query": "Test", "limit": 10})

    assert len(result) == 1
    assert "Found 2 schools" in result[0].text
    assert "Test Primary" in result[0].text
    assert "Test Secondary" in result[0].text


async def test_search_schools_no_results():
    mock_gias = AsyncMock()
    mock_gias.search_schools.return_value = []
    with patch.object(server, "get_gias", return_value=mock_gias):
        result = await server._handle_search_schools({"query": "Nonexistent"})

    assert "No schools found" in result[0].text


async def test_search_schools_with_filters():
    mock_gias = AsyncMock()
    mock_gias.search_schools.return_value = [
        {"name": "Camden Primary", "URN": "100003", "phase": "Primary"},
    ]
    with patch.object(server, "get_gias", return_value=mock_gias):
        result = await server._handle_search_schools({
            "query": "Camden",
            "local_authority": "Camden",
            "phase": "Primary",
            "limit": 5,
        })

    mock_gias.search_schools.assert_called_once_with(
        query="Camden", local_authority="Camden", phase="Primary", limit=5
    )
    assert "in Camden" in result[0].text


async def test_search_schools_limit_capped_at_50():
    mock_gias = AsyncMock()
    mock_gias.search_schools.return_value = []
    with patch.object(server, "get_gias", return_value=mock_gias):
        await server._handle_search_schools({"query": "Test", "limit": 100})

    mock_gias.search_schools.assert_called_once_with(
        query="Test", local_authority=None, phase=None, limit=50
    )


# --- get_school_details ---


async def test_get_school_details_found():
    mock_gias = AsyncMock()
    mock_gias.get_school_by_urn.return_value = _make_school()
    with patch.object(server, "get_gias", return_value=mock_gias):
        result = await server._handle_get_school_details({"urn": 109825})

    text = result[0].text
    assert "Test Academy" in text
    assert "URN: 109825" in text
    assert "Secondary" in text
    assert "1100" in text
    assert "Test Trust" in text
    assert "Jane Smith" in text
    assert "ofsted_report_url" not in text  # Should use formatted URL
    assert "reports.ofsted.gov.uk" in text
    assert "get_ofsted_ratings" in text


async def test_get_school_details_not_found():
    mock_gias = AsyncMock()
    mock_gias.get_school_by_urn.return_value = None
    with patch.object(server, "get_gias", return_value=mock_gias):
        result = await server._handle_get_school_details({"urn": 999999})

    assert "No school found" in result[0].text


# --- find_schools_near_postcode ---


async def test_find_schools_near_postcode():
    mock_postcodes = AsyncMock()
    mock_postcodes.geocode.return_value = (51.5, -0.1)

    mock_gias = AsyncMock()
    mock_gias.find_schools_near.return_value = [
        {"name": "Nearby School", "URN": "100010", "distance_km": 0.5, "phase": "Primary"},
    ]

    with patch.object(server, "get_postcodes", return_value=mock_postcodes), \
         patch.object(server, "get_gias", return_value=mock_gias):
        result = await server._handle_find_schools_near_postcode({"postcode": "SW1A 1AA"})

    assert "1 schools" in result[0].text
    assert "Nearby School" in result[0].text
    mock_postcodes.geocode.assert_called_once_with("SW1A 1AA")


async def test_find_schools_near_postcode_no_results():
    mock_postcodes = AsyncMock()
    mock_postcodes.geocode.return_value = (51.5, -0.1)

    mock_gias = AsyncMock()
    mock_gias.find_schools_near.return_value = []

    with patch.object(server, "get_postcodes", return_value=mock_postcodes), \
         patch.object(server, "get_gias", return_value=mock_gias):
        result = await server._handle_find_schools_near_postcode({"postcode": "AB1 2CD", "radius_km": 1})

    assert "No schools found" in result[0].text


# --- compare_schools ---


async def test_compare_schools():
    school_a = _make_school(URN="100001", EstablishmentName="School A")
    school_b = _make_school(URN="100002", EstablishmentName="School B")

    mock_gias = AsyncMock()
    mock_gias.get_school_by_urn.side_effect = [school_a, school_b]

    with patch.object(server, "get_gias", return_value=mock_gias):
        result = await server._handle_compare_schools({"urns": [100001, 100002]})

    text = result[0].text
    assert "School A" in text
    assert "School B" in text
    assert "2 schools" in text


async def test_compare_schools_not_found():
    mock_gias = AsyncMock()
    mock_gias.get_school_by_urn.return_value = None

    with patch.object(server, "get_gias", return_value=mock_gias):
        result = await server._handle_compare_schools({"urns": [999999, 888888]})

    text = result[0].text
    assert "Not found" in text


# --- search_education_statistics ---


async def test_search_education_statistics():
    mock_ees = AsyncMock()
    mock_ees.search_publications_for_topic.return_value = [
        {"id": "pub-1", "title": "Pupil Absence in Schools", "summary": "Data on absence rates..."},
        {"id": "pub-2", "title": "School Workforce", "summary": "Data on teacher numbers..."},
    ]

    with patch.object(server, "get_ees", return_value=mock_ees):
        result = await server._handle_search_education_statistics({"topic": "absence"})

    text = result[0].text
    assert "2 DfE publications" in text
    assert "Pupil Absence" in text
    assert "pub-1" in text


async def test_search_education_statistics_no_results():
    mock_ees = AsyncMock()
    mock_ees.search_publications_for_topic.return_value = []

    with patch.object(server, "get_ees", return_value=mock_ees):
        result = await server._handle_search_education_statistics({"topic": "nonexistent"})

    assert "No publications found" in result[0].text


# --- get_publication_datasets ---


async def test_get_publication_datasets():
    mock_ees = AsyncMock()
    mock_ees.list_data_sets.return_value = {
        "results": [
            {
                "id": "ds-1",
                "title": "Absence rates by school",
                "summary": "Overall and persistent absence...",
                "latestVersion": {"number": "3.0", "published": "2024-03-01"},
            }
        ]
    }

    with patch.object(server, "get_ees", return_value=mock_ees):
        result = await server._handle_get_publication_datasets({"publication_id": "pub-1"})

    text = result[0].text
    assert "1 data set" in text
    assert "Absence rates by school" in text
    assert "ds-1" in text
    assert "get_dataset_metadata" in text


# --- get_dataset_metadata ---


async def test_get_dataset_metadata():
    mock_ees = AsyncMock()
    mock_ees.get_data_set_meta.return_value = {
        "filters": [
            {
                "id": "f1",
                "label": "School Type",
                "column": "school_type",
                "options": [
                    {"id": "opt-1", "label": "Academy"},
                    {"id": "opt-2", "label": "Maintained"},
                ],
            }
        ],
        "indicators": [
            {"id": "ind-1", "label": "Overall absence rate", "unit": "%"},
            {"id": "ind-2", "label": "Number of pupils", "unit": ""},
        ],
        "geographicLevels": ["NAT", "LA", "SCH"],
        "timePeriods": [
            {"code": "AY", "period": "2023"},
            {"code": "AY", "period": "2022"},
        ],
        "locations": [
            {"level": "LA", "label": "Camden", "code": "202"},
        ],
    }

    with patch.object(server, "get_ees", return_value=mock_ees):
        result = await server._handle_get_dataset_metadata({"dataset_id": "ds-1"})

    text = result[0].text
    assert "School Type" in text
    assert "Academy" in text
    assert "Overall absence rate" in text
    assert "NAT" in text
    assert "2023|AY" in text
    assert "Camden" in text
    assert "query_dataset" in text


# --- query_dataset ---


async def test_query_dataset():
    mock_ees = AsyncMock()
    mock_ees.query_data_set.return_value = {
        "results": [
            {
                "timePeriod": {"period": "2023", "code": "AY"},
                "geographicLevel": "NAT",
                "locations": {"country": {"name": "England"}},
                "filters": {},
                "values": {"ind-1": "7.4", "ind-2": "8000000"},
            }
        ],
        "paging": {"totalResults": 1, "totalPages": 1},
    }

    with patch.object(server, "get_ees", return_value=mock_ees):
        result = await server._handle_query_dataset({
            "dataset_id": "ds-1",
            "indicators": ["ind-1", "ind-2"],
            "time_periods": ["2023|AY"],
            "geographic_levels": ["NAT"],
        })

    text = result[0].text
    assert "1 of 1" in text
    assert "2023" in text
    assert "England" in text
    assert "7.4" in text


async def test_query_dataset_no_results():
    mock_ees = AsyncMock()
    mock_ees.query_data_set.return_value = {"results": [], "paging": {"totalResults": 0}}

    with patch.object(server, "get_ees", return_value=mock_ees):
        result = await server._handle_query_dataset({
            "dataset_id": "ds-1",
            "indicators": ["ind-1"],
        })

    assert "No data returned" in result[0].text


async def test_query_dataset_pagination():
    mock_ees = AsyncMock()
    mock_ees.query_data_set.return_value = {
        "results": [
            {
                "timePeriod": {"period": "2023", "code": "AY"},
                "geographicLevel": "LA",
                "locations": {"localAuthority": {"name": "Camden"}},
                "filters": {"school_type": {"label": "Academy"}},
                "values": {"ind-1": "5.2"},
            }
        ],
        "paging": {"totalResults": 150, "totalPages": 2},
    }

    with patch.object(server, "get_ees", return_value=mock_ees):
        result = await server._handle_query_dataset({
            "dataset_id": "ds-1",
            "indicators": ["ind-1"],
            "page": 1,
            "page_size": 100,
        })

    text = result[0].text
    assert "1 of 150" in text
    assert "Page 1 of 2" in text
    assert "Camden" in text
    assert "Academy" in text


# --- get_ofsted_ratings ---


async def test_get_ofsted_ratings():
    mock_ofsted = AsyncMock()
    mock_ofsted.get_inspection.return_value = {
        "urn": 109825,
        "school_name": "Test Academy",
        "overall_effectiveness": "2",
        "overall_effectiveness_text": "Good",
        "quality_of_education": "2",
        "quality_of_education_text": "Good",
        "behaviour_and_attitudes": "1",
        "behaviour_and_attitudes_text": "Outstanding",
        "personal_development": "2",
        "personal_development_text": "Good",
        "leadership_and_management": "2",
        "leadership_and_management_text": "Good",
        "inspection_type": "Section 5",
        "inspection_start_date": "2023-01-15",
        "inspection_end_date": "2023-01-16",
        "publication_date": "2023-03-01",
        "ofsted_phase": "Secondary",
        "previous_overall_effectiveness": "3",
        "previous_overall_effectiveness_text": "Requires Improvement",
        "previous_inspection_start_date": "2019-06-01",
        "number_of_previous_inspections": "4",
        "report_url": "https://reports.ofsted.gov.uk/provider/17/109825",
    }

    with patch.object(server, "get_ofsted", return_value=mock_ofsted):
        result = await server._handle_get_ofsted_ratings({"urn": 109825})

    text = result[0].text
    assert "Test Academy" in text
    assert "Good" in text
    assert "Outstanding" in text
    assert "Section 5" in text
    assert "2023-01-15" in text
    assert "Previous Inspection Grades" in text
    assert "Requires Improvement" in text


async def test_get_ofsted_ratings_not_found():
    mock_ofsted = AsyncMock()
    mock_ofsted.get_inspection.return_value = None

    with patch.object(server, "get_ofsted", return_value=mock_ofsted):
        result = await server._handle_get_ofsted_ratings({"urn": 999999})

    text = result[0].text
    assert "No Ofsted inspection data" in text
    assert "999999" in text
    assert "reports.ofsted.gov.uk" in text


# --- call_tool error handling ---


async def test_call_tool_unknown():
    result = await server.call_tool("nonexistent_tool", {})
    assert "Error" in result[0].text
    assert "Unknown tool" in result[0].text


async def test_call_tool_routes_correctly():
    mock_gias = AsyncMock()
    mock_gias.search_schools.return_value = []
    with patch.object(server, "get_gias", return_value=mock_gias):
        result = await server.call_tool("search_schools", {"query": "test"})

    assert "No schools found" in result[0].text


async def test_call_tool_handles_exception():
    mock_gias = AsyncMock()
    mock_gias.search_schools.side_effect = RuntimeError("Network error")
    with patch.object(server, "get_gias", return_value=mock_gias):
        result = await server.call_tool("search_schools", {"query": "test"})

    assert "Error calling search_schools" in result[0].text
    assert "Network error" in result[0].text


# --- OfstedClient unit tests ---


class TestOfstedClientStatic:
    def test_report_url(self):
        url = OfstedClient.ofsted_report_url(109825)
        assert url == "https://reports.ofsted.gov.uk/provider/17/109825"

    def test_format_rating_outstanding(self):
        assert OfstedClient.format_rating("1") == "Outstanding"

    def test_format_rating_good(self):
        assert OfstedClient.format_rating("2") == "Good"

    def test_format_rating_requires_improvement(self):
        assert OfstedClient.format_rating("3") == "Requires Improvement"

    def test_format_rating_inadequate(self):
        assert OfstedClient.format_rating("4") == "Inadequate"

    def test_format_rating_none(self):
        assert OfstedClient.format_rating(None) == "Not yet inspected"

    def test_format_rating_unknown(self):
        assert "Unknown" in OfstedClient.format_rating("99")

    def test_format_rating_integer(self):
        assert OfstedClient.format_rating(2) == "Good"

    def test_format_rating_with_whitespace(self):
        assert OfstedClient.format_rating(" 1 ") == "Outstanding"


# --- Format helper ---


class TestFormatSchoolSummary:
    def test_basic_format(self):
        school = {"name": "Test School", "URN": "12345", "type": "Academy", "phase": "Primary"}
        text = server._format_school_summary(school)
        assert "Test School" in text
        assert "12345" in text
        assert "Academy" in text
        assert "Primary" in text

    def test_with_distance(self):
        school = {"name": "Nearby", "URN": "12345", "distance_km": 1.5}
        text = server._format_school_summary(school)
        assert "1.5 km" in text

    def test_with_location(self):
        school = {"name": "School", "URN": "12345", "Town": "London", "Postcode": "SW1A 1AA"}
        text = server._format_school_summary(school)
        assert "London" in text
        assert "SW1A 1AA" in text
