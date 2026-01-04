---
name: list
description: List all temp files saved by skim. Use when you need to see what large outputs have been cached or find a specific saved file.
---

# List Temp Files

View all files in the skim temp directory.

## Usage

```bash
# List all temp files with details
ls -lah .claude-temp/

# List only JSON files
ls -la .claude-temp/*.json 2>/dev/null || echo "No JSON files"

# List only CSV files
ls -la .claude-temp/*.csv 2>/dev/null || echo "No CSV files"

# List only text files
ls -la .claude-temp/*.txt 2>/dev/null || echo "No text files"

# List with human-readable sizes, sorted by time (newest first)
ls -laht .claude-temp/

# Show file count and total size
echo "Files: $(ls -1 .claude-temp/ 2>/dev/null | wc -l | tr -d ' ')"
du -sh .claude-temp/ 2>/dev/null || echo "Directory empty or not exists"
```

## File Naming Convention

Files are named: `{YYYYMMDD}_{HHMMSS}_{hash}.{ext}`

- Date and time of when the output was saved
- Hash for uniqueness
- Extension indicates format: `.json`, `.csv`, `.yaml`, `.xml`, `.txt`

## When to Use

- To find a previously saved output
- To check how many temp files exist
- Before using `/skim:clean` to see what will be deleted
