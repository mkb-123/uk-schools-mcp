"""UK Schools MCP Server - Provides UK school data to AI assistants.

This MCP server provides tools for:
- Searching schools by name, postcode, or local authority (GIAS data)
- Getting detailed school information by URN
- Finding schools near a postcode (GIAS + Postcodes.io)
- Comparing schools side-by-side
- Browsing DfE education statistics (Explore Education Statistics API)
- Querying EES datasets with filters for absence, exclusions, performance, etc.
- Getting Ofsted inspection grades and judgements
- Links to Ofsted inspection reports

Data is sourced from official government APIs (GIAS, Ofsted, DfE).

Based on: https://github.com/modelcontextprotocol/python-sdk
"""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from uk_schools_mcp.clients.ees import EESClient
from uk_schools_mcp.clients.gias import GIASClient
from uk_schools_mcp.clients.ofsted import OfstedClient
from uk_schools_mcp.clients.postcodes import PostcodesClient

# Initialize MCP server
app = Server("uk-schools")

# Clients (created lazily)
_gias: GIASClient | None = None
_postcodes: PostcodesClient | None = None
_ees: EESClient | None = None
_ofsted: OfstedClient | None = None


def get_gias() -> GIASClient:
    global _gias
    if _gias is None:
        _gias = GIASClient()
    return _gias


def get_postcodes() -> PostcodesClient:
    global _postcodes
    if _postcodes is None:
        _postcodes = PostcodesClient()
    return _postcodes


def get_ees() -> EESClient:
    global _ees
    if _ees is None:
        _ees = EESClient()
    return _ees


def get_ofsted() -> OfstedClient:
    global _ofsted
    if _ofsted is None:
        _ofsted = OfstedClient()
    return _ofsted


def _format_school_summary(school: dict[str, Any]) -> str:
    """Format a school dict into a readable summary line."""
    parts = [f"**{school.get('name', 'Unknown')}** (URN: {school.get('URN', 'N/A')})"]
    info = []
    if school.get("type"):
        info.append(f"Type: {school['type']}")
    if school.get("phase"):
        info.append(f"Phase: {school['phase']}")
    if school.get("age_low") and school.get("age_high"):
        info.append(f"Ages: {school['age_low']}-{school['age_high']}")
    if school.get("number_of_pupils"):
        info.append(f"Pupils: {school['number_of_pupils']}")
    if school.get("Town") or school.get("Postcode"):
        addr = ", ".join(filter(None, [school.get("Town"), school.get("Postcode")]))
        info.append(f"Location: {addr}")
    if school.get("distance_km") is not None:
        info.append(f"Distance: {school['distance_km']} km")
    if school.get("website"):
        info.append(f"Web: {school['website']}")
    result = parts[0] + "\n"
    for item in info:
        result += f"  {item}\n"
    return result


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools for querying UK school data."""
    return [
        Tool(
            name="search_schools",
            description=(
                "Search for UK schools by name, postcode, or local authority. "
                "Uses live data from GIAS (Get Information About Schools). "
                "Returns a list of matching schools with name, URN, type, phase, "
                "address, and contact details."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "School name or postcode to search for",
                    },
                    "local_authority": {
                        "type": "string",
                        "description": "Local authority name (e.g., 'Milton Keynes', 'Camden')",
                    },
                    "phase": {
                        "type": "string",
                        "description": "Education phase filter (e.g., 'Primary', 'Secondary', 'Nursery')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10, max: 50)",
                        "default": 10,
                    },
                },
            },
        ),
        Tool(
            name="get_school_details",
            description=(
                "Get comprehensive details for a specific school by its URN "
                "(Unique Reference Number). Returns all GIAS data including "
                "type, phase, address, capacity, pupil numbers, head teacher, "
                "religious character, admissions policy, SEN provision, and more. "
                "Also provides links to the school's GIAS page and Ofsted reports."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "urn": {
                        "type": "integer",
                        "description": "The school's URN (Unique Reference Number)",
                    },
                },
                "required": ["urn"],
            },
        ),
        Tool(
            name="find_schools_near_postcode",
            description=(
                "Find schools within a specified distance of a UK postcode. "
                "Geocodes the postcode using Postcodes.io, then searches GIAS "
                "data for nearby schools sorted by distance. "
                "Useful for finding schools in a catchment area."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "postcode": {
                        "type": "string",
                        "description": "UK postcode (e.g., 'MK9 3BZ', 'SW1A 1AA')",
                    },
                    "radius_km": {
                        "type": "number",
                        "description": "Search radius in kilometres (default: 3, max: 10)",
                        "default": 3,
                    },
                    "phase": {
                        "type": "string",
                        "description": "Filter by phase (e.g., 'Primary', 'Secondary')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results (default: 20)",
                        "default": 20,
                    },
                },
                "required": ["postcode"],
            },
        ),
        Tool(
            name="compare_schools",
            description=(
                "Compare multiple schools side-by-side by their URNs. "
                "Shows key facts for each school including type, phase, "
                "pupil numbers, capacity, admissions policy, and Ofsted info."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "urns": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of URNs to compare (2-6 schools)",
                        "minItems": 2,
                        "maxItems": 6,
                    },
                },
                "required": ["urns"],
            },
        ),
        Tool(
            name="search_education_statistics",
            description=(
                "Search the DfE Explore Education Statistics catalogue for "
                "publications on topics like school performance, absence, "
                "exclusions, applications and offers, workforce, and more. "
                "Returns publication IDs that can be used with get_publication_datasets "
                "and then get_dataset_metadata/query_dataset to access the actual data."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": (
                            "Topic to search for, e.g. 'school absence', "
                            "'GCSE results', 'applications and offers', "
                            "'exclusions', 'school workforce'"
                        ),
                    },
                },
                "required": ["topic"],
            },
        ),
        Tool(
            name="get_publication_datasets",
            description=(
                "List the available datasets for a DfE Explore Education Statistics "
                "publication. Use after search_education_statistics to find "
                "specific data sets, then use get_dataset_metadata to explore "
                "available filters and indicators before querying."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "publication_id": {
                        "type": "string",
                        "description": "Publication ID from search_education_statistics",
                    },
                },
                "required": ["publication_id"],
            },
        ),
        Tool(
            name="get_dataset_metadata",
            description=(
                "Get the available filters, indicators, geographic levels, locations, "
                "and time periods for a DfE dataset. Use this to discover what data "
                "is available and what filter/indicator IDs to use with query_dataset. "
                "This is essential before querying - it tells you what indicators "
                "(e.g. absence rate, number of exclusions) and filters (e.g. school type, "
                "gender) are available, along with their IDs."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "Dataset ID from get_publication_datasets",
                    },
                },
                "required": ["dataset_id"],
            },
        ),
        Tool(
            name="query_dataset",
            description=(
                "Query a DfE Explore Education Statistics dataset with specific "
                "indicators and filters. Use get_dataset_metadata first to discover "
                "available indicator and filter IDs. This tool enables access to "
                "school-level data on absence, exclusions, performance, admissions, "
                "workforce, and more. "
                "Time periods use format 'YYYY|CODE' where CODE is: "
                "AY (academic year), CY (calendar year), FY (financial year), etc. "
                "Geographic levels include: NAT (national), REG (regional), "
                "LA (local authority), SCH (school). "
                "Locations use format 'LEVEL|id_type|id_value' e.g. 'LA|code|823'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_id": {
                        "type": "string",
                        "description": "Dataset ID from get_publication_datasets",
                    },
                    "indicators": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of indicator IDs to retrieve (from get_dataset_metadata)",
                    },
                    "time_periods": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Time periods in 'YYYY|CODE' format, e.g. ['2023|AY']",
                    },
                    "geographic_levels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Geographic levels: NAT, REG, LA, SCH, etc.",
                    },
                    "locations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Locations in 'LEVEL|id_type|id_value' format",
                    },
                    "filters": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter option IDs (from get_dataset_metadata)",
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number (default: 1)",
                        "default": 1,
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Results per page (default: 100, max: 1000)",
                        "default": 100,
                    },
                },
                "required": ["dataset_id", "indicators"],
            },
        ),
        Tool(
            name="get_ofsted_ratings",
            description=(
                "Get Ofsted inspection ratings and grades for a school by URN. "
                "Returns the overall effectiveness grade (Outstanding/Good/"
                "Requires Improvement/Inadequate) along with grades for each "
                "inspection area: Quality of Education, Behaviour and Attitudes, "
                "Personal Development, Leadership and Management, and where "
                "applicable Early Years and Sixth Form provision. "
                "Also includes inspection dates, type, and previous grades. "
                "Data comes from Ofsted Management Information files published monthly."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "urn": {
                        "type": "integer",
                        "description": "The school's URN (Unique Reference Number)",
                    },
                },
                "required": ["urn"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls from the MCP client."""
    try:
        if name == "search_schools":
            return await _handle_search_schools(arguments)
        elif name == "get_school_details":
            return await _handle_get_school_details(arguments)
        elif name == "find_schools_near_postcode":
            return await _handle_find_schools_near_postcode(arguments)
        elif name == "compare_schools":
            return await _handle_compare_schools(arguments)
        elif name == "search_education_statistics":
            return await _handle_search_education_statistics(arguments)
        elif name == "get_publication_datasets":
            return await _handle_get_publication_datasets(arguments)
        elif name == "get_dataset_metadata":
            return await _handle_get_dataset_metadata(arguments)
        elif name == "query_dataset":
            return await _handle_query_dataset(arguments)
        elif name == "get_ofsted_ratings":
            return await _handle_get_ofsted_ratings(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        error_msg = f"Error calling {name}: {str(e)}"
        return [TextContent(type="text", text=error_msg)]


async def _handle_search_schools(arguments: Any) -> list[TextContent]:
    query = arguments.get("query")
    local_authority = arguments.get("local_authority")
    phase = arguments.get("phase")
    limit = min(arguments.get("limit", 10), 50)

    gias = get_gias()
    schools = await gias.search_schools(
        query=query,
        local_authority=local_authority,
        phase=phase,
        limit=limit,
    )

    if not schools:
        return [TextContent(type="text", text="No schools found matching your search criteria.")]

    result = f"Found {len(schools)} schools"
    if local_authority:
        result += f" in {local_authority}"
    if query:
        result += f" matching '{query}'"
    result += ":\n\n"

    for school in schools:
        result += _format_school_summary(school) + "\n"

    result += "\nUse get_school_details with a URN for full information."
    return [TextContent(type="text", text=result)]


async def _handle_get_school_details(arguments: Any) -> list[TextContent]:
    urn = arguments["urn"]
    gias = get_gias()
    school = await gias.get_school_by_urn(urn)

    if school is None:
        return [TextContent(type="text", text=f"No school found with URN {urn}.")]

    name = school.get("EstablishmentName", "Unknown")
    result = f"# {name} (URN: {urn})\n\n"

    # Core info
    sections = {
        "Type": "TypeOfEstablishment (name)",
        "Status": "EstablishmentStatus (name)",
        "Phase": "PhaseOfEducation (name)",
        "Age Range": None,
        "Gender": "Gender (name)",
        "Religious Character": "ReligiousCharacter (name)",
        "Admissions Policy": "AdmissionsPolicy (name)",
        "Capacity": "SchoolCapacity",
        "Number of Pupils": "NumberOfPupils",
        "FSM Eligible": "PercentageFSM",
    }

    for label, key in sections.items():
        if label == "Age Range":
            low = school.get("StatutoryLowAge")
            high = school.get("StatutoryHighAge")
            if low and high:
                result += f"**{label}:** {low} - {high}\n"
        elif key and school.get(key):
            val = school[key]
            if label == "FSM Eligible":
                val = f"{val}%"
            result += f"**{label}:** {val}\n"

    # Address
    addr_parts = [school.get(f) for f in ["Street", "Locality", "Address3", "Town", "County (name)", "Postcode"]]
    addr = ", ".join(filter(None, addr_parts))
    if addr:
        result += f"\n**Address:** {addr}\n"

    # Contact
    if school.get("TelephoneNum"):
        result += f"**Phone:** {school['TelephoneNum']}\n"
    if school.get("SchoolWebsite"):
        result += f"**Website:** {school['SchoolWebsite']}\n"

    # Head teacher
    head_parts = [school.get("HeadTitle (name)"), school.get("HeadFirstName"), school.get("HeadLastName")]
    head = " ".join(filter(None, head_parts))
    if head:
        title = school.get("HeadPreferredJobTitle", "Head Teacher")
        result += f"**{title}:** {head}\n"

    # Local authority
    if school.get("LA (name)"):
        result += f"**Local Authority:** {school['LA (name)']}\n"

    # Ofsted
    if school.get("OfstedLastInsp"):
        result += f"\n**Last Ofsted Inspection:** {school['OfstedLastInsp']}\n"
    result += f"**Ofsted Reports:** {OfstedClient.ofsted_report_url(urn)}\n"

    # Trust info
    if school.get("Trusts (name)"):
        result += f"**Trust:** {school['Trusts (name)']}\n"

    # SEN
    sen_fields = [k for k in school if k.startswith("SEN") and school[k]]
    if sen_fields:
        result += f"\n**SEN Provision:** {len(sen_fields)} type(s) recorded\n"

    # Links
    result += f"\n**GIAS Page:** {school.get('gias_url', '')}\n"

    result += "\nUse get_ofsted_ratings for detailed inspection grades."
    return [TextContent(type="text", text=result)]


async def _handle_find_schools_near_postcode(arguments: Any) -> list[TextContent]:
    postcode = arguments["postcode"]
    radius_km = min(arguments.get("radius_km", 3), 10)
    phase = arguments.get("phase")
    limit = min(arguments.get("limit", 20), 50)

    postcodes = get_postcodes()
    lat, lng = await postcodes.geocode(postcode)

    gias = get_gias()
    schools = await gias.find_schools_near(
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        phase=phase,
        limit=limit,
    )

    if not schools:
        return [TextContent(type="text", text=f"No schools found within {radius_km}km of {postcode}.")]

    result = f"Found {len(schools)} schools within {radius_km}km of {postcode}:\n\n"
    for school in schools:
        result += _format_school_summary(school) + "\n"

    result += "\nUse get_school_details with a URN for full information."
    return [TextContent(type="text", text=result)]


async def _handle_compare_schools(arguments: Any) -> list[TextContent]:
    urns = arguments["urns"]
    gias = get_gias()

    result = f"# School Comparison ({len(urns)} schools)\n\n"

    for urn in urns:
        school = await gias.get_school_by_urn(urn)
        if school is None:
            result += f"## URN {urn} - Not found\n\n"
            continue

        name = school.get("EstablishmentName", "Unknown")
        result += f"## {name} (URN: {urn})\n"
        result += f"- **Type:** {school.get('TypeOfEstablishment (name)', 'N/A')}\n"
        result += f"- **Phase:** {school.get('PhaseOfEducation (name)', 'N/A')}\n"

        low = school.get("StatutoryLowAge")
        high = school.get("StatutoryHighAge")
        if low and high:
            result += f"- **Age Range:** {low}-{high}\n"

        if school.get("NumberOfPupils"):
            cap = school.get("SchoolCapacity", "N/A")
            result += f"- **Pupils:** {school['NumberOfPupils']} (capacity: {cap})\n"

        if school.get("AdmissionsPolicy (name)"):
            result += f"- **Admissions:** {school['AdmissionsPolicy (name)']}\n"
        if school.get("ReligiousCharacter (name)"):
            result += f"- **Religious Character:** {school['ReligiousCharacter (name)']}\n"
        if school.get("Gender (name)"):
            result += f"- **Gender:** {school['Gender (name)']}\n"
        if school.get("PercentageFSM"):
            result += f"- **FSM:** {school['PercentageFSM']}%\n"

        addr_parts = [school.get("Town"), school.get("Postcode")]
        addr = ", ".join(filter(None, addr_parts))
        if addr:
            result += f"- **Location:** {addr}\n"

        if school.get("OfstedLastInsp"):
            result += f"- **Last Ofsted:** {school['OfstedLastInsp']}\n"
        result += f"- **Ofsted Reports:** {OfstedClient.ofsted_report_url(urn)}\n"
        result += "\n"

    return [TextContent(type="text", text=result)]


async def _handle_search_education_statistics(arguments: Any) -> list[TextContent]:
    topic = arguments["topic"]
    ees = get_ees()
    publications = await ees.search_publications_for_topic(topic)

    if not publications:
        return [TextContent(type="text", text=f"No publications found for topic '{topic}'.")]

    result = f"Found {len(publications)} DfE publications for '{topic}':\n\n"
    for pub in publications:
        result += f"**{pub['title']}**\n"
        result += f"  ID: `{pub['id']}`\n"
        if pub.get("summary"):
            summary = pub["summary"][:200]
            result += f"  {summary}\n"
        result += "\n"

    result += "Use get_publication_datasets with a publication ID to see available data sets."
    return [TextContent(type="text", text=result)]


async def _handle_get_publication_datasets(arguments: Any) -> list[TextContent]:
    publication_id = arguments["publication_id"]
    ees = get_ees()
    data = await ees.list_data_sets(publication_id)

    datasets = data.get("results", [])
    if not datasets:
        return [TextContent(type="text", text=f"No data sets found for publication {publication_id}.")]

    result = f"Found {len(datasets)} data set(s):\n\n"
    for ds in datasets:
        result += f"**{ds.get('title', 'Untitled')}**\n"
        result += f"  ID: `{ds.get('id')}`\n"
        if ds.get("summary"):
            result += f"  {ds['summary'][:200]}\n"
        if ds.get("latestVersion"):
            ver = ds["latestVersion"]
            result += f"  Version: {ver.get('number', 'N/A')}, Published: {ver.get('published', 'N/A')}\n"
        result += "\n"

    result += "Use get_dataset_metadata with a dataset ID to see available filters and indicators."
    return [TextContent(type="text", text=result)]


async def _handle_get_dataset_metadata(arguments: Any) -> list[TextContent]:
    dataset_id = arguments["dataset_id"]
    ees = get_ees()
    meta = await ees.get_data_set_meta(dataset_id)

    result = f"# Dataset Metadata: `{dataset_id}`\n\n"

    # Filters
    filters = meta.get("filters", [])
    if filters:
        result += f"## Filters ({len(filters)})\n\n"
        for f in filters:
            result += f"**{f.get('label', f.get('id', 'Unknown'))}** (column: `{f.get('column', 'N/A')}`)\n"
            options = f.get("options", [])
            if options:
                # Show up to 20 options
                shown = options[:20]
                for opt in shown:
                    result += f"  - `{opt.get('id', '')}`: {opt.get('label', 'N/A')}\n"
                if len(options) > 20:
                    result += f"  - ... and {len(options) - 20} more options\n"
            result += "\n"

    # Indicators
    indicators = meta.get("indicators", [])
    if indicators:
        result += f"## Indicators ({len(indicators)})\n\n"
        for ind in indicators:
            unit = ind.get("unit", "")
            unit_str = f" ({unit})" if unit else ""
            result += f"- `{ind.get('id', '')}`: {ind.get('label', 'N/A')}{unit_str}\n"
        result += "\n"

    # Geographic levels
    geo_levels = meta.get("geographicLevels", [])
    if geo_levels:
        result += "## Geographic Levels\n\n"
        for gl in geo_levels:
            result += f"- {gl}\n"
        result += "\n"

    # Time periods
    time_periods = meta.get("timePeriods", [])
    if time_periods:
        result += f"## Time Periods ({len(time_periods)})\n\n"
        shown = time_periods[:20]
        for tp in shown:
            code = tp.get("code", "")
            period = tp.get("period", "")
            result += f"- `{period}|{code}`\n"
        if len(time_periods) > 20:
            result += f"- ... and {len(time_periods) - 20} more periods\n"
        result += "\n"

    # Locations
    locations = meta.get("locations", [])
    if locations:
        result += f"## Locations ({len(locations)})\n\n"
        shown = locations[:30]
        for loc in shown:
            level = loc.get("level", "")
            label = loc.get("label", "N/A")
            loc_id = loc.get("id", loc.get("code", ""))
            result += f"- `{level}|id|{loc_id}`: {label}\n"
        if len(locations) > 30:
            result += f"- ... and {len(locations) - 30} more locations\n"
        result += "\n"

    result += "Use query_dataset with indicator IDs and optional filters/time_periods to retrieve data."
    return [TextContent(type="text", text=result)]


async def _handle_query_dataset(arguments: Any) -> list[TextContent]:
    dataset_id = arguments["dataset_id"]
    indicators = arguments["indicators"]
    time_periods = arguments.get("time_periods")
    geographic_levels = arguments.get("geographic_levels")
    locations = arguments.get("locations")
    filters = arguments.get("filters")
    page = arguments.get("page", 1)
    page_size = min(arguments.get("page_size", 100), 1000)

    ees = get_ees()
    data = await ees.query_data_set(
        data_set_id=dataset_id,
        indicators=indicators,
        time_periods=time_periods,
        geographic_levels=geographic_levels,
        locations=locations,
        filters=filters,
        page=page,
        page_size=page_size,
    )

    results = data.get("results", [])
    paging = data.get("paging", {})
    total = paging.get("totalResults", len(results))

    if not results:
        return [TextContent(type="text", text="No data returned for this query. Try broadening your filters.")]

    result = f"# Query Results (showing {len(results)} of {total} total)\n\n"

    for row in results:
        # Build a readable representation of each data row
        time_period = row.get("timePeriod", {})
        period_str = f"{time_period.get('period', 'N/A')} ({time_period.get('code', '')})"

        geo = row.get("geographicLevel", "")
        location_info = ""
        for loc_key in ["school", "localAuthority", "region", "country"]:
            loc = row.get("locations", {}).get(loc_key)
            if loc:
                location_info = loc.get("name", loc.get("label", str(loc)))
                break

        result += f"**{period_str}** | {geo}"
        if location_info:
            result += f" | {location_info}"
        result += "\n"

        # Show filter values
        filter_items = row.get("filters", {})
        if filter_items:
            filter_strs = []
            for fk, fv in filter_items.items():
                if isinstance(fv, dict):
                    filter_strs.append(f"{fk}: {fv.get('label', fv.get('id', str(fv)))}")
                else:
                    filter_strs.append(f"{fk}: {fv}")
            if filter_strs:
                result += f"  Filters: {', '.join(filter_strs)}\n"

        # Show indicator values
        values = row.get("values", {})
        if values:
            for ind_id, val in values.items():
                result += f"  {ind_id}: {val}\n"
        result += "\n"

    # Pagination info
    if total > len(results):
        total_pages = paging.get("totalPages", 1)
        result += f"Page {page} of {total_pages}. Use page parameter to see more results.\n"

    return [TextContent(type="text", text=result)]


async def _handle_get_ofsted_ratings(arguments: Any) -> list[TextContent]:
    urn = arguments["urn"]
    ofsted = get_ofsted()
    inspection = await ofsted.get_inspection(urn)

    if inspection is None:
        return [TextContent(
            type="text",
            text=(
                f"No Ofsted inspection data found for URN {urn}.\n"
                f"This could mean the school hasn't been inspected yet, "
                f"or it may not be in the Ofsted MI dataset (e.g. independent schools).\n"
                f"Check the Ofsted report page: {OfstedClient.ofsted_report_url(urn)}"
            ),
        )]

    school_name = inspection.get("school_name", f"URN {urn}")
    result = f"# Ofsted Inspection: {school_name}\n\n"

    # Current grades
    result += "## Current Grades\n\n"
    grade_display = [
        ("overall_effectiveness", "Overall Effectiveness"),
        ("quality_of_education", "Quality of Education"),
        ("behaviour_and_attitudes", "Behaviour and Attitudes"),
        ("personal_development", "Personal Development"),
        ("leadership_and_management", "Leadership and Management"),
        ("early_years_provision", "Early Years Provision"),
        ("sixth_form_provision", "Sixth Form Provision"),
    ]

    for field, label in grade_display:
        text_val = inspection.get(f"{field}_text")
        if text_val:
            code = inspection.get(field, "")
            result += f"**{label}:** {text_val} ({code})\n"

    # Inspection details
    result += "\n## Inspection Details\n\n"
    if inspection.get("inspection_type"):
        result += f"**Type:** {inspection['inspection_type']}\n"
    if inspection.get("inspection_start_date"):
        end = inspection.get("inspection_end_date", "")
        date_str = inspection["inspection_start_date"]
        if end and end != date_str:
            date_str += f" to {end}"
        result += f"**Date:** {date_str}\n"
    if inspection.get("publication_date"):
        result += f"**Published:** {inspection['publication_date']}\n"
    if inspection.get("ofsted_phase"):
        result += f"**Ofsted Phase:** {inspection['ofsted_phase']}\n"
    if inspection.get("category_of_concern"):
        result += f"**Category of Concern:** {inspection['category_of_concern']}\n"

    # Previous grades
    has_previous = any(
        inspection.get(f"previous_{f}_text")
        for f in ["overall_effectiveness", "quality_of_education", "behaviour_and_attitudes",
                   "personal_development", "leadership_and_management"]
    )
    if has_previous:
        result += "\n## Previous Inspection Grades\n\n"
        prev_display = [
            ("previous_overall_effectiveness", "Overall Effectiveness"),
            ("previous_quality_of_education", "Quality of Education"),
            ("previous_behaviour_and_attitudes", "Behaviour and Attitudes"),
            ("previous_personal_development", "Personal Development"),
            ("previous_leadership_and_management", "Leadership and Management"),
        ]
        for field, label in prev_display:
            text_val = inspection.get(f"{field}_text")
            if text_val:
                code = inspection.get(field, "")
                result += f"**{label}:** {text_val} ({code})\n"

        if inspection.get("previous_inspection_start_date"):
            result += f"**Previous Inspection Date:** {inspection['previous_inspection_start_date']}\n"
        if inspection.get("number_of_previous_inspections"):
            result += f"**Number of Previous Inspections:** {inspection['number_of_previous_inspections']}\n"

    # Links
    result += f"\n**Full Report:** {inspection.get('report_url', OfstedClient.ofsted_report_url(urn))}\n"

    return [TextContent(type="text", text=result)]


async def main():
    """Run the MCP server using stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
