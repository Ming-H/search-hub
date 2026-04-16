#!/usr/bin/env python3
"""
Search Hub - 免费开源聚合搜索引擎
17 大引擎并发搜索，开箱即用，无需注册

用法:
  python3 search.py <关键词>                          # 全局搜索（所有引擎并发）
  python3 search.py <关键词> --deep                   # + Jina 读取 TOP 网页内容
  python3 search.py <关键词> --web                    # 仅互联网搜索
  python3 search.py <关键词> --academic               # 仅学术搜索
  python3 search.py <关键词> --tech                   # 仅技术社区搜索
  python3 search.py <关键词> --json                   # JSON 格式输出

  # 单引擎
  python3 search.py local <关键词> [--content]        # 本地项目
  python3 search.py feishu search|read|list|refresh   # 飞书知识库
  python3 search.py searxng <关键词>                  # SearXNG 元搜索
  python3 search.py xcrawl <关键词>                   # XCrawl 搜索
  python3 search.py ddg <关键词>                      # DuckDuckGo
  python3 search.py wiki <关键词> [--zh]              # Wikipedia
  python3 search.py arxiv <关键词>                    # arXiv 论文
  python3 search.py hn <关键词>                       # Hacker News
  python3 search.py github <关键词>                   # GitHub 仓库
  python3 search.py reddit <关键词>                   # Reddit 讨论
  python3 search.py stackoverflow <关键词>            # Stack Overflow
  python3 search.py scholar <关键词>                  # Semantic Scholar
  python3 search.py crossref <关键词>                 # CrossRef 学术
  python3 search.py openalex <关键词>                 # OpenAlex 学术
  python3 search.py archive <关键词>                  # Internet Archive
  python3 search.py jina <url>                        # Jina Reader 读取网页
  python3 search.py notebooklm read|ask <url> [问题]  # NotebookLM
  python3 search.py engines                           # 列出所有引擎状态
  python3 search.py cache [clear]                     # 缓存管理
  python3 search.py init                              # 初始化配置文件
"""

import sys
import json
import os
import re
import subprocess
import urllib.request
import urllib.parse
import hashlib
import time
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(SCRIPT_DIR, ".env")
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
CACHE_DIR = os.path.join(SCRIPT_DIR, ".cache")

VERSION = "2.0.0"

DEFAULT_CONFIG = {
    "work_dir": "",
    "local_projects": {},
    "feishu_domain": "",
    "searxng_instances": [
        "https://search.ononoki.org",
        "https://searx.oxf.io",
        "https://search.mdclip.com",
        "https://searx.work",
        "https://priv.au",
        "https://searxng.ch",
        "https://search.bus-hit.me",
        "https://searx.dresden.network",
    ],
    "feishu_index": [],
}


def _get_work_dir(config):
    wd = config.get("work_dir", "")
    if wd:
        return os.path.expanduser(wd)
    return SCRIPT_DIR


def _get_local_projects(config):
    return config.get("local_projects", {})


def _get_feishu_domain(config):
    return config.get("feishu_domain", "")


def _get_searxng_instances(config):
    instances = config.get("searxng_instances", [])
    return instances if instances else DEFAULT_CONFIG["searxng_instances"]


# ─── 通用工具 ───

def load_env():
    env = {}
    if not os.path.exists(ENV_PATH):
        return env
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
            return cfg
    return dict(DEFAULT_CONFIG)


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def http_post(url, headers, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("User-Agent", "SearchHub/1.0")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def http_get_json(url, headers=None, timeout=15):
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "SearchHub/1.0")
    req.add_header("Accept", "application/json")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def http_get_text(url, headers=None, timeout=15):
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "SearchHub/1.0")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode()


def is_chinese(text):
    return any('\u4e00' <= c <= '\u9fff' for c in text)


# ─── 缓存层 ───

def cache_key(prefix, query):
    h = hashlib.md5(query.encode()).hexdigest()
    return f"{prefix}_{h}"


MAX_CACHE_MB = 50
DEFAULT_TTL = 3600


def cache_evict():
    if not os.path.exists(CACHE_DIR):
        return
    now = time.time()
    for f in os.listdir(CACHE_DIR):
        path = os.path.join(CACHE_DIR, f)
        age = now - os.path.getmtime(path)
        if age > DEFAULT_TTL * 2:
            os.remove(path)
    files = [(os.path.getmtime(os.path.join(CACHE_DIR, f)),
              os.path.getsize(os.path.join(CACHE_DIR, f)),
              os.path.join(CACHE_DIR, f))
             for f in os.listdir(CACHE_DIR)]
    total_size = sum(s for _, s, _ in files)
    if total_size > MAX_CACHE_MB * 1024 * 1024:
        files.sort()
        for _, size, path in files:
            os.remove(path)
            total_size -= size
            if total_size <= MAX_CACHE_MB * 1024 * 1024 * 0.8:
                break


def cache_get(prefix, query, ttl=DEFAULT_TTL):
    os.makedirs(CACHE_DIR, exist_ok=True)
    k = cache_key(prefix, query)
    path = os.path.join(CACHE_DIR, k)
    if os.path.exists(path):
        age = time.time() - os.path.getmtime(path)
        if age < ttl:
            with open(path) as f:
                return json.load(f)
        else:
            os.remove(path)
    return None


def cache_set(prefix, query, data):
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_evict()
    k = cache_key(prefix, query)
    path = os.path.join(CACHE_DIR, k)
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False)


def cache_stats():
    if not os.path.exists(CACHE_DIR):
        print("缓存为空")
        return
    files = os.listdir(CACHE_DIR)
    total_size = sum(os.path.getsize(os.path.join(CACHE_DIR, f)) for f in files)
    prefixes = {}
    for f in files:
        p = f.split("_")[0]
        prefixes[p] = prefixes.get(p, 0) + 1
    print(f"缓存文件数: {len(files)}")
    print(f"缓存大小: {total_size / 1024:.1f} KB")
    print(f"按引擎: {dict(prefixes)}")


def cache_clear():
    import shutil
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR)
    print("缓存已清空")


# ─── 飞书引擎 ───

def feishu_api(method, path, token, body=None):
    url = f"https://open.feishu.cn{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def feishu_get_token():
    env = load_env()
    resp = feishu_api("POST", "/open-apis/auth/v3/tenant_access_token/internal", None, {
        "app_id": env["FEISHU_APP_ID"],
        "app_secret": env["FEISHU_APP_SECRET"],
    })
    return resp["tenant_access_token"]


def feishu_get_all_spaces(token):
    spaces, page_token = [], None
    while True:
        path = "/open-apis/wiki/v2/spaces?page_size=50"
        if page_token:
            path += f"&page_token={page_token}"
        resp = feishu_api("GET", path, token)
        spaces.extend(resp["data"].get("items", []))
        if not resp["data"].get("has_more"):
            break
        page_token = resp["data"].get("page_token")
    return spaces


def feishu_get_space_nodes(token, space_id):
    nodes, page_token = [], None
    while True:
        path = f"/open-apis/wiki/v2/spaces/{space_id}/nodes?page_size=50"
        if page_token:
            path += f"&page_token={page_token}"
        resp = feishu_api("GET", path, token)
        nodes.extend(resp["data"].get("items", []))
        if not resp["data"].get("has_more"):
            break
        page_token = resp["data"].get("page_token")
    return nodes


def feishu_read_doc(token, obj_token, obj_type="docx"):
    if obj_type == "docx":
        resp = feishu_api("GET", f"/open-apis/docx/v1/documents/{obj_token}/raw_content", token)
        return resp["data"]["content"]
    elif obj_type == "doc":
        resp = feishu_api("GET", f"/open-apis/doc/v2/{obj_token}/raw_content", token)
        return resp["data"]["content"]
    return f"[不支持的文档类型: {obj_type}]"


def feishu_resolve_node(token, doc_token):
    resp = feishu_api("GET", f"/open-apis/wiki/v2/spaces/get_node?token={doc_token}", token)
    return resp["data"]["node"]


def feishu_build_index(token, config):
    index = []
    for space in feishu_get_all_spaces(token):
        for node in feishu_get_space_nodes(token, space["space_id"]):
            index.append({
                "title": node.get("title", ""),
                "node_token": node["node_token"],
                "obj_token": node["obj_token"],
                "obj_type": node["obj_type"],
                "space_id": space["space_id"],
            })
    config["feishu_index"] = index
    save_config(config)
    return index


def feishu_search(keyword, deep=False):
    token = feishu_get_token()
    config = load_config()
    index = config.get("feishu_index") or feishu_build_index(token, config)
    domain = _get_feishu_domain(config)
    keyword_lower = keyword.lower()
    results = []
    for doc in index:
        url = f"https://{domain}/wiki/{doc['node_token']}" if domain else f"https://feishu.cn/wiki/{doc['node_token']}"
        if keyword_lower in doc["title"].lower():
            results.append({"source": "feishu", "type": "title", "title": doc["title"], "url": url})
        elif deep:
            content = feishu_read_doc(token, doc["obj_token"], doc["obj_type"])
            if keyword_lower in content.lower():
                results.append({"source": "feishu", "type": "content", "title": doc["title"], "url": url})
    return results


def feishu_read(doc_input):
    token = feishu_get_token()
    match = re.search(r'/wiki/([A-Za-z0-9]+)', doc_input)
    doc_token = match.group(1) if match else doc_input
    config = load_config()
    title = next((d["title"] for d in config.get("feishu_index") or []
                  if d["node_token"] == doc_token), "")
    node = feishu_resolve_node(token, doc_token)
    if not title:
        title = node.get("title", doc_token)
    return title, feishu_read_doc(token, node["obj_token"], node["obj_type"])


# ─── 本地引擎 ───

def local_search(keyword, search_content=False):
    config = load_config()
    projects = _get_local_projects(config)
    work_dir = _get_work_dir(config)
    if not projects:
        return []
    keyword_lower = keyword.lower()
    results = []
    for proj_name, proj_info in projects.items():
        proj_path = os.path.join(work_dir, proj_info["path"])
        if not os.path.exists(proj_path):
            continue
        for root, dirs, files in os.walk(proj_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "node_modules" and d != "venv"]
            for fname in files:
                if not fname.endswith((".md", ".txt", ".json")):
                    continue
                fpath = os.path.join(root, fname)
                if keyword_lower in fname.lower():
                    results.append({"source": "local", "type": "filename", "project": proj_name,
                                    "title": fname, "path": os.path.relpath(fpath, work_dir)})
                elif search_content:
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            head = "".join(f.readlines(100))
                            if keyword_lower in head.lower():
                                results.append({"source": "local", "type": "content", "project": proj_name,
                                                "title": fname, "path": os.path.relpath(fpath, work_dir)})
                    except:
                        pass
    return results


# ─── SearXNG 引擎 (元搜索) ───

def searxng_search(keyword, limit=10):
    cached = cache_get("searxng", keyword)
    if cached is not None:
        return cached
    config = load_config()
    instances = _get_searxng_instances(config)
    query = urllib.parse.quote(keyword)
    for instance in instances:
        try:
            url = f"{instance}/search?q={query}&format=json&limit={limit}"
            data = http_get_json(url)
            results = []
            for item in data.get("results", [])[:limit]:
                results.append({
                    "source": "searxng",
                    "type": "web",
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "description": item.get("content", "")
                })
            if results:
                cache_set("searxng", keyword, results)
                return results
        except Exception:
            continue
    return []


# ─── Wikipedia 引擎 ───

def wiki_search(keyword, limit=10, lang=None):
    if lang is None:
        lang = "zh" if is_chinese(keyword) else "en"
    cached = cache_get(f"wiki_{lang}", keyword, ttl=86400)
    if cached is not None:
        return cached
    query = urllib.parse.quote(keyword)
    url = (f"https://{lang}.wikipedia.org/w/api.php?"
           f"action=query&list=search&srsearch={query}&srlimit={limit}&format=json")
    data = http_get_json(url)
    results = []
    for item in data.get("query", {}).get("search", []):
        title = item.get("title", "")
        results.append({
            "source": f"wiki_{lang}",
            "type": "encyclopedia",
            "title": title,
            "url": f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
            "description": re.sub(r'<[^>]+>', '', item.get("snippet", ""))
        })
    cache_set(f"wiki_{lang}", keyword, results)
    return results


# ─── arXiv 引擎 ───

def arxiv_search(keyword, limit=10):
    cached = cache_get("arxiv", keyword, ttl=86400)
    if cached is not None:
        return cached
    query = urllib.parse.quote(keyword)
    url = f"https://export.arxiv.org/api/query?search_query=all:{query}&max_results={limit}&sortBy=submittedDate"
    xml_text = http_get_text(url)
    root = ET.fromstring(xml_text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    results = []
    for entry in root.findall("atom:entry", ns):
        title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")[:200]
        link = ""
        for link_elem in entry.findall("atom:link", ns):
            if link_elem.get("type") == "text/html":
                link = link_elem.get("href")
                break
        if not link:
            link = entry.find("atom:id", ns).text.strip()
        results.append({
            "source": "arxiv",
            "type": "paper",
            "title": title,
            "url": link,
            "description": summary
        })
    cache_set("arxiv", keyword, results)
    return results


# ─── Hacker News 引擎 ───

def hn_search(keyword, limit=10):
    cached = cache_get("hn", keyword)
    if cached is not None:
        return cached
    query = urllib.parse.quote(keyword)
    url = f"https://hn.algolia.com/api/v1/search?query={query}&hitsPerPage={limit}"
    data = http_get_json(url)
    results = []
    for item in data.get("hits", [])[:limit]:
        url_link = item.get("url") or f"https://news.ycombinator.com/item?id={item.get('objectID', '')}"
        points = item.get("points", 0)
        num_comments = item.get("num_comments", 0)
        results.append({
            "source": "hn",
            "type": "discussion",
            "title": item.get("title", ""),
            "url": url_link,
            "description": f"\u2b06 {points} | {item.get('author', '')} | {num_comments} comments"
        })
    cache_set("hn", keyword, results)
    return results


# ─── GitHub 引擎 ───

def github_search(keyword, limit=10):
    cached = cache_get("github", keyword, ttl=1800)
    if cached is not None:
        return cached
    query = urllib.parse.quote(keyword)
    url = f"https://api.github.com/search/repositories?q={query}&per_page={limit}&sort=stars"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "SearchHub/1.0")
    req.add_header("Accept", "application/vnd.github.v3+json")
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    results = []
    for item in data.get("items", []):
        results.append({
            "source": "github",
            "type": "repository",
            "title": item.get("full_name", ""),
            "url": item.get("html_url", ""),
            "description": f"\u2b50 {item.get('stargazers_count', 0)} | {item.get('description', '')[:150]}"
        })
    cache_set("github", keyword, results)
    return results


# ─── Reddit 引擎 ───

def reddit_search(keyword, limit=10):
    cached = cache_get("reddit", keyword)
    if cached is not None:
        return cached
    query = urllib.parse.quote(keyword)
    url = f"https://www.reddit.com/search.json?q={query}&limit={limit}&sort=relevance"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "SearchHub/1.0 bot")
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    results = []
    for child in data.get("data", {}).get("children", []):
        item = child.get("data", {})
        results.append({
            "source": "reddit",
            "type": "discussion",
            "title": item.get("title", ""),
            "url": f"https://www.reddit.com{item.get('permalink', '')}",
            "description": f"\u2b06 {item.get('score', 0)} | r/{item.get('subreddit', '')} | {item.get('num_comments', 0)} comments"
        })
    cache_set("reddit", keyword, results)
    return results


# ─── Stack Overflow 引擎 ───

def stackoverflow_search(keyword, limit=10):
    cached = cache_get("stackoverflow", keyword, ttl=86400)
    if cached is not None:
        return cached
    query = urllib.parse.quote(keyword)
    url = (f"https://api.stackexchange.com/2.3/search/advanced?"
           f"order=desc&sort=relevance&q={query}&site=stackoverflow&pagesize={limit}")
    data = http_get_json(url)
    results = []
    for item in data.get("items", []):
        tags = ", ".join(item.get("tags", [])[:3])
        results.append({
            "source": "stackoverflow",
            "type": "qa",
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "description": f"\u2b06 {item.get('score', 0)} | {item.get('answer_count', 0)} answers | [{tags}]"
        })
    cache_set("stackoverflow", keyword, results)
    return results


# ─── Semantic Scholar 引擎 ───

def scholar_search(keyword, limit=10):
    cached = cache_get("scholar", keyword, ttl=86400)
    if cached is not None:
        return cached
    query = urllib.parse.quote(keyword)
    url = (f"https://api.semanticscholar.org/graph/v1/paper/search?"
           f"query={query}&limit={limit}&fields=title,url,abstract,year,citationCount,authors")
    data = http_get_json(url)
    results = []
    for item in data.get("data", []):
        authors = ", ".join(a.get("name", "") for a in (item.get("authors") or [])[:3])
        abstract = (item.get("abstract") or "")[:150]
        results.append({
            "source": "scholar",
            "type": "paper",
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "description": f"{item.get('year', '')} | {item.get('citationCount', 0)} citations | {authors}\n{abstract}"
        })
    cache_set("scholar", keyword, results)
    return results


# ─── CrossRef 引擎 ───

def crossref_search(keyword, limit=10):
    cached = cache_get("crossref", keyword, ttl=86400)
    if cached is not None:
        return cached
    query = urllib.parse.quote(keyword)
    url = f"https://api.crossref.org/works?query={query}&rows={limit}"
    data = http_get_json(url)
    results = []
    for item in data.get("message", {}).get("items", []):
        title = item.get("title", [""])[0]
        authors = ", ".join(a.get("family", "") for a in item.get("author", [])[:3])
        year = item.get("published-print", item.get("published-online", {})).get("date-parts", [[""]])[0][0]
        results.append({
            "source": "crossref",
            "type": "paper",
            "title": title,
            "url": item.get("URL", ""),
            "description": f"{year} | {authors} | {item.get('container-title', [''])[0]}"
        })
    cache_set("crossref", keyword, results)
    return results


# ─── OpenAlex 引擎 ───

def openalex_search(keyword, limit=10):
    cached = cache_get("openalex", keyword, ttl=86400)
    if cached is not None:
        return cached
    query = urllib.parse.quote(keyword)
    url = f"https://api.openalex.org/works?search={query}&per_page={limit}"
    data = http_get_json(url)
    results = []
    for item in data.get("results", []):
        title = item.get("title", "")
        authors = ", ".join(
            a.get("author", {}).get("display_name", "")
            for a in (item.get("authorships") or [])[:3]
        )
        year = item.get("publication_year", "")
        cited = item.get("cited_by_count", 0)
        results.append({
            "source": "openalex",
            "type": "paper",
            "title": title,
            "url": item.get("doi") or item.get("id", ""),
            "description": f"{year} | {cited} citations | {authors}"
        })
    cache_set("openalex", keyword, results)
    return results


# ─── Internet Archive 引擎 ───

def archive_search(keyword, limit=10):
    cached = cache_get("archive", keyword, ttl=86400)
    if cached is not None:
        return cached
    query = urllib.parse.quote(keyword)
    url = f"https://archive.org/advancedsearch.php?q={query}&output=json&rows={limit}"
    data = http_get_json(url)
    results = []
    docs = data.get("response", {}).get("docs", [])
    for item in docs:
        identifier = item.get("identifier", "")
        title = item.get("title", "")
        if isinstance(title, list):
            title = title[0]
        mediatype = item.get("mediatype", "")
        results.append({
            "source": "archive",
            "type": "archive",
            "title": title,
            "url": f"https://archive.org/details/{identifier}",
            "description": f"[{mediatype}] {item.get('creator', '')} | {item.get('date', '')}"
        })
    cache_set("archive", keyword, results)
    return results


# ─── XCrawl 引擎 ───

def xcrawl_request(endpoint, body):
    env = load_env()
    api_key = env.get("XCRAWL_API_KEY", "")
    if not api_key:
        raise RuntimeError("未配置 XCRAWL_API_KEY")
    return http_post(f"https://run.xcrawl.com/v1/{endpoint}", {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }, body)


def xcrawl_search(keyword, limit=10):
    cached = cache_get("xcrawl", keyword)
    if cached is not None:
        return cached
    resp = xcrawl_request("search", {"query": keyword, "limit": limit})
    results = [{"source": "xcrawl", "type": "web", "title": i.get("title", ""),
                "url": i.get("url", ""), "description": i.get("description", "")}
               for i in resp.get("data", {}).get("data", [])]
    cache_set("xcrawl", keyword, results)
    return results


def xcrawl_scrape(url):
    return xcrawl_request("scrape", {"url": url, "formats": ["markdown"]})


def xcrawl_map(url, limit=100):
    return xcrawl_request("map", {"url": url, "limit": limit})


# ─── DuckDuckGo 引擎 ───

def ddg_search(keyword, limit=10):
    cached = cache_get("ddg", keyword)
    if cached is not None:
        return cached
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            raise RuntimeError("请安装: pip install ddgs")

    results = []
    with DDGS() as d:
        for item in d.text(keyword, max_results=limit):
            results.append({"source": "ddg", "type": "web", "title": item.get("title", ""),
                            "url": item.get("href", ""), "description": item.get("body", "")})
    cache_set("ddg", keyword, results)
    return results


# ─── Jina Reader 引擎 ───

def jina_read(url):
    cached = cache_get("jina", url, ttl=86400)
    if cached is not None:
        return cached
    content = http_get_text(f"https://r.jina.ai/{url}", headers={"Accept": "text/plain"})
    cache_set("jina", url, content)
    return content


# ─── NotebookLM 引擎 ───

def nlm_run(args, input_text=None):
    result = subprocess.run(["nlm"] + args, capture_output=True, text=True,
                            input=input_text, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"nlm error: {result.stderr}")
    return result.stdout


def _nlm_create_temp():
    output = nlm_run(["notebook", "create", "search-hub-temp", "--json"])
    try:
        nb = json.loads(output)
        return nb.get("id", nb.get("notebook_id", ""))
    except:
        match = re.search(r'ID:\s*([a-f0-9-]+)', output)
        return match.group(1) if match else ""


def nlm_read_url(url):
    notebook_id = _nlm_create_temp()
    if not notebook_id:
        raise RuntimeError("无法创建 NotebookLM 笔记本")
    try:
        nlm_run(["source", "add", notebook_id, "--url", url, "--wait"])
        query_result = nlm_run(["notebook", "query", notebook_id, "请完整总结这个页面的所有内容"])
        try:
            return json.loads(query_result)["value"]["answer"]
        except:
            return query_result
    finally:
        try:
            nlm_run(["notebook", "delete", notebook_id])
        except:
            pass


def nlm_ask_url(url, question):
    notebook_id = _nlm_create_temp()
    if not notebook_id:
        raise RuntimeError("无法创建 NotebookLM 笔记本")
    try:
        nlm_run(["source", "add", notebook_id, "--url", url, "--wait"])
        query_result = nlm_run(["notebook", "query", notebook_id, question])
        try:
            return json.loads(query_result)["value"]["answer"]
        except:
            return query_result
    finally:
        try:
            nlm_run(["notebook", "delete", notebook_id])
        except:
            pass


# ─── 组合搜索 ───

ENGINE_LABELS = {
    "local": "本地项目", "feishu": "飞书知识库",
    "searxng": "SearXNG", "xcrawl": "XCrawl", "ddg": "DuckDuckGo",
    "wiki_en": "Wikipedia(en)", "wiki_zh": "Wikipedia(zh)",
    "arxiv": "arXiv", "scholar": "Semantic Scholar", "crossref": "CrossRef", "openalex": "OpenAlex",
    "hn": "Hacker News", "github": "GitHub", "reddit": "Reddit", "stackoverflow": "Stack Overflow",
    "archive": "Internet Archive", "jina": "Jina Reader", "notebooklm": "NotebookLM",
}

WEB_ENGINES = ["searxng", "xcrawl", "ddg"]
ACADEMIC_ENGINES = ["arxiv", "scholar", "crossref", "openalex", "wiki"]
TECH_ENGINES = ["hn", "github", "reddit", "stackoverflow"]


def _run_engine(name, keyword):
    """安全执行单个引擎搜索，返回 (name, results, error)"""
    try:
        if name == "local":
            return name, local_search(keyword, search_content=True), None
        elif name == "feishu":
            return name, feishu_search(keyword), None
        elif name == "searxng":
            return name, searxng_search(keyword), None
        elif name == "xcrawl":
            return name, xcrawl_search(keyword, limit=5), None
        elif name == "ddg":
            return name, ddg_search(keyword, limit=5), None
        elif name == "wiki":
            return name, wiki_search(keyword), None
        elif name == "arxiv":
            return name, arxiv_search(keyword), None
        elif name == "scholar":
            return name, scholar_search(keyword), None
        elif name == "crossref":
            return name, crossref_search(keyword), None
        elif name == "openalex":
            return name, openalex_search(keyword), None
        elif name == "hn":
            return name, hn_search(keyword), None
        elif name == "github":
            return name, github_search(keyword), None
        elif name == "reddit":
            return name, reddit_search(keyword), None
        elif name == "stackoverflow":
            return name, stackoverflow_search(keyword), None
        elif name == "archive":
            return name, archive_search(keyword), None
    except Exception as e:
        return name, [], str(e)


def deep_read(keyword, web_results):
    """对搜索结果中的 TOP 链接用 Jina 读取内容摘要"""
    enriched = []
    for item in web_results[:3]:
        url = item.get("url", "")
        if not url:
            continue
        try:
            content = jina_read(url)
            lines = [l for l in content.split("\n") if l.strip()
                     and not l.startswith("Title:") and not l.startswith("URL Source:")]
            summary = "\n".join(lines[:10])[:500]
            item["deep_summary"] = summary
            enriched.append(item)
        except:
            pass
    return enriched


def unified_search(keyword, deep=False, mode="all", json_output=False):
    """并发搜索多引擎
    mode: all / web / academic / tech
    json_output: return JSON instead of printing
    """
    if mode == "web":
        engines = WEB_ENGINES
    elif mode == "academic":
        engines = ACADEMIC_ENGINES
    elif mode == "tech":
        engines = TECH_ENGINES
    else:
        engines = ["local", "feishu"] + WEB_ENGINES + ACADEMIC_ENGINES + TECH_ENGINES

    all_results = []
    web_results = []
    errors = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_run_engine, name, keyword): name for name in engines}
        for future in as_completed(futures):
            name, results, error = future.result()
            label = ENGINE_LABELS.get(name, name)
            if error:
                print(f"  \u2717 {label}: {error}", file=sys.stderr)
                errors.append((name, error))
            elif results:
                print(f"  \u2713 {label}: {len(results)} 个结果", file=sys.stderr)
                all_results.extend(results)
                if name in WEB_ENGINES:
                    web_results.extend(results)
            else:
                print(f"  - {label}: 无结果", file=sys.stderr)

    # --deep: 读取 TOP 网页内容
    if deep and web_results:
        print(f"  \u2022 Jina Reader 读取 TOP 网页...", file=sys.stderr)
        enriched = deep_read(keyword, web_results)
        for item in enriched:
            for r in all_results:
                if r.get("url") == item["url"] and r["source"] == item["source"]:
                    r["deep_summary"] = item["deep_summary"]

    if json_output:
        print(json.dumps(all_results, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'='*60}")
        print(f"  「{keyword}」共 {len(all_results)} 个匹配")
        print(f"{'='*60}")
        print_results(all_results, keyword)


# ─── 输出 ───

def print_results(results, keyword):
    if not results:
        print(f"  未找到与「{keyword}」相关的内容")
        return

    by_source = {}
    for r in results:
        by_source.setdefault(r["source"], []).append(r)

    for source, items in by_source.items():
        label = ENGINE_LABELS.get(source, source)
        print(f"\n  [{label}] {len(items)} 个结果：")
        for item in items:
            if source == "local":
                tag = "[文件名]" if item.get("type") == "filename" else "[内容]"
                print(f"    {tag} {item['title']}")
                print(f"         {item['project']} | {item['path']}")
            elif source == "feishu":
                print(f"    {item['title']}")
                print(f"         {item['url']}")
            else:
                print(f"    {item['title']}")
                print(f"         {item['url']}")
                if item.get("description"):
                    desc = item['description'][:150].replace('\n', ' ')
                    print(f"         {desc}")
                if item.get("deep_summary"):
                    summary = item['deep_summary'][:150].replace('\n', ' ')
                    print(f"         \U0001f4c4 {summary}...")
        print()


def list_engines():
    env = load_env()
    print("可用搜索引擎：\n")
    engines = [
        ("local",        "本地项目搜索",     True, "免费"),
        ("feishu",       "飞书知识库",       bool(env.get("FEISHU_APP_ID")), "需配置 App"),
        ("searxng",      "SearXNG 元搜索",   True, "免费"),
        ("xcrawl",       "XCrawl 搜索",      bool(env.get("XCRAWL_API_KEY")), "付费，需 Key"),
        ("ddg",          "DuckDuckGo",       True, "免费，需 ddgs 包"),
        ("wiki",         "Wikipedia",         True, "免费"),
        ("arxiv",        "arXiv 论文",        True, "免费"),
        ("hn",           "Hacker News",       True, "免费"),
        ("github",       "GitHub 仓库",       True, "免费"),
        ("reddit",       "Reddit 讨论",       True, "免费"),
        ("stackoverflow","Stack Overflow",    True, "免费"),
        ("scholar",      "Semantic Scholar",  True, "免费"),
        ("crossref",     "CrossRef 学术",     True, "免费"),
        ("openalex",     "OpenAlex 学术",     True, "免费"),
        ("archive",      "Internet Archive",  True, "免费"),
        ("jina",         "Jina Reader",       True, "免费"),
        ("notebooklm",   "NotebookLM",        True, "免费，需 nlm CLI"),
    ]
    ready = 0
    for name, desc, available, cost in engines:
        status = "\u2713" if available else "\u2717"
        print(f"  {status} {name:15s} {desc:20s} [{cost}]")
        if available:
            ready += 1
    print(f"\n  共 {len(engines)} 个引擎，{ready} 个就绪")


# ─── CLI 入口 ───

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    # ─── 全局搜索 ───
    single_engines = ("feishu", "local", "searxng", "xcrawl", "ddg",
                      "wiki", "arxiv", "hn", "github", "reddit", "stackoverflow",
                      "scholar", "crossref", "openalex", "archive",
                      "jina", "notebooklm", "cache", "engines", "init", "help")

    if cmd not in single_engines:
        mode = "all"
        deep = False
        json_output = False
        if "--web" in args:
            mode = "web"
            args.remove("--web")
        if "--academic" in args:
            mode = "academic"
            args.remove("--academic")
        if "--tech" in args:
            mode = "tech"
            args.remove("--tech")
        if "--deep" in args:
            deep = True
            args.remove("--deep")
        if "--json" in args:
            json_output = True
            args.remove("--json")
        unified_search(cmd, deep=deep, mode=mode, json_output=json_output)
        return

    # ─── 飞书 ───
    if cmd == "feishu":
        if not args:
            print("用法: search.py feishu <search|read|list|refresh> [args]")
            return
        sub = args[0]
        if sub == "search" and len(args) >= 2:
            print_results(feishu_search(args[1], "--deep" in args), args[1])
        elif sub == "read" and len(args) >= 2:
            title, content = feishu_read(args[1])
            print(f"# {title}\n\n{content}")
        elif sub == "list":
            token = feishu_get_token()
            index = load_config().get("feishu_index") or feishu_build_index(token, load_config())
            for i, doc in enumerate(index):
                print(f"  {i+1}. {doc['title']}")
            print(f"\n共 {len(index)} 个文档")
        elif sub == "refresh":
            feishu_build_index(feishu_get_token(), load_config())
            print("飞书索引已更新")

    # ─── 本地 ───
    elif cmd == "local":
        if not args:
            print("用法: search.py local <关键词> [--content]")
            return
        print_results(local_search(args[0], "--content" in args), args[0])

    # ─── SearXNG ───
    elif cmd == "searxng":
        if not args:
            print("用法: search.py searxng <关键词>")
            return
        try:
            print_results(searxng_search(args[0]), args[0])
        except Exception as e:
            print(f"  SearXNG 搜索失败: {e}")

    # ─── Wikipedia ───
    elif cmd == "wiki":
        if not args:
            print("用法: search.py wiki <关键词> [--zh]")
            return
        lang = "zh" if "--zh" in args else None
        print_results(wiki_search(args[0], lang=lang), args[0])

    # ─── arXiv ───
    elif cmd == "arxiv":
        if not args:
            print("用法: search.py arxiv <关键词>")
            return
        try:
            print_results(arxiv_search(args[0]), args[0])
        except Exception as e:
            print(f"  arXiv 搜索失败: {e}")

    # ─── Hacker News ───
    elif cmd == "hn":
        if not args:
            print("用法: search.py hn <关键词>")
            return
        print_results(hn_search(args[0]), args[0])

    # ─── GitHub ───
    elif cmd == "github":
        if not args:
            print("用法: search.py github <关键词>")
            return
        print_results(github_search(args[0]), args[0])

    # ─── Reddit ───
    elif cmd == "reddit":
        if not args:
            print("用法: search.py reddit <关键词>")
            return
        try:
            print_results(reddit_search(args[0]), args[0])
        except Exception as e:
            print(f"  Reddit 搜索失败: {e}")

    # ─── Stack Overflow ───
    elif cmd == "stackoverflow":
        if not args:
            print("用法: search.py stackoverflow <关键词>")
            return
        print_results(stackoverflow_search(args[0]), args[0])

    # ─── Semantic Scholar ───
    elif cmd == "scholar":
        if not args:
            print("用法: search.py scholar <关键词>")
            return
        try:
            print_results(scholar_search(args[0]), args[0])
        except Exception as e:
            print(f"  Semantic Scholar 搜索失败: {e}")

    # ─── CrossRef ───
    elif cmd == "crossref":
        if not args:
            print("用法: search.py crossref <关键词>")
            return
        print_results(crossref_search(args[0]), args[0])

    # ─── OpenAlex ───
    elif cmd == "openalex":
        if not args:
            print("用法: search.py openalex <关键词>")
            return
        print_results(openalex_search(args[0]), args[0])

    # ─── Internet Archive ───
    elif cmd == "archive":
        if not args:
            print("用法: search.py archive <关键词>")
            return
        print_results(archive_search(args[0]), args[0])

    # ─── XCrawl ───
    elif cmd == "xcrawl":
        if not args:
            print("用法: search.py xcrawl <关键词|scrape|map> [args]")
            return
        sub = args[0]
        if sub == "scrape" and len(args) >= 2:
            result = xcrawl_scrape(args[1])
            data = result.get("data", {})
            print(data.get("markdown", json.dumps(data, ensure_ascii=False, indent=2)))
        elif sub == "map" and len(args) >= 2:
            result = xcrawl_map(args[1], int(args[2]) if len(args) >= 3 else 100)
            links = result.get("data", {}).get("links", [])
            for link in links:
                print(f"  {link}")
            print(f"\n共 {len(links)} 个 URL")
        else:
            limit = int(args[1]) if len(args) >= 2 and args[1].isdigit() else 10
            print_results(xcrawl_search(sub, limit), sub)

    # ─── DuckDuckGo ───
    elif cmd == "ddg":
        if not args:
            print("用法: search.py ddg <关键词>")
            return
        print_results(ddg_search(args[0]), args[0])

    # ─── Jina Reader ───
    elif cmd == "jina":
        if not args:
            print("用法: search.py jina <url>")
            return
        print(jina_read(args[0]))

    # ─── NotebookLM ───
    elif cmd == "notebooklm":
        if not args:
            print("用法: search.py notebooklm <read|ask> <url> [问题]")
            return
        sub = args[0]
        if sub == "read" and len(args) >= 2:
            print(nlm_read_url(args[1]))
        elif sub == "ask" and len(args) >= 3:
            print(nlm_ask_url(args[1], args[2]))
        else:
            print("用法: search.py notebooklm <read|ask> <url> [问题]")

    # ─── 缓存 ───
    elif cmd == "cache":
        if args and args[0] == "clear":
            cache_clear()
        else:
            cache_stats()

    # ─── 引擎列表 ───
    elif cmd == "engines":
        list_engines()

    # ─── 初始化配置 ───
    elif cmd == "init":
        if os.path.exists(CONFIG_PATH):
            print(f"  配置文件已存在: {CONFIG_PATH}")
            return
        save_config(dict(DEFAULT_CONFIG))
        print(f"  已创建配置文件: {CONFIG_PATH}")
        print(f"  请编辑 config.json 添加本地项目目录和飞书域名（可选）")
        if not os.path.exists(ENV_PATH):
            with open(ENV_PATH, "w") as f:
                f.write("# Search Hub 环境变量（可选）\n")
                f.write("# FEISHU_APP_ID=\n")
                f.write("# FEISHU_APP_SECRET=\n")
                f.write("# XCRAWL_API_KEY=\n")
            print(f"  已创建环境变量模板: {ENV_PATH}")

    elif cmd == "help":
        print(__doc__)


if __name__ == "__main__":
    main()
