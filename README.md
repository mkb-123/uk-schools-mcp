# UK Schools MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that provides AI assistants with access to comprehensive UK school data from official government sources.

## Features

- Search schools by name, postcode, or local authority (GIAS bulk data)
- Get detailed school information (type, phase, age range, capacity, contact details)
- Find schools near a postcode with distance sorting (Postcodes.io geocoding)
- Compare schools side-by-side
- Browse DfE education statistics (performance, absence, exclusions, admissions)
- Query DfE datasets with filters for school-level absence, exclusions, workforce, and performance data
- Get Ofsted inspection grades and judgements from Management Information data
- Links to Ofsted inspection reports

## Data Sources

| Source | Type | Auth | What it provides |
|--------|------|------|-----------------|
| [GIAS](https://get-information-schools.service.gov.uk/) | Bulk CSV (daily) | None | All ~65k schools: name, URN, type, phase, address, capacity, pupils, head teacher, SEN, etc. |
| [Postcodes.io](https://postcodes.io/) | REST JSON API | None | UK postcode geocoding (lat/lng) for catchment area searches |
| [Explore Education Statistics](https://explore-education-statistics.service.gov.uk/) | REST JSON API | None | DfE publications: performance tables, absence, exclusions, applications & offers, workforce |
| [Ofsted](https://reports.ofsted.gov.uk/) | Monthly Excel + report links | None | Inspection grades, judgement areas, dates, and report URLs |

## Installation

### Using uv (recommended)

```bash
git clone https://github.com/yourusername/uk-schools-mcp.git
cd uk-schools-mcp
uv sync --all-extras
uv run python -m uk_schools_mcp.server
```

### Using pip

```bash
pip install mcp httpx polars pydantic openpyxl
```

## Usage with Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "uk-schools": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/uk-schools-mcp",
        "run",
        "python",
        "-m",
        "uk_schools_mcp.server"
      ]
    }
  }
}
```

## Available Tools

### `search_schools`
Search for UK schools by name, postcode, or local authority using GIAS data.

**Example:** "Find primary schools in Milton Keynes"

### `get_school_details`
Get comprehensive details for a specific school by URN, including links to Ofsted reports and the GIAS page.

**Example:** "Show me details for URN 109825"

### `find_schools_near_postcode`
Find schools within a radius of a UK postcode, sorted by distance. Uses Postcodes.io for geocoding and GIAS data for school locations.

**Example:** "Find all primary schools within 2km of MK9 3BZ"

### `compare_schools`
Compare multiple schools side-by-side by URN.

**Example:** "Compare schools with URNs 109825, 110234, and 110567"

### `search_education_statistics`
Search the DfE Explore Education Statistics catalogue for publications on school performance, absence, exclusions, applications & offers, workforce, etc.

**Example:** "Search for publications about school absence"

### `get_publication_datasets`
List available datasets for a DfE publication (use after `search_education_statistics`).

### `get_dataset_metadata`
Get available filters, indicators, geographic levels, and time periods for a DfE dataset. Essential before querying to discover what data is available and what IDs to use.

**Example:** "What filters and indicators are available for dataset ds-123?"

### `query_dataset`
Query a DfE Explore Education Statistics dataset with specific indicators, filters, time periods, and geographic levels. Enables access to school-level data on absence, exclusions, performance, admissions, workforce, and more.

**Example:** "Query the absence dataset for 2023 academic year at national level"

### `get_ofsted_ratings`
Get Ofsted inspection ratings and grades for a school by URN. Returns overall effectiveness grade and grades for each inspection area (Quality of Education, Behaviour and Attitudes, Personal Development, Leadership and Management), plus inspection dates, type, and previous grades.

**Example:** "Get Ofsted ratings for URN 109825"

## Development

### Setup

```bash
git clone https://github.com/yourusername/uk-schools-mcp.git
cd uk-schools-mcp
uv sync --all-extras
uv run pytest
uv run ruff check src/ tests/
```

### Project Structure

```
uk-schools-mcp/
├── src/
│   └── uk_schools_mcp/
│       ├── server.py           # MCP server + tool handlers
│       └── clients/
│           ├── gias.py         # GIAS bulk CSV client
│           ├── postcodes.py    # Postcodes.io geocoding client
│           ├── ees.py          # Explore Education Statistics API client
│           └── ofsted.py       # Ofsted report URL helper
├── tests/
│   └── test_server.py
├── NEXT_STEPS.md               # Roadmap for additional data sources
└── pyproject.toml
```

### How GIAS Data Works

On first use, the server downloads the daily GIAS bulk CSV (~65k schools, ~30MB) from:
```
https://ea-edubase-api-prod.azurewebsites.net/edubase/downloads/public/edubasealldata{YYYYMMDD}.csv
```

The CSV is cached locally at `~/.cache/uk-schools-mcp/` and refreshed daily. All search and lookup operations run against this cached data using polars for fast filtering.

## Contributing

Contributions welcome! See [NEXT_STEPS.md](NEXT_STEPS.md) for planned enhancements.

## License

MIT License - See LICENSE file for details.

## Acknowledgments

Built with data from:
- Department for Education (DfE) - GIAS and Explore Education Statistics
- Office for Standards in Education (Ofsted) - Inspection reports
- [Postcodes.io](https://postcodes.io/) - Open-source UK postcode geocoding
