"""UK Schools MCP Server - Provides UK school data to AI assistants.

This MCP server connects to the school-finder API and provides tools for:
- Searching schools
- Getting school details
- Finding schools in catchment areas
- Comparing schools
- Getting Ofsted ratings

Based on: https://github.com/modelcontextprotocol/python-sdk
"""

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from uk_schools_mcp.clients.school_finder import SchoolFinderClient


# Initialize MCP server
app = Server("uk-schools")

# Initialize API client (will be created on first use)
_client: SchoolFinderClient | None = None


def get_client() -> SchoolFinderClient:
    """Get or create the SchoolFinderClient instance."""
    global _client
    if _client is None:
        _client = SchoolFinderClient()
    return _client


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools for querying UK school data."""
    return [
        Tool(
            name="search_schools",
            description=(
                "Search for UK schools by name, postcode, or local authority. "
                "Returns a list of matching schools with basic information including "
                "name, address, type, phase, Ofsted rating, and contact details."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "School name, postcode, or search term",
                    },
                    "council": {
                        "type": "string",
                        "description": "Local authority name (e.g., 'Milton Keynes')",
                    },
                    "school_type": {
                        "type": "string",
                        "enum": [
                            "state_primary",
                            "state_secondary",
                            "academy",
                            "private",
                            "nursery",
                        ],
                        "description": "Filter by school type",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 10)",
                        "default": 10,
                    },
                },
            },
        ),
        Tool(
            name="get_school_details",
            description=(
                "Get comprehensive details for a specific school including "
                "Ofsted rating, performance data, clubs, term dates, admissions "
                "criteria, catchment area, and contact information."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "school_id": {
                        "type": "integer",
                        "description": "Database ID of the school",
                    },
                },
                "required": ["school_id"],
            },
        ),
        Tool(
            name="find_schools_in_catchment",
            description=(
                "Find schools within a specified distance of a postcode. "
                "Useful for finding schools in catchment area for a home address. "
                "Returns schools sorted by distance."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "postcode": {
                        "type": "string",
                        "description": "UK postcode (e.g., 'MK9 3BZ')",
                    },
                    "radius_km": {
                        "type": "number",
                        "description": "Search radius in kilometres (default: 3)",
                        "default": 3,
                    },
                    "school_type": {
                        "type": "string",
                        "description": "Filter by school type",
                    },
                },
                "required": ["postcode"],
            },
        ),
        Tool(
            name="compare_schools",
            description=(
                "Compare multiple schools side-by-side showing Ofsted ratings, "
                "performance data, admissions statistics, clubs, and facilities."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "school_ids": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "List of school IDs to compare (2-4 schools)",
                        "minItems": 2,
                        "maxItems": 4,
                    },
                },
                "required": ["school_ids"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls from the MCP client."""
    client = get_client()

    try:
        if name == "search_schools":
            query = arguments.get("query")
            council = arguments.get("council")
            school_type = arguments.get("school_type")
            limit = arguments.get("limit", 10)

            schools = await client.search_schools(
                query=query,
                council=council,
                school_type=school_type,
                limit=limit,
            )

            result = f"Found {len(schools)} schools"
            if council:
                result += f" in {council}"
            if query:
                result += f" matching '{query}'"
            result += ":\n\n"

            for school in schools:
                result += f"**{school['name']}** (ID: {school['id']})\n"
                result += f"  Type: {school.get('type', 'N/A')}\n"
                result += f"  Ofsted: {school.get('ofsted_rating', 'Not rated')}\n"
                result += f"  Address: {school.get('address', 'N/A')}\n"
                if school.get('distance_km'):
                    result += f"  Distance: {school['distance_km']:.1f} km\n"
                if school.get('website'):
                    result += f"  Website: {school['website']}\n"
                result += "\n"

            return [TextContent(type="text", text=result)]

        elif name == "get_school_details":
            school_id = arguments["school_id"]
            school = await client.get_school_by_id(school_id)

            result = f"# {school['name']}\n\n"
            result += f"**Type:** {school.get('type', 'N/A')}\n"
            result += f"**Ofsted Rating:** {school.get('ofsted_rating', 'Not rated')}\n"
            result += f"**Phase:** {school.get('phase', 'N/A')}\n"
            result += f"**Age Range:** {school.get('age_range_from', 'N/A')} - {school.get('age_range_to', 'N/A')}\n"
            result += f"**Address:** {school.get('address', 'N/A')}, {school.get('postcode', 'N/A')}\n\n"

            if school.get('ethos'):
                result += f"**Ethos:** {school['ethos']}\n\n"

            if school.get('clubs'):
                result += f"**Clubs:** {len(school['clubs'])} available\n"
                for club in school['clubs'][:5]:  # Show first 5
                    result += f"  - {club['name']} ({club['club_type']})\n"

            if school.get('website'):
                result += f"\n**Website:** {school['website']}\n"

            return [TextContent(type="text", text=result)]

        elif name == "find_schools_in_catchment":
            postcode = arguments["postcode"]
            radius_km = arguments.get("radius_km", 3)
            school_type = arguments.get("school_type")

            # First geocode the postcode
            location = await client.geocode_postcode(postcode)
            lat, lng = location['latitude'], location['longitude']

            # Find schools in catchment
            schools = await client.find_schools_in_catchment(
                lat=lat,
                lng=lng,
                radius_km=radius_km,
                school_type=school_type,
            )

            result = f"Found {len(schools)} schools within {radius_km}km of {postcode}:\n\n"

            for school in schools[:15]:  # Show top 15
                result += f"**{school['name']}** ({school['distance_km']:.1f} km)\n"
                result += f"  Ofsted: {school.get('ofsted_rating', 'Not rated')}\n"
                result += f"  Type: {school.get('type', 'N/A')}\n"
                result += f"  ID: {school['id']}\n\n"

            return [TextContent(type="text", text=result)]

        elif name == "compare_schools":
            school_ids = arguments["school_ids"]
            comparison = await client.compare_schools(school_ids)

            result = f"# School Comparison ({len(comparison['schools'])} schools)\n\n"

            for school in comparison['schools']:
                result += f"## {school['name']}\n"
                result += f"- **Ofsted:** {school.get('ofsted_rating', 'N/A')}\n"
                result += f"- **Type:** {school.get('type', 'N/A')}\n"
                result += f"- **Address:** {school.get('address', 'N/A')}\n"
                if school.get('clubs'):
                    result += f"- **Clubs:** {len(school['clubs'])}\n"
                result += "\n"

            return [TextContent(type="text", text=result)]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        error_msg = f"Error calling {name}: {str(e)}"
        return [TextContent(type="text", text=error_msg)]


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
