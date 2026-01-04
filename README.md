# skim

A Claude Code plugin that **skims** large command outputs - automatically saves them to temp files and returns only the structure/schema to the AI. This reduces context pollution and token usage while preserving full data for detailed inspection when needed.

## Features

- **Auto-save large outputs** - Bash outputs exceeding 1000 characters are automatically saved
- **Schema extraction** - Returns structure (field names + types) instead of full content
- **Multi-format support** - JSON, CSV, YAML, XML, plain text
- **Drill-down capability** - View specific parts of saved data using jq/head/tail
- **Auto-gitignore** - Temp directory is automatically added to `.gitignore`

## Installation

```bash
# Install from GitHub
claude plugin install skim@your-marketplace

# Or install locally
claude plugin install ./skim
```

## How It Works

```
Bash command produces large output (> 1000 chars)
    ↓
PostToolUse Hook intercepts
    ↓
Saves to .claude-temp/{timestamp}_{hash}.{json|csv|txt}
    ↓
Returns to AI:
  - File path
  - Schema/structure only
  - Statistics (size, item count)
  - Usage hints for drill-down
    ↓
AI can use /skim:drill to view specific content
```

## Example

When a Bash command returns a large JSON response:

**Before (without skim):**
```
AI sees entire 500KB response, consuming context window
```

**After (with skim):**
```
Large output saved: .claude-temp/20240104_143052_abc123.json

Structure (JSON):
{
  "users": [{ "id": "number", "name": "string", "email": "string" }],
  "pagination": { "page": "number", "total": "number" }
}

Stats: 512KB | 1000 items | JSON

View details:
  jq '.' .claude-temp/20240104_143052_abc123.json           # Full content
  jq '.users[0]' .claude-temp/20240104_143052_abc123.json   # First user
```

## Skills

| Skill | Description |
|-------|-------------|
| `/skim:drill` | View specific content from saved files using jq/JSONPath |
| `/skim:list` | List all cached temp files |
| `/skim:clean` | Clean up temp directory |

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

Edit `scripts/post-tool-handler.py` to customize:

| Setting | Default | Description |
|---------|---------|-------------|
| `THRESHOLD` | 1000 | Character count to trigger save |
| `MAX_SCHEMA_DEPTH` | 3 | Max depth for schema extraction |
| `ARRAY_SAMPLE_SIZE` | 1 | Number of array items to sample |
| `TEMP_DIR` | `.claude-temp` | Temp directory name |

## Requirements

- Python 3.6+
- `jq` (recommended, usually pre-installed on macOS/Linux)

## License

MIT
