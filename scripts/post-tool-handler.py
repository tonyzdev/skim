#!/usr/bin/env python3
"""
context-saver PostToolUse Hook
Automatically saves large Bash outputs to temp files and returns schema/structure.
Supports: JSON, YAML, CSV, XML, plain text
"""

import json
import sys
import os
import re
import hashlib
from datetime import datetime
from pathlib import Path

# Configuration
THRESHOLD = 1000  # Characters threshold to trigger save
TEMP_DIR = ".claude-temp"
MAX_SCHEMA_DEPTH = 3
ARRAY_SAMPLE_SIZE = 1
PREVIEW_LINES = 5

def get_project_root():
    """Get project root from environment or current directory."""
    return os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

def ensure_temp_dir(project_root):
    """Ensure temp directory exists and is gitignored."""
    temp_path = Path(project_root) / TEMP_DIR
    temp_path.mkdir(exist_ok=True)

    # Create README in temp dir
    readme_path = temp_path / "README.md"
    if not readme_path.exists():
        readme_path.write_text("""# Claude Code Temp Cache

This directory stores temporary files from large command outputs.

- Files may be cleaned up at any time
- Do NOT store important data here
- Automatically added to .gitignore

Use `/context-saver:list` to view files
Use `/context-saver:clean` to clean up
""")

    # Ensure .gitignore includes temp dir
    gitignore_path = Path(project_root) / ".gitignore"
    gitignore_entry = f"\n# Claude Code temp cache\n{TEMP_DIR}/\n"

    if gitignore_path.exists():
        content = gitignore_path.read_text()
        if TEMP_DIR not in content:
            with open(gitignore_path, "a") as f:
                f.write(gitignore_entry)
    else:
        gitignore_path.write_text(gitignore_entry)

    return temp_path

def extract_json_schema(obj, depth=0):
    """Extract JSON schema (structure only, no values)."""
    if depth > MAX_SCHEMA_DEPTH:
        return "..."

    if isinstance(obj, dict):
        return {k: extract_json_schema(v, depth + 1) for k, v in list(obj.items())[:10]}
    elif isinstance(obj, list):
        if not obj:
            return "[]"
        sample = obj[:ARRAY_SAMPLE_SIZE]
        return [extract_json_schema(item, depth + 1) for item in sample]
    elif isinstance(obj, str):
        return "string"
    elif isinstance(obj, bool):
        return "boolean"
    elif isinstance(obj, int):
        return "number"
    elif isinstance(obj, float):
        return "number"
    elif obj is None:
        return "null"
    else:
        return str(type(obj).__name__)

def detect_format(content):
    """Detect content format."""
    content_stripped = content.strip()

    # JSON
    if content_stripped.startswith(('{', '[')):
        try:
            json.loads(content_stripped)
            return 'json'
        except:
            pass

    # YAML (starts with --- or has key: value pattern)
    if content_stripped.startswith('---') or re.match(r'^[\w_]+:\s', content_stripped, re.MULTILINE):
        try:
            import yaml
            yaml.safe_load(content_stripped)
            return 'yaml'
        except:
            pass

    # CSV (stricter detection: header-like first line, consistent commas, no timestamps/brackets)
    lines = content_stripped.split('\n')[:10]
    if len(lines) >= 2:
        first_line = lines[0]
        first_commas = first_line.count(',')
        # Check if first line looks like header (no timestamps, brackets, or long text)
        looks_like_header = (
            first_commas >= 2 and
            not re.search(r'\d{4}-\d{2}-\d{2}', first_line) and  # No dates
            not re.search(r'\[\w+\]', first_line) and  # No log levels like [INFO]
            not re.search(r':\d{2}:\d{2}', first_line) and  # No time
            len(first_line) < 200 and  # Header shouldn't be too long
            all(len(h.strip()) < 30 for h in first_line.split(','))  # Each header short
        )
        if looks_like_header and all(line.count(',') == first_commas for line in lines[:5] if line.strip()):
            return 'csv'

    # XML
    if content_stripped.startswith('<?xml') or re.match(r'^<[\w_]+[^>]*>', content_stripped):
        return 'xml'

    # HTML
    if re.match(r'^<!DOCTYPE\s+html|^<html', content_stripped, re.IGNORECASE):
        return 'html'

    return 'text'

def extract_csv_schema(content):
    """Extract CSV structure: column names and sample rows."""
    lines = content.strip().split('\n')
    if not lines:
        return None, "Empty CSV"

    # Assume first line is header
    headers = [h.strip().strip('"\'') for h in lines[0].split(',')]

    # Get sample data (first 3 data rows)
    sample_rows = []
    for line in lines[1:4]:
        if line.strip():
            values = [v.strip().strip('"\'')[:20] + ('...' if len(v) > 20 else '') for v in line.split(',')]
            sample_rows.append(dict(zip(headers, values)))

    schema = {
        'columns': headers,
        'sample': sample_rows
    }

    row_count = len([l for l in lines[1:] if l.strip()])
    return schema, f"{row_count} rows | {len(headers)} columns | CSV"

def extract_xml_schema(content, depth=0, max_depth=3):
    """Extract XML tag structure."""
    if depth > max_depth:
        return "..."

    # Simple regex-based extraction (not full XML parsing)
    tags = re.findall(r'<([\w_:]+)[^>]*>', content)
    unique_tags = list(dict.fromkeys(tags))[:15]  # Keep order, limit to 15

    return {'tags': unique_tags}

def extract_yaml_schema(content):
    """Extract YAML structure."""
    try:
        import yaml
        data = yaml.safe_load(content)
        return extract_json_schema(data)
    except:
        # Fallback: extract top-level keys
        keys = re.findall(r'^([\w_]+):', content, re.MULTILINE)
        return {'keys': list(dict.fromkeys(keys))[:10]}

def get_stats(content, format_type, data=None):
    """Get statistics about the content."""
    size_bytes = len(content.encode('utf-8'))
    if size_bytes < 1024:
        size_str = f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        size_str = f"{size_bytes / 1024:.1f}KB"
    else:
        size_str = f"{size_bytes / (1024 * 1024):.1f}MB"

    if format_type == 'json' and data is not None:
        if isinstance(data, list):
            return f"{size_str} | {len(data)} items | JSON"
        elif isinstance(data, dict):
            return f"{size_str} | {len(data)} keys | JSON"

    lines = content.count('\n') + 1
    format_label = format_type.upper()
    return f"{size_str} | {lines} lines | {format_label}"

def save_and_summarize(content, project_root):
    """Save content to temp file and return summary."""
    temp_path = ensure_temp_dir(project_root)

    # Detect format
    format_type = detect_format(content)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    content_hash = hashlib.md5(content.encode()).hexdigest()[:8]

    ext_map = {
        'json': 'json',
        'yaml': 'yaml',
        'csv': 'csv',
        'xml': 'xml',
        'html': 'html',
        'text': 'txt'
    }
    ext = ext_map.get(format_type, 'txt')
    filename = f"{timestamp}_{content_hash}.{ext}"

    # Save file
    file_path = temp_path / filename
    file_path.write_text(content)
    relative_path = f"{TEMP_DIR}/{filename}"

    # Extract schema based on format
    schema = None
    stats = None

    if format_type == 'json':
        try:
            data = json.loads(content)
            schema = extract_json_schema(data)
            stats = get_stats(content, format_type, data)
        except:
            format_type = 'text'

    if format_type == 'yaml':
        schema = extract_yaml_schema(content)
        stats = get_stats(content, format_type)

    elif format_type == 'csv':
        schema, stats = extract_csv_schema(content)

    elif format_type == 'xml':
        schema = extract_xml_schema(content)
        stats = get_stats(content, format_type)

    elif format_type == 'html':
        # Extract title and main tags
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
        title = title_match.group(1) if title_match else None
        schema = {'title': title, 'tags': extract_xml_schema(content).get('tags', [])}
        stats = get_stats(content, format_type)

    if stats is None:
        stats = get_stats(content, format_type)

    # Build summary
    summary_parts = [
        f"Large output saved: {relative_path}",
        "",
    ]

    if schema:
        summary_parts.extend([
            f"Structure ({format_type.upper()}):",
            json.dumps(schema, indent=2, ensure_ascii=False),
            "",
        ])
    else:
        # For plain text, show preview
        lines = content.split('\n')[:PREVIEW_LINES]
        preview = '\n'.join(lines)
        if len(content.split('\n')) > PREVIEW_LINES:
            preview += "\n..."
        summary_parts.extend([
            "Preview:",
            preview,
            "",
        ])

    summary_parts.extend([
        f"Stats: {stats}",
        "",
        "View details:",
    ])

    if format_type == 'json':
        summary_parts.extend([
            f"  jq '.' {relative_path}                    # 全部内容",
            f"  jq '.key' {relative_path}                 # 特定字段",
            f"  jq '.[0]' {relative_path}                 # 第一个元素",
        ])
    elif format_type == 'csv':
        summary_parts.extend([
            f"  head -20 {relative_path}                  # 前20行",
            f"  cut -d',' -f1,2 {relative_path}           # 特定列",
        ])
    else:
        summary_parts.extend([
            f"  head -50 {relative_path}                  # 前50行",
            f"  tail -50 {relative_path}                  # 后50行",
            f"  sed -n '10,20p' {relative_path}           # 行10-20",
        ])

    return '\n'.join(summary_parts)

def main():
    try:
        # Read hook input from stdin
        input_data = json.load(sys.stdin)

        # Only process Bash tool
        tool_name = input_data.get("tool_name", "")
        if tool_name != "Bash":
            sys.exit(0)

        # Get tool response
        tool_response = input_data.get("tool_response", "")
        if not tool_response:
            sys.exit(0)

        # Check if output exceeds threshold
        if len(tool_response) < THRESHOLD:
            sys.exit(0)

        # Get project root
        project_root = get_project_root()

        # Save and generate summary
        summary = save_and_summarize(tool_response, project_root)

        # Output summary
        print(summary)

        sys.exit(0)

    except Exception as e:
        # On error, let original output through
        print(f"context-saver error: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()
