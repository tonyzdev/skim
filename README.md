# 🔍 skim

> **Stop feeding your AI giant data blobs.** Skim extracts the structure, saves the rest for later.

A Claude Code MCP Server that automatically **skims** large command outputs — returning only the schema/structure to the AI while preserving full data for on-demand inspection.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-MCP%20Server-blueviolet)](https://claude.com/claude-code)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)

## 🎯 The Problem

When AI agents run commands that return large outputs (API responses, database queries, log files), the entire content floods the context window:

```
❌ curl api.example.com/users
→ AI receives 500KB of JSON, consuming precious context
→ Token costs increase
→ AI gets distracted by irrelevant details
```

## ✨ The Solution

**skim** intercepts large outputs and returns only what matters — the structure:

```
✅ skim_exec("curl api.example.com/users")

→ AI receives:
  Saved: .claude-temp/20240104_143052_abc123.json

  Structure (JSON):
  {
    "users": [{ "id": "number", "name": "string", "email": "string" }],
    "pagination": { "page": "number", "total": "number" }
  }

  Stats: 512KB | 1000 items | JSON

→ Full data saved to temp file for later inspection
→ AI understands the shape without the bloat
```

## 🚀 Quick Start

### 1. Install

```bash
# Clone the repo
git clone https://github.com/tonyzdev/skim.git

# Install uv if you haven't
brew install uv  # macOS
# or: pip install uv
```

### 2. Add to Claude Code

```bash
claude mcp add -s user skim -- uv run --with mcp python3 /path/to/skim/server.py
```

Or manually add to `~/.claude.json`:

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

### 3. Restart Claude Code & Use

```
You: Use skim_exec to run: curl https://api.github.com/users

Claude: [Calls skim_exec]
        Got structure with 30 users, each has id, login, avatar_url...

You: Show me the first user's details

Claude: [Calls skim_drill with ".users[0]"]
        Here's the first user: { "id": 1, "login": "mojombo", ... }
```

## 🛠 MCP Tools

| Tool | Description |
|------|-------------|
| `skim_exec(command)` | Execute command, return schema for large outputs |
| `skim_drill(file, query)` | Drill into saved data with JSON path queries |
| `skim_list()` | List all cached temp files |
| `skim_clean(hours)` | Clean up old temp files |

## 📊 Supported Formats

| Format | What You Get |
|--------|--------------|
| **JSON** | Field names + types (`"id": "number"`) |
| **CSV** | Column names + 3 sample rows |
| **YAML** | Key structure |
| **XML/HTML** | Tag hierarchy |
| **Text/Logs** | Line count + first 5 lines preview |

## 💡 Use Cases

### API Development
```bash
skim_exec("curl -X POST localhost:3000/api/users -d '{...}'")
# See response structure, verify fields, drill into errors
```

### Database Queries
```bash
skim_exec("psql -c 'SELECT * FROM orders'")
# Get column names and types without 10,000 rows
```

### Log Analysis
```bash
skim_exec("cat /var/log/app.log")
# Preview format, then drill into specific line ranges
```

### Build Output
```bash
skim_exec("npm run build 2>&1")
# Capture full output, see summary, drill into errors
```

## ⚙️ Configuration

Edit `server.py` to customize:

| Setting | Default | Description |
|---------|---------|-------------|
| `THRESHOLD` | `1000` | Characters before skim kicks in |
| `MAX_SCHEMA_DEPTH` | `3` | How deep to extract nested structures |
| `ARRAY_SAMPLE_SIZE` | `1` | Items to sample from arrays |
| `TEMP_DIR` | `.claude-temp` | Where to save files |

## 📁 Temp Directory

- **Location:** `.claude-temp/` in your project
- **Auto-gitignore:** Added automatically on first use
- **⚠️ Warning:** Files are temporary cache — don't store important data here

## 🔧 Requirements

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) (for dependency management)

## 🤝 Contributing

PRs welcome! Ideas for improvement:

- [ ] Binary file support (images, PDFs)
- [ ] Streaming output support
- [ ] Custom schema extractors
- [ ] Integration with other AI tools

## 📄 License

MIT © 2024

---

<p align="center">
  <b>Stop the context bloat. Start skimming.</b>
  <br><br>
  <a href="https://github.com/tonyzdev/skim">⭐ Star on GitHub</a>
</p>
