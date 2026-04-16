# Search Hub

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-2.0.0-green.svg)](https://github.com/Ming-H/search-hub)

A free, open-source aggregated search engine CLI. Search 17 engines concurrently with a single command -- no API keys required for 12 of them.

English | **[中文](README.zh-CN.md)**

## Features

- **17 search engines** aggregated into one command
- **12 engines work out of the box** -- zero config, no API keys
- **Concurrent execution** via ThreadPoolExecutor (8 workers)
- **4 search modes**: `all`, `--web`, `--academic`, `--tech`
- **`--deep` flag** reads top web pages via Jina Reader
- **`--json` flag** for machine-readable output
- **Built-in cache** (1 hr search, 24 hr web content, 50 MB max)
- **Auto Chinese detection** for Wikipedia language selection
- **Single file**, no external dependencies (optional `ddgs` for DuckDuckGo)

## Engines

| Engine | Category | Cost | Config | Description |
|--------|----------|------|--------|-------------|
| SearXNG | Web | Free | Zero config | Meta search (Google, Bing, etc.) |
| DuckDuckGo | Web | Free | Optional `ddgs` | Privacy-first web search |
| Wikipedia | Web | Free | Zero config | Encyclopedia (auto zh/en) |
| arXiv | Academic | Free | Zero config | CS / Physics preprints |
| Semantic Scholar | Academic | Free | Zero config | AI-focused paper search |
| CrossRef | Academic | Free | Zero config | Academic DOI metadata |
| OpenAlex | Academic | Free | Zero config | Open academic works catalog |
| Hacker News | Tech | Free | Zero config | Tech news & discussions |
| GitHub | Tech | Free | Zero config | Code repositories |
| Reddit | Tech | Free | Zero config | Community discussions |
| Stack Overflow | Tech | Free | Zero config | Programming Q&A |
| Internet Archive | Web | Free | Zero config | Digital library |
| Jina Reader | Utility | Free | Zero config | Read any URL as Markdown |
| NotebookLM | Utility | Free | Requires `nlm` CLI | AI deep Q&A on web pages |
| XCrawl | Web | Paid | API key | Advanced web search & scrape |
| Feishu Wiki | Local | Free | App credentials | Feishu workspace documents |
| Local files | Local | Free | `config.json` | Search local project files |

**12 engines work immediately** with no configuration: SearXNG, DDG, Wikipedia, arXiv, Hacker News, GitHub, Reddit, Stack Overflow, Semantic Scholar, CrossRef, OpenAlex, Internet Archive.

## Quick Start

```bash
git clone https://github.com/Ming-H/search-hub.git
cd search-hub
pip install -r requirements.txt   # optional, for DuckDuckGo
python3 search.py "your keyword"  # that's it!
```

No `pip install` step is required if you skip DuckDuckGo. The script runs on Python 3.8+ with only stdlib.

## Usage

### Global Search (all engines concurrently)

```bash
python3 search.py "transformer"              # search all engines
python3 search.py "RAG" --academic           # academic papers only
python3 search.py "python async" --tech      # tech community only
python3 search.py "GPT-4" --web              # web search only
python3 search.py "AI Agent" --deep          # + read top 3 web pages
python3 search.py "AI Agent" --json          # JSON output for piping
```

### Single Engine

```bash
python3 search.py wiki "深度学习"            # Wikipedia (auto Chinese)
python3 search.py arxiv "attention mechanism"
python3 search.py github "web crawler"
python3 search.py hn "startup"
python3 search.py reddit "side project"
python3 search.py stackoverflow "python async"
python3 search.py scholar "large language model"
python3 search.py crossref "machine learning"
python3 search.py openalex "neural network"
python3 search.py searxng "best laptops 2025"
python3 search.py ddg "weather"
python3 search.py archive "old website"
python3 search.py jina https://example.com   # read any URL
python3 search.py local "project notes"
```

### Management Commands

```bash
python3 search.py init          # create config.json
python3 search.py engines       # show engine status
python3 search.py cache         # view cache stats
python3 search.py cache clear   # clear all cache
```

## Configuration

Run `python3 search.py init` to generate `config.json`:

```json
{
  "work_dir": "",
  "local_projects": {
    "my-notes": { "path": "/path/to/notes", "desc": "My notes" }
  },
  "feishu_domain": "your-company.feishu.cn",
  "searxng_instances": [
    "https://search.ononoki.org",
    "https://searx.oxf.io",
    "https://searx.work"
  ],
  "feishu_index": []
}
```

Optional environment variables (`.env`):

```
FEISHU_APP_ID=xxx         # Feishu Wiki access
FEISHU_APP_SECRET=xxx     # Feishu Wiki access
XCRAWL_API_KEY=xxx        # XCrawl search (paid, free 1000 credits)
```

## Architecture

```
search.py <keyword>
    |
    +-- Concurrent ThreadPool (8 workers)
    |   +-- SearXNG ---- meta search (Google/Bing/...)
    |   +-- DDG -------- DuckDuckGo (fallback)
    |   +-- XCrawl ----- web search (optional, paid)
    |   +-- Wikipedia -- encyclopedia (auto zh/en)
    |   +-- arXiv ------ CS/Physics papers
    |   +-- Scholar ---- Semantic Scholar
    |   +-- CrossRef --- academic metadata
    |   +-- OpenAlex --- academic works
    |   +-- HN --------- Hacker News
    |   +-- GitHub ----- repositories
    |   +-- Reddit ----- discussions
    |   +-- StackOverflow -- Q&A
    |   +-- Archive ---- Internet Archive
    |   +-- Local ------ local files (configurable)
    |   +-- Feishu ----- Feishu Wiki (optional)
    |
    +-- [--deep] Jina Reader reads TOP 3 web pages
```

### Search Modes

| Flag | Engines |
|------|---------|
| (default) | All 15+ engines concurrently |
| `--web` | SearXNG, XCrawl, DuckDuckGo |
| `--academic` | arXiv, Semantic Scholar, CrossRef, OpenAlex, Wikipedia |
| `--tech` | Hacker News, GitHub, Reddit, Stack Overflow |

### Cache Policy

| Rule | Value |
|------|-------|
| Search result cache | 1 hour |
| Web content cache (`--deep`) | 24 hours |
| Max cache size | 50 MB |
| Expired cleanup | Auto-delete on read |
| Overflow cleanup | Oldest-first eviction |

## License

[MIT](LICENSE) (c) 2025 Ming-H
