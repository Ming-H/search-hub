---
name: search-hub
description: Personal search hub integrating 18 engines (local files, Feishu wiki, SearXNG, DuckDuckGo, Brave, Wikipedia, arXiv, Hacker News, GitHub, Reddit, Stack Overflow, Semantic Scholar, CrossRef, OpenAlex, Internet Archive, XCrawl, Jina Reader, NotebookLM) into a unified CLI with concurrent search. This skill should be used when the user needs to search across multiple sources, find information in local projects or Feishu docs, scrape web pages, or perform deep content retrieval. Triggers on keywords like "search", "搜索", "查找", "飞书搜索", "scrape", "read url", or when multi-source information gathering is needed.
---

# Search Hub

## Overview

Search Hub is a unified personal search engine that aggregates 18 different search and retrieval engines into a single CLI tool. All searches run concurrently for maximum speed. Free engines are prioritized.

## Core Capabilities

### 1. Unified Global Search (Concurrent)

Run a keyword search across all engines simultaneously:

```bash
python3 search.py <keyword>           # All engines (concurrent)
python3 search.py <keyword> --deep    # + Jina reads top web results
python3 search.py <keyword> --web     # Web search only
python3 search.py <keyword> --academic # Academic search only
python3 search.py <keyword> --tech    # Tech community search only
```

### 2. 18 Engines

**Web Search:**
- `searxng` — Meta-search (aggregates Google, Bing, etc.), completely free
- `xcrawl` — Web search/scrape/sitemap (paid, requires key)
- `ddg` — DuckDuckGo (free, fallback)
- `brave` — Brave Search (free 2000/month, optional key)

**Knowledge:**
- `wiki` — Wikipedia (free, auto-detects Chinese)
- `feishu` — Feishu Wiki docs (requires app credentials)
- `local` — Local project files (free)

**Academic:**
- `arxiv` — CS/Physics papers (free)
- `scholar` — Semantic Scholar (free)
- `crossref` — Academic metadata (free)
- `openalex` — Academic works (free)

**Tech Community:**
- `hn` — Hacker News via Algolia (free)
- `github` — GitHub repositories (free)
- `reddit` — Reddit discussions (free)
- `stackoverflow` — Stack Overflow Q&A (free)

**Media & Tools:**
- `archive` — Internet Archive (free)
- `jina` — URL to Markdown reader (free)
- `notebooklm` — AI deep Q&A on URLs (free, requires nlm CLI)

### 3. Single Engine Usage

```bash
python3 search.py searxng <keyword>
python3 search.py wiki <keyword> [--zh]
python3 search.py arxiv <keyword>
python3 search.py hn <keyword>
python3 search.py github <keyword>
python3 search.py reddit <keyword>
python3 search.py stackoverflow <keyword>
python3 search.py scholar <keyword>
python3 search.py crossref <keyword>
python3 search.py openalex <keyword>
python3 search.py archive <keyword>
# ... and all original engines
```

### 4. Engine Status

```bash
python3 search.py engines    # List all engines with availability
```

## Setup Requirements

### Environment File (.env)

```
# Required for Feishu
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret

# Required for XCrawl
XCRAWL_API_KEY=your_xcrawl_key

# Optional: Brave Search (free 2000/month)
BRAVE_API_KEY=your_brave_key
```

### Python Dependencies

- `ddgs` or `duckduckgo-search` — for DuckDuckGo search
- Standard library only for all other engines

### External Tools

- `nlm` CLI — for NotebookLM integration (optional)

## Caching

- Default TTL: 1 hour (academic/wiki: 24 hours)
- Max cache size: 50 MB with LRU eviction
- Manage: `python3 search.py cache` (stats) or `cache clear`

## How to Use This Skill

1. When the user asks to search, run unified search: `python3 search.py <keyword>`
2. Use `--web` for general web searches, `--academic` for papers, `--tech` for code/communities
3. For single-source queries, use the engine name directly
4. For web content extraction: `python3 search.py jina <url>`
5. `python3 search.py engines` shows which engines are ready
