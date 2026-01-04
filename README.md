# skim

A Claude Code MCP Server that **skims** large command outputs - executes commands and returns only the structure/schema to the AI. This reduces context pollution and token usage while preserving full data for detailed inspection when needed.

## Features

- **Execute & Skim** - Run commands via `skim_exec`, get only schema for large outputs
- **Schema extraction** - Returns structure (field names + types) instead of full content
- **Multi-format support** - JSON, CSV, YAML, XML, plain text
- **Drill-down capability** - View specific parts of saved data using `skim_drill`
- **Auto-gitignore** - Temp directory is automatically added to `.gitignore`

## Installation

### Option 1: Add to Claude Code settings

Add to `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "skim": {
      "command": "uv",
      "args": ["run", "--with", "mcp", "python3", "/path/to/skim/server.py"]
    }
  }
}
```

### Option 2: Use .mcp.json in project

Create `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "skim": {
      "command": "uv",
      "args": ["run", "--with", "mcp", "python3", "/path/to/skim/server.py"]
    }
  }
}
```

## How It Works

```
AI calls: skim_exec("curl https://api.example.com/users")
    ↓
MCP Server executes command
    ↓
If output > 1000 chars:
    - Saves to .claude-temp/{timestamp}_{hash}.json
    - Returns only schema/structure
    ↓
AI sees only the schema, not the full content
    ↓
AI can use skim_drill to view specific content
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `skim_exec(command)` | Execute command, return schema if output is large |
| `skim_drill(file_path, query)` | View specific content from saved files |
| `skim_list()` | List all cached temp files |
| `skim_clean(older_than_hours)` | Clean up temp files |

## Example

**Using skim_exec:**
```
> skim_exec("curl https://api.example.com/users")

Saved: .claude-temp/20240104_143052_abc123.json

Structure (JSON):
{
  "users": [{ "id": "number", "name": "string", "email": "string" }],
  "pagination": { "page": "number", "total": "number" }
}

Stats: 512KB | 1000 items | JSON

Use skim_drill to view specific content.
```

**Using skim_drill:**
```
> skim_drill(".claude-temp/20240104_143052_abc123.json", ".users[0]")

{
  "id": 1,
  "name": "Alice",
  "email": "alice@example.com"
}
```

## Supported Formats

| Format | Schema Extraction |
|--------|-------------------|
| JSON | Field names + types |
| CSV | Column names + sample rows |
| YAML | Keys + structure |
| XML | Tag structure |
| Text/Logs | Line count + preview |

## Temp Directory

- **Location:** `.claude-temp/` in project root
- **Auto-gitignore:** Added automatically on first use
- **Warning:** Files may be cleaned up at any time. Do not store important data here.

## Configuration

Edit `server.py` to customize:

| Setting | Default | Description |
|---------|---------|-------------|
| `THRESHOLD` | 1000 | Character count to trigger skim |
| `MAX_SCHEMA_DEPTH` | 3 | Max depth for schema extraction |
| `ARRAY_SAMPLE_SIZE` | 1 | Number of array items to sample |
| `TEMP_DIR` | `.claude-temp` | Temp directory name |

## Requirements

- Python 3.8+
- `uv` (for running with mcp dependency)

Install uv: `brew install uv` (macOS) or `pip install uv`

## License

MIT
