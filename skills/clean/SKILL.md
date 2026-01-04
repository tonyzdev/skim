---
name: clean
description: Clean up the skim temp directory. Use when you want to remove old cached outputs to free up space or start fresh.
---

# Clean Temp Directory

Remove cached files from the skim temp directory.

## Usage

```bash
# Remove all temp files (keeps the directory and README)
rm -f .claude-temp/*.json .claude-temp/*.csv .claude-temp/*.txt .claude-temp/*.yaml .claude-temp/*.xml

# Remove files older than 1 day
find .claude-temp/ -type f \( -name "*.json" -o -name "*.csv" -o -name "*.txt" \) -mtime +1 -delete

# Remove files older than 1 hour
find .claude-temp/ -type f \( -name "*.json" -o -name "*.csv" -o -name "*.txt" \) -mmin +60 -delete

# Show what would be deleted (dry run for files older than 1 day)
find .claude-temp/ -type f \( -name "*.json" -o -name "*.csv" -o -name "*.txt" \) -mtime +1

# Remove entire directory (will be recreated on next save)
rm -rf .claude-temp/
```

## When to Use

- After finishing a debugging session
- When temp files are taking up too much space
- When you want to start fresh

## Note

The `.claude-temp/` directory is already in `.gitignore`, so these files won't be committed. This cleanup is optional and mainly for keeping your workspace tidy.
