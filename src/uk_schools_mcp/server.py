"""UK Schools MCP Server - Provides UK school data to AI assistants.

This MCP server provides tools for:
- Searching schools
- Getting school details
- Finding schools in catchment areas
- Comparing schools
- Getting Ofsted ratings

Data is sourced from official government APIs (GIAS, Ofsted, DfE).

Based on: https://github.com/modelcontextprotocol/python-sdk
"""

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


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
    try:
        if name == "search_schools":
            return [TextContent(
                type="text",
                text="search_schools is not yet connected to a data source. "
                     "Configure a GIAS or DfE API client to enable this tool.",
            )]

        elif name == "get_school_details":
            return [TextContent(
                type="text",
                text="get_school_details is not yet connected to a data source. "
                     "Configure a GIAS or DfE API client to enable this tool.",
            )]

        elif name == "find_schools_in_catchment":
            return [TextContent(
                type="text",
                text="find_schools_in_catchment is not yet connected to a data source. "
                     "Configure a GIAS or DfE API client to enable this tool.",
            )]

        elif name == "compare_schools":
            return [TextContent(
                type="text",
                text="compare_schools is not yet connected to a data source. "
                     "Configure a GIAS or DfE API client to enable this tool.",
            )]

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
