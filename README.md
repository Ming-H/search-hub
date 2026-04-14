# Search Hub

English | **[中文](README.zh-CN.md)**

A personal professional search engine integrating 6 search channels. One command to search across all knowledge sources.

## Engines

| Engine | Purpose | Cost | Description |
|--------|---------|------|-------------|
| **local** | Local project search | Free | Scans 1300+ local documents, matches filenames and content |
| **feishu** | Feishu Wiki | Free | Reads documents via Feishu Open Platform API |
| **xcrawl** | Web search | Credits | Primary search engine with search/scrape/sitemap |
| **ddg** | DuckDuckGo | Free | Auto-fallback when XCrawl fails |
| **jina** | Web reader | Free | Converts any URL to Markdown |
| **notebooklm** | Deep Q&A | Free | AI-powered deep Q&A based on web page content |

## Quick Start

### Prerequisites

```bash
pip install ddgs
uv tool install notebooklm-mcp-cli && nlm login
```

### Configuration

Edit `.env`:

```
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
XCRAWL_API_KEY=your_xcrawl_key
```

Feishu app requires `wiki:wiki:readonly` and `docx:document:readonly` permissions. Register for XCrawl at [dash.xcrawl.com](https://dash.xcrawl.com/) (free 1000 credits).

### Feishu App Permissions

Enable in Feishu Open Platform:
- `wiki:wiki:readonly` — Read wiki spaces
- `docx:document:readonly` — Read document content
- Add the app as a collaborator to your wiki space

### Initialize Feishu Index

```bash
python3 search.py feishu refresh
```

## Usage

### Global Search (Recommended)

```bash
python3 search.py <keyword>          # local + feishu + XCrawl
python3 search.py <keyword> --deep   # additionally reads TOP web pages via Jina
```

### Single Engine

```bash
# Local
python3 search.py local <keyword>
python3 search.py local <keyword> --content

# Feishu
python3 search.py feishu search <keyword>
python3 search.py feishu search <keyword> --deep
python3 search.py feishu read <wiki_url_or_token>
python3 search.py feishu list
python3 search.py feishu refresh

# XCrawl
python3 search.py xcrawl <keyword>
python3 search.py xcrawl <keyword> 20          # specify result count
python3 search.py xcrawl scrape <url>          # scrape webpage
python3 search.py xcrawl map <url>             # site map
python3 search.py xcrawl map <url> 200         # limit URL count

# DuckDuckGo
python3 search.py ddg <keyword>

# Jina Reader
python3 search.py jina <url>

# NotebookLM
python3 search.py notebooklm read <url>
python3 search.py notebooklm ask <url> "question"
```

### Cache Management

```bash
python3 search.py cache          # view cache stats
python3 search.py cache clear    # clear all cache
```

## Architecture

```
search.py <keyword>
    │
    ├─ 1. local ──── Scan 6 local projects for .md/.txt/.json
    │
    ├─ 2. feishu ─── Match against Feishu wiki index
    │
    ├─ 3. xcrawl ─── Web search (primary)
    │     └─ Auto-fallback on failure → ddg (free backup)
    │
    └─ 4. [--deep] ── jina reads TOP 3 web page content
```

### Fallback Strategy

```
XCrawl fails/times out → Automatically switches to DuckDuckGo
```

### Cache Policy

| Rule | Value |
|------|-------|
| Search result cache | 1 hour |
| Jina web content cache | 24 hours |
| Max cache size | 50 MB |
| Expired cleanup | Auto-delete on read |
| Overflow cleanup | Oldest-first deletion before write |

## Local Projects Coverage

| Project | Path | Content |
|---------|------|---------|
| content-forge-ai | data/ | AI daily digest + tech series (711 docs) |
| ai-insights | content/ | Hugo blog (411 docs) |
| yinxiang-migration | obsidian-vault | Evernote migration (189 docs) |
| personal-wiki | wiki/ | Personal knowledge base |
| devfox-pulse | output/ | Published content |
| devfox-vision | prompt_libs/ | AI prompt library |

## File Structure

```
search-hub/
├── .env           # API credentials (Feishu + XCrawl)
├── .cache/        # Auto-managed cache directory
├── config.json    # Feishu wiki index
└── search.py      # Single entry point
```

## Examples

```bash
# Search a tech topic
$ python3 search.py "AI Agent"
🔍 本地项目...
🔍 飞书知识库...
🔍 互联网 (XCrawl)...
==================================================
  「AI Agent」共 70 个匹配
==================================================

  [本地项目] 65 个结果：...

  [XCrawl] 5 个结果：...

# Read a Feishu document
$ python3 search.py feishu read MBiJwF5QhiwAvQk0c8LckGZOnec
# HappyHorse 学习手册
# ...

# Ask NotebookLM about a webpage
$ python3 search.py notebooklm ask https://example.com "What is the core competitive advantage?"
```
