---
name: search-hub
description: Personal search hub integrating 6 engines (local files, Feishu wiki, XCrawl, DuckDuckGo, Jina Reader, NotebookLM) into a unified CLI. This skill should be used when the user needs to search across multiple sources, find information in local projects or Feishu docs, scrape web pages, or perform deep content retrieval. Triggers on keywords like "search", "搜索", "查找", "飞书搜索", "scrape", "read url", or when multi-source information gathering is needed.
---

# Search Hub

## Overview

Search Hub is a unified personal search engine that aggregates 6 different search and retrieval engines into a single CLI tool. It enables cross-source searching — from local project files to Feishu knowledge bases to the open web — with optional deep content reading capabilities.

## Core Capabilities

### 1. Unified Global Search

Run a keyword search across all engines simultaneously:

```bash
python3 scripts/search.py <keyword>
```

Searches local projects + Feishu + XCrawl (with DuckDuckGo fallback). Add `--deep` to auto-read top web results via Jina Reader for content summaries.

### 2. Feishu Knowledge Base

```bash
python3 scripts/search.py feishu search <keyword>        # Search Feishu docs by title
python3 scripts/search.py feishu search <keyword> --deep  # Search doc content too
python3 scripts/search.py feishu read <url-or-token>      # Read a Feishu document
python3 scripts/search.py feishu list                     # List all indexed docs
python3 scripts/search.py feishu refresh                  # Rebuild Feishu index
```

Requires `FEISHU_APP_ID` and `FEISHU_APP_SECRET` in `.env`.

### 3. Local Project Search

```bash
python3 scripts/search.py local <keyword>          # Search filenames
python3 scripts/search.py local <keyword> --content # Search file contents too
```

Scans configured local projects (see `LOCAL_PROJECTS` dict in script). Supports `.md`, `.txt`, `.json` files.

### 4. XCrawl Web Search & Scraping

```bash
python3 scripts/search.py xcrawl <keyword>         # Web search
python3 scripts/search.py xcrawl scrape <url>       # Scrape page as markdown
python3 scripts/search.py xcrawl map <url>           # Get site map URLs
```

Requires `XCRAWL_API_KEY` in `.env`.

### 5. DuckDuckGo Search

```bash
python3 scripts/search.py ddg <keyword>
```

Fallback engine when XCrawl is unavailable. Requires `ddgs` or `duckduckgo-search` pip package.

### 6. Jina Reader

```bash
python3 scripts/search.py jina <url>
```

Fetches any URL and converts to clean text via `r.jina.ai`. Cached for 24 hours.

### 7. NotebookLM Integration

```bash
python3 scripts/search.py notebooklm read <url>           # Summarize a URL
python3 scripts/search.py notebooklm ask <url> <question>  # Q&A on a URL
```

Requires the `nlm` CLI tool installed.

## Setup Requirements

### Environment File (.env)

Create a `.env` file in the working directory with:

```
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
XCRAWL_API_KEY=your_xcrawl_key
```

Only the keys for engines you plan to use are needed.

### Python Dependencies

- `ddgs` or `duckduckgo-search` — for DuckDuckGo search
- Standard library only for other engines (`urllib`, `json`, `subprocess`)

### External Tools

- `nlm` CLI — for NotebookLM integration (optional)

## Caching

All search results are cached in `.cache/` with:
- Default TTL: 1 hour (Jina: 24 hours)
- Max cache size: 50MB with LRU eviction
- Manage with: `python3 scripts/search.py cache` (stats) or `cache clear`

## How to Use This Skill

1. When the user asks to search for something, run the unified search first: `python3 scripts/search.py <keyword>`
2. For Feishu-specific queries, use `feishu search` / `feishu read`
3. For web content extraction, use `jina <url>` or `xcrawl scrape <url>`
4. For deep research, add `--deep` flag to get content summaries of top results
5. Results are printed in a structured format grouped by source engine
