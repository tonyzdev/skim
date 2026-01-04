#!/usr/bin/env python3
"""
skim MCP Server
Executes commands and returns only schema/structure for large outputs.
"""

import json
import os
import re
import hashlib
import subprocess
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

# Configuration
THRESHOLD = 1000  # Characters threshold to trigger skim
TEMP_DIR = ".claude-temp"
MAX_SCHEMA_DEPTH = 3
ARRAY_SAMPLE_SIZE = 1
PREVIEW_LINES = 5

# Initialize MCP server
mcp = FastMCP("skim")


def get_project_root() -> Path:
    """Get project root from environment or current directory."""
    return Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))


def ensure_temp_dir(project_root: Path) -> Path:
    """Ensure temp directory exists and is gitignored."""
    temp_path = project_root / TEMP_DIR
    temp_path.mkdir(exist_ok=True)

    # Create README in temp dir
    readme_path = temp_path / "README.md"
    if not readme_path.exists():
        readme_path.write_text("""# Claude Code Temp Cache

This directory stores temporary files from large command outputs.

- Files may be cleaned up at any time
- Do NOT store important data here
- Automatically added to .gitignore

Use `skim_list` to view files
Use `skim_clean` to clean up
""")

    # Ensure .gitignore includes temp dir
    gitignore_path = project_root / ".gitignore"
    gitignore_entry = f"\n# Claude Code temp cache\n{TEMP_DIR}/\n"

    if gitignore_path.exists():
        content = gitignore_path.read_text()
        if TEMP_DIR not in content:
            with open(gitignore_path, "a") as f:
                f.write(gitignore_entry)
    else:
        gitignore_path.write_text(gitignore_entry)

    return temp_path


def extract_json_schema(obj: Any, depth: int = 0) -> Any:
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


def detect_format(content: str) -> str:
    """Detect content format."""
    content_stripped = content.strip()

    # JSON
    if content_stripped.startswith(('{', '[')):
        try:
            json.loads(content_stripped)
            return 'json'
        except:
            pass

    # YAML
    if content_stripped.startswith('---') or re.match(r'^[\w_]+:\s', content_stripped, re.MULTILINE):
        try:
            import yaml
            yaml.safe_load(content_stripped)
            return 'yaml'
        except:
            pass

    # CSV (stricter detection)
    lines = content_stripped.split('\n')[:10]
    if len(lines) >= 2:
        first_line = lines[0]
        first_commas = first_line.count(',')
        looks_like_header = (
            first_commas >= 2 and
            not re.search(r'\d{4}-\d{2}-\d{2}', first_line) and
            not re.search(r'\[\w+\]', first_line) and
            not re.search(r':\d{2}:\d{2}', first_line) and
            len(first_line) < 200 and
            all(len(h.strip()) < 30 for h in first_line.split(','))
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


def extract_csv_schema(content: str) -> tuple:
    """Extract CSV structure."""
    lines = content.strip().split('\n')
    if not lines:
        return None, "Empty CSV"

    headers = [h.strip().strip('"\'') for h in lines[0].split(',')]
    sample_rows = []
    for line in lines[1:4]:
        if line.strip():
            values = [v.strip().strip('"\'')[:20] + ('...' if len(v) > 20 else '') for v in line.split(',')]
            sample_rows.append(dict(zip(headers, values)))

    schema = {'columns': headers, 'sample': sample_rows}
    row_count = len([l for l in lines[1:] if l.strip()])
    return schema, f"{row_count} rows | {len(headers)} columns | CSV"


def extract_xml_schema(content: str) -> dict:
    """Extract XML tag structure."""
    tags = re.findall(r'<([\w_:]+)[^>]*>', content)
    unique_tags = list(dict.fromkeys(tags))[:15]
    return {'tags': unique_tags}


def extract_yaml_schema(content: str) -> Any:
    """Extract YAML structure."""
    try:
        import yaml
        data = yaml.safe_load(content)
        return extract_json_schema(data)
    except:
        keys = re.findall(r'^([\w_]+):', content, re.MULTILINE)
        return {'keys': list(dict.fromkeys(keys))[:10]}


def get_stats(content: str, format_type: str, data: Any = None) -> str:
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
    return f"{size_str} | {lines} lines | {format_type.upper()}"


def save_and_summarize(content: str, project_root: Path) -> str:
    """Save content to temp file and return summary."""
    temp_path = ensure_temp_dir(project_root)

    format_type = detect_format(content)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    content_hash = hashlib.md5(content.encode()).hexdigest()[:8]

    ext_map = {'json': 'json', 'yaml': 'yaml', 'csv': 'csv', 'xml': 'xml', 'html': 'html', 'text': 'txt'}
    ext = ext_map.get(format_type, 'txt')
    filename = f"{timestamp}_{content_hash}.{ext}"

    file_path = temp_path / filename
    file_path.write_text(content)
    relative_path = f"{TEMP_DIR}/{filename}"

    # Extract schema
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
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
        title = title_match.group(1) if title_match else None
        schema = {'title': title, 'tags': extract_xml_schema(content).get('tags', [])}
        stats = get_stats(content, format_type)

    if stats is None:
        stats = get_stats(content, format_type)

    # Build summary
    summary_parts = [f"Saved: {relative_path}", ""]

    if schema:
        summary_parts.extend([
            f"Structure ({format_type.upper()}):",
            json.dumps(schema, indent=2, ensure_ascii=False),
            "",
        ])
    else:
        lines = content.split('\n')[:PREVIEW_LINES]
        preview = '\n'.join(lines)
        if len(content.split('\n')) > PREVIEW_LINES:
            preview += "\n..."
        summary_parts.extend(["Preview:", preview, ""])

    summary_parts.extend([
        f"Stats: {stats}",
        "",
        "Use skim_drill to view specific content.",
    ])

    return '\n'.join(summary_parts)


@mcp.tool()
def skim_exec(command: str, shell: bool = True) -> str:
    """
    Execute a command and return only the schema/structure if output is large.

    For large outputs (>1000 chars), saves to temp file and returns only the structure.
    For small outputs, returns the full content.

    Args:
        command: The shell command to execute
        shell: Whether to use shell execution (default: True)

    Returns:
        Full output if small, or schema/structure if large
    """
    project_root = get_project_root()

    try:
        result = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(project_root)
        )

        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"

        if result.returncode != 0:
            output = f"[Exit code: {result.returncode}]\n{output}"

        # If output is small, return as-is
        if len(output) < THRESHOLD:
            return output

        # Large output: save and return schema
        return save_and_summarize(output, project_root)

    except subprocess.TimeoutExpired:
        return "[Error] Command timed out after 120 seconds"
    except Exception as e:
        return f"[Error] {str(e)}"


@mcp.tool()
def skim_drill(file_path: str, query: str = "") -> str:
    """
    View specific content from a saved temp file.

    Args:
        file_path: Path to the temp file (e.g., .claude-temp/xxx.json)
        query: Optional query - for JSON use jq syntax (e.g., '.users[0]'),
               for text use line range (e.g., '1-10' or 'head:20' or 'tail:20')

    Returns:
        The requested portion of the file content
    """
    project_root = get_project_root()
    full_path = project_root / file_path

    if not full_path.exists():
        return f"[Error] File not found: {file_path}"

    content = full_path.read_text()

    if not query:
        # No query: return first 50 lines or 2000 chars
        lines = content.split('\n')[:50]
        result = '\n'.join(lines)
        if len(result) > 2000:
            result = result[:2000] + "\n...[truncated]"
        return result

    # JSON query using jq syntax
    if file_path.endswith('.json'):
        try:
            data = json.loads(content)
            # Simple path parsing (supports .key, [0], [:3])
            result = eval_json_path(data, query)
            return json.dumps(result, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"[Error] Query failed: {e}"

    # Text file: line range
    lines = content.split('\n')
    if query.startswith('head:'):
        n = int(query[5:])
        return '\n'.join(lines[:n])
    elif query.startswith('tail:'):
        n = int(query[5:])
        return '\n'.join(lines[-n:])
    elif '-' in query:
        start, end = map(int, query.split('-'))
        return '\n'.join(lines[start-1:end])

    return content


def eval_json_path(data: Any, path: str) -> Any:
    """Evaluate a simple JSON path expression."""
    if not path or path == '.':
        return data

    # Remove leading dot
    if path.startswith('.'):
        path = path[1:]

    current = data
    # Split by . but keep [] parts together
    parts = re.split(r'\.(?![^\[]*\])', path)

    for part in parts:
        if not part:
            continue

        # Handle array indexing
        match = re.match(r'(\w+)?(\[.+\])?', part)
        if match:
            key, index_part = match.groups()

            if key and isinstance(current, dict):
                current = current.get(key, None)
                if current is None:
                    return None

            if index_part:
                # Parse index
                idx_match = re.match(r'\[(-?\d+)\]', index_part)
                slice_match = re.match(r'\[:(\d+)\]', index_part)

                if idx_match:
                    idx = int(idx_match.group(1))
                    current = current[idx]
                elif slice_match:
                    n = int(slice_match.group(1))
                    current = current[:n]

    return current


@mcp.tool()
def skim_list() -> str:
    """
    List all temp files saved by skim.

    Returns:
        List of cached files with their sizes and timestamps
    """
    project_root = get_project_root()
    temp_path = project_root / TEMP_DIR

    if not temp_path.exists():
        return "No temp directory found. No files have been cached yet."

    files = []
    for f in sorted(temp_path.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.name == "README.md":
            continue
        stat = f.stat()
        size = stat.st_size
        if size < 1024:
            size_str = f"{size}B"
        elif size < 1024 * 1024:
            size_str = f"{size/1024:.1f}KB"
        else:
            size_str = f"{size/(1024*1024):.1f}MB"

        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        files.append(f"{f.name}  {size_str}  {mtime}")

    if not files:
        return "Temp directory is empty."

    return f"Cached files ({len(files)}):\n" + '\n'.join(files)


@mcp.tool()
def skim_clean(older_than_hours: int = 0) -> str:
    """
    Clean up temp files.

    Args:
        older_than_hours: Only delete files older than this many hours.
                         Use 0 to delete all files.

    Returns:
        Summary of deleted files
    """
    project_root = get_project_root()
    temp_path = project_root / TEMP_DIR

    if not temp_path.exists():
        return "No temp directory found."

    deleted = 0
    now = datetime.now().timestamp()

    for f in temp_path.iterdir():
        if f.name == "README.md":
            continue

        if older_than_hours > 0:
            age_hours = (now - f.stat().st_mtime) / 3600
            if age_hours < older_than_hours:
                continue

        f.unlink()
        deleted += 1

    return f"Deleted {deleted} file(s)."


if __name__ == "__main__":
    mcp.run()
