"""
UK Schools MCP Server - Starter Template

This is a starter template for building an MCP server that provides access to
UK school data from GIAS, Ofsted, and DfE APIs.

Based on: https://github.com/modelcontextprotocol/python-sdk
"""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Optional: Import your school-finder logic
# You can either:
# 1. Make HTTP requests to your deployed school-finder API
# 2. Import and reuse your existing Python modules
# 3. Create new API clients for GIAS/Ofsted/DfE

import httpx


# Initialize MCP server
app = Server("uk-schools")


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
                "required": ["query"],
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
                    "urn": {
                        "type": "string",
                        "description": "Unique Reference Number (URN) of the school",
                    },
                    "school_name": {
                        "type": "string",
                        "description": "Exact name of the school (alternative to URN)",
                    },
                },
            },
        ),
        Tool(
            name="get_ofsted_rating",
            description=(
                "Get current Ofsted rating and inspection history for a school. "
                "Includes rating trajectory (improving/stable/declining), inspection dates, "
                "key findings, and links to full reports."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "urn": {"type": "string", "description": "School URN"},
                },
                "required": ["urn"],
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
                    "urns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of school URNs to compare (2-4 schools)",
                        "minItems": 2,
                        "maxItems": 4,
                    },
                },
                "required": ["urns"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls from the MCP client."""

    if name == "search_schools":
        # Example: Call your school-finder API or GIAS API
        query = arguments.get("query")
        council = arguments.get("council")
        limit = arguments.get("limit", 10)

        # Option 1: Call your deployed school-finder API
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(
        #         "https://school-finder.fly.dev/api/schools",
        #         params={"council": council, "search": query, "limit": limit}
        #     )
        #     schools = response.json()

        # Option 2: Call GIAS API directly
        # schools = await fetch_gias_schools(query, council)

        # For now, return example data
        result = f"Searching for schools matching '{query}' in {council or 'all councils'}..."
        result += f"\n\nFound {limit} schools (example data - connect to real API)"

        return [TextContent(type="text", text=result)]

    elif name == "get_school_details":
        urn = arguments.get("urn")
        school_name = arguments.get("school_name")

        # Fetch school details from your API or GIAS
        result = f"Fetching details for school URN: {urn or school_name}..."
        result += "\n\n(Connect to school-finder API or GIAS API)"

        return [TextContent(type="text", text=result)]

    elif name == "get_ofsted_rating":
        urn = arguments["urn"]

        # Fetch Ofsted data
        result = f"Fetching Ofsted rating for URN: {urn}..."
        result += "\n\n(Connect to Ofsted API or your school-finder API)"

        return [TextContent(type="text", text=result)]

    elif name == "find_schools_in_catchment":
        postcode = arguments["postcode"]
        radius_km = arguments.get("radius_km", 3)

        # Geocode postcode and find nearby schools
        result = f"Finding schools within {radius_km}km of {postcode}..."
        result += "\n\n(Implement postcodes.io geocoding + distance search)"

        return [TextContent(type="text", text=result)]

    elif name == "compare_schools":
        urns = arguments["urns"]

        result = f"Comparing {len(urns)} schools: {', '.join(urns)}..."
        result += "\n\n(Fetch and format comparison data)"

        return [TextContent(type="text", text=result)]

    else:
        raise ValueError(f"Unknown tool: {name}")


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
