---
name: search-hub
description: Free open-source aggregated search engine CLI with 17 engines. Zero config needed — 12 engines work out of the box. Triggers on "search", "搜索", "查找", "scrape", "read url", or any multi-source information gathering need.
---

# Search Hub

17-engine aggregated search CLI. 12 engines work with zero config.

## Quick Search

```bash
python3 search.py <keyword>              # All engines concurrent
python3 search.py <keyword> --web        # Web only (SearXNG, DDG, XCrawl)
python3 search.py <keyword> --academic   # Academic only (arXiv, Scholar, CrossRef, OpenAlex, Wiki)
python3 search.py <keyword> --tech       # Tech only (HN, GitHub, Reddit, StackOverflow)
python3 search.py <keyword> --deep       # + Jina reads top 3 web pages
python3 search.py <keyword> --json       # JSON output (progress → stderr, JSON → stdout)
```

## Engines

| Engine | Command | Zero Config | Category |
|--------|---------|:-----------:|----------|
| SearXNG | `searxng` | Yes | Web (meta-search: Google/Bing/...) |
| DuckDuckGo | `ddg` | Yes (needs ddgs) | Web |
| XCrawl | `xcrawl` | No (paid key) | Web |
| Wikipedia | `wiki [--zh]` | Yes | Knowledge (auto zh/en) |
| arXiv | `arxiv` | Yes | Academic |
| Semantic Scholar | `scholar` | Yes | Academic |
| CrossRef | `crossref` | Yes | Academic |
| OpenAlex | `openalex` | Yes | Academic |
| Hacker News | `hn` | Yes | Tech |
| GitHub | `github` | Yes | Tech |
| Reddit | `reddit` | Yes | Tech |
| Stack Overflow | `stackoverflow` | Yes | Tech |
| Internet Archive | `archive` | Yes | Media |
| Jina Reader | `jina <url>` | Yes | Tool (URL → Markdown) |
| NotebookLM | `notebooklm` | Yes (needs nlm) | Tool (AI Q&A) |
| Feishu Wiki | `feishu` | No (app creds) | Knowledge |
| Local Files | `local` | No (config) | Knowledge |

## How to Use This Skill

1. When the user asks to search, run: `python3 search.py <keyword>`
2. For general web search: `--web`
3. For papers/academic: `--academic`
4. For code/tech discussions: `--tech`
5. To read any URL as text: `python3 search.py jina <url>`
6. To get JSON for piping: add `--json`
7. Check engine status: `python3 search.py engines`
8. First-time setup: `python3 search.py init`

## Cache

- Search results: 1 hour | Academic/wiki: 24 hours | Max: 50 MB
- Manage: `python3 search.py cache` or `cache clear`
