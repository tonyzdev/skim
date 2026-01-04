---
name: drill
description: Deep dive into a saved temp file. Use when you need to view specific content from a large output that was saved by skim. Supports jq for JSON files and line ranges for text files.
---

# Drill Into Temp File

View specific content from a saved large output file.

## Usage

```bash
# View entire file (use with caution for large files)
cat .claude-temp/<filename>

# For JSON files - use jq to extract specific paths
jq '.<path>' .claude-temp/<filename>.json

# Examples:
jq '.users[0]' .claude-temp/20240104_143052_abc123.json      # First user
jq '.users[:3]' .claude-temp/20240104_143052_abc123.json     # First 3 users
jq '.users[0].name' .claude-temp/20240104_143052_abc123.json # Specific field
jq '.data | keys' .claude-temp/20240104_143052_abc123.json   # List all keys

# For CSV files
head -20 .claude-temp/<filename>.csv       # First 20 lines
cut -d',' -f1,2 .claude-temp/<filename>.csv # Specific columns

# For text files - use head/tail/sed
head -20 .claude-temp/<filename>.txt      # First 20 lines
tail -20 .claude-temp/<filename>.txt      # Last 20 lines
sed -n '10,20p' .claude-temp/<filename>.txt  # Lines 10-20
```

## When to Use

- After skim saves a large output and shows you the schema
- When you need to verify specific values in the data
- When debugging requires seeing actual content, not just structure

## Tips

- Always start with specific paths rather than reading the whole file
- Use `jq` for JSON navigation - it's more efficient than reading raw content
- If you need multiple values, combine them in one jq query: `jq '{id: .id, name: .name}'`
