# UK Schools MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) server that provides AI assistants with access to comprehensive UK school data from official government sources.

## Features

🏫 **Comprehensive School Data**
- Search schools by name, postcode, or local authority
- Get detailed school information (type, phase, age range, contact details)
- Access Ofsted ratings and inspection history
- View academic performance data (SATs, GCSEs, Progress 8)
- Find schools within catchment areas

📊 **Official Data Sources**
- [Get Information About Schools (GIAS)](https://www.get-information-schools.service.gov.uk/)
- [Ofsted Data View](https://www.gov.uk/government/statistical-data-sets/ofsted-inspection-data)
- [Explore Education Statistics API](https://explore-education-statistics.service.gov.uk/)

## Installation

### Using uv (recommended)

```bash
# Create new repo
mkdir uk-schools-mcp && cd uk-schools-mcp
git init

# Initialize Python project
uv init
uv add mcp httpx polars pydantic

# Copy server code
# (Add your server.py here)

# Run the server
uv run python -m uk_schools_mcp.server
```

### Using pip

```bash
pip install mcp httpx polars pydantic
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

Restart Claude Desktop, and you'll see the UK Schools server available in the MCP menu (🔌 icon).

## Available Tools

### `search_schools`
Search for schools by name, postcode, or local authority.

**Example:**
> "Find primary schools in Milton Keynes"

### `get_school_details`
Get comprehensive details for a specific school including Ofsted rating, performance data, clubs, and admissions criteria.

**Example:**
> "Show me details for Knowles Nursery School (URN: 109825)"

### `get_ofsted_rating`
Get current Ofsted rating and inspection history with trajectory analysis.

**Example:**
> "What's the Ofsted rating for URN 109825?"

### `find_schools_in_catchment`
Find schools within a specified distance of a postcode.

**Example:**
> "Find all primary schools within 2km of MK9 3BZ"

### `compare_schools`
Compare multiple schools side-by-side.

**Example:**
> "Compare schools with URNs 109825, 110234, and 110567"

## Development

### Setup

```bash
# Clone repo
git clone https://github.com/yourusername/uk-schools-mcp.git
cd uk-schools-mcp

# Install dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Lint
uv run ruff check src/ tests/
```

### Project Structure

```
uk-schools-mcp/
├── src/
│   └── uk_schools_mcp/
│       ├── server.py        # Main MCP server
│       ├── tools.py         # Tool definitions
│       └── clients/
│           ├── gias.py      # GIAS API client
│           ├── ofsted.py    # Ofsted API client
│           └── dfe.py       # DfE API client
├── tests/
│   └── test_server.py
└── examples/
    └── claude_desktop_config.json
```

## Data Sources

The server fetches data directly from official government APIs:

```python
# GIAS establishment data
gias_url = "https://www.get-information-schools.service.gov.uk/Establishments/Establishment/DownloadEstablishments"

# Ofsted data
ofsted_url = "https://files.ofsted.gov.uk/downloads/data/management_information_-_state-funded_schools_latest.csv"

# DfE Explore Education Statistics
dfe_api = "https://api.education.gov.uk/statistics/v1"
```

## Contributing

Contributions welcome! This MCP server helps parents, educators, and researchers access UK school data through AI assistants.

## License

MIT License - See LICENSE file for details

## Resources

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/docs)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [UK Schools MCP Server on MCP Registry](https://registry.modelcontextprotocol.io) (coming soon!)
- [Official MCP Servers List](https://github.com/modelcontextprotocol/servers)

## Acknowledgments

Built with data from:
- Department for Education (DfE)
- Office for Standards in Education (Ofsted)
- Get Information About Schools (GIAS)
