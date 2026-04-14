#!/usr/bin/env python3
"""
Search Hub - 个人专业搜索引擎
6 大引擎：本地 / 飞书 / XCrawl / DuckDuckGo / Jina Reader / NotebookLM

用法:
  python3 search.py <关键词>                          # 全局搜索（本地+飞书+XCrawl+DDG）
  python3 search.py <关键词> --deep                   # 全局搜索 + Jina读取TOP网页内容
  python3 search.py feishu <关键词>                   # 搜索飞书知识库
  python3 search.py feishu <关键词> --deep            # 搜索飞书文档内容
  python3 search.py feishu read <链接或token>         # 读取飞书文档
  python3 search.py feishu list                       # 列出飞书文档
  python3 search.py feishu refresh                    # 更新飞书索引
  python3 search.py local <关键词>                    # 搜索本地项目
  python3 search.py local <关键词> --content          # 搜索文件内容
  python3 search.py xcrawl <关键词>                   # XCrawl 互联网搜索
  python3 search.py xcrawl scrape <url>               # XCrawl 抓取网页
  python3 search.py xcrawl map <url>                  # XCrawl 站点地图
  python3 search.py ddg <关键词>                      # DuckDuckGo 搜索
  python3 search.py jina <url>                        # Jina Reader 读取网页
  python3 search.py notebooklm read <url>             # NotebookLM 读取URL
  python3 search.py notebooklm ask <url> <问题>        # NotebookLM 问答
  python3 search.py cache                             # 查看缓存统计
  python3 search.py cache clear                       # 清空缓存
"""

import sys
import json
import os
import re
import subprocess
import urllib.request
import hashlib
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(SCRIPT_DIR, ".env")
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
CACHE_DIR = os.path.join(SCRIPT_DIR, ".cache")
WORK_DIR = os.path.dirname(SCRIPT_DIR)

LOCAL_PROJECTS = {
    "content-forge-ai": {"path": "content-forge-ai/data", "desc": "AI内容工厂数据"},
    "ai-insights": {"path": "ai-insights/content", "desc": "AI深度分析博客"},
    "yinxiang": {"path": "yinxiang-migration/obsidian-vault-from-yinxiang", "desc": "印象笔记迁移"},
    "personal-wiki": {"path": "personal-wiki/wiki", "desc": "个人Wiki"},
    "devfox-pulse": {"path": "devfox-pulse/output", "desc": "DevFox发布内容"},
    "devfox-vision": {"path": "devfox-vision/prompt_libs", "desc": "AI提示词库"},
}


# ─── 通用工具 ───

def load_env():
    env = {}
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
            return json.load(f)
    return {}


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


def http_get_text(url, headers=None, timeout=15):
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "SearchHub/1.0")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode()


# ─── 缓存层 ───

def cache_key(prefix, query):
    h = hashlib.md5(query.encode()).hexdigest()
    return f"{prefix}_{h}"


MAX_CACHE_MB = 50  # 最大缓存 50MB
DEFAULT_TTL = 3600  # 默认 1 小时过期


def cache_evict():
    """清理过期文件和超出大小限制的旧文件"""
    if not os.path.exists(CACHE_DIR):
        return
    now = time.time()
    # 1. 删除过期文件
    for f in os.listdir(CACHE_DIR):
        path = os.path.join(CACHE_DIR, f)
        age = now - os.path.getmtime(path)
        if age > DEFAULT_TTL * 2:  # 超过 2 小时的一律删除
            os.remove(path)
    # 2. 如果还是超大小限制，按时间从旧到新删除
    files = [(os.path.getmtime(os.path.join(CACHE_DIR, f)),
              os.path.getsize(os.path.join(CACHE_DIR, f)),
              os.path.join(CACHE_DIR, f))
             for f in os.listdir(CACHE_DIR)]
    total_size = sum(s for _, s, _ in files)
    if total_size > MAX_CACHE_MB * 1024 * 1024:
        files.sort()  # 按时间排序，最旧的在前
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
            os.remove(path)  # 过期直接删除
    return None


def cache_set(prefix, query, data):
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_evict()  # 写入前先清理
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
    keyword_lower = keyword.lower()
    results = []
    for doc in index:
        if keyword_lower in doc["title"].lower():
            results.append({"source": "feishu", "type": "title", "title": doc["title"],
                            "url": f"https://yunyinghui.feishu.cn/wiki/{doc['node_token']}"})
        elif deep:
            content = feishu_read_doc(token, doc["obj_token"], doc["obj_type"])
            if keyword_lower in content.lower():
                results.append({"source": "feishu", "type": "content", "title": doc["title"],
                                "url": f"https://yunyinghui.feishu.cn/wiki/{doc['node_token']}"})
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
    keyword_lower = keyword.lower()
    results = []
    for proj_name, proj_info in LOCAL_PROJECTS.items():
        proj_path = os.path.join(WORK_DIR, proj_info["path"])
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
                                    "title": fname, "path": os.path.relpath(fpath, WORK_DIR)})
                elif search_content:
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                            head = "".join(f.readlines(100))
                            if keyword_lower in head.lower():
                                results.append({"source": "local", "type": "content", "project": proj_name,
                                                "title": fname, "path": os.path.relpath(fpath, WORK_DIR)})
                    except:
                        pass
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
    cached = cache_get("jina", url, ttl=86400)  # 网页内容缓存 24 小时
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

def deep_read(keyword, web_results):
    """对搜索结果中的 TOP 链接用 Jina 读取内容摘要"""
    enriched = []
    for item in web_results[:3]:
        url = item.get("url", "")
        if not url:
            continue
        try:
            content = jina_read(url)
            # 提取前 300 字符作为摘要
            lines = [l for l in content.split("\n") if l.strip() and not l.startswith("Title:") and not l.startswith("URL Source:")]
            summary = "\n".join(lines[:10])[:500]
            item["deep_summary"] = summary
            enriched.append(item)
        except:
            pass
    return enriched


# ─── 统一入口 ───

def print_results(results, keyword):
    if not results:
        print(f"  未找到与「{keyword}」相关的内容")
        return

    by_source = {}
    for r in results:
        by_source.setdefault(r["source"], []).append(r)

    labels = {"feishu": "飞书知识库", "local": "本地项目", "xcrawl": "XCrawl",
              "ddg": "DuckDuckGo", "jina": "Jina Reader", "notebooklm": "NotebookLM"}
    for source, items in by_source.items():
        print(f"\n  [{labels.get(source, source)}] {len(items)} 个结果：")
        for item in items:
            if source == "local":
                tag = "[文件名]" if item.get("type") == "filename" else "[内容]"
                print(f"    {tag} {item['title']}")
                print(f"         {item['project']} | {item['path']}")
            elif source == "feishu":
                print(f"    {item['title']}")
                print(f"         {item['url']}")
            elif source in ("xcrawl", "ddg"):
                print(f"    {item['title']}")
                print(f"         {item['url']}")
                if item.get("description"):
                    print(f"         {item['description'][:120].replace(chr(10),' ')}")
                if item.get("deep_summary"):
                    print(f"         📄 {item['deep_summary'][:150].replace(chr(10),' ')}...")
            elif source == "notebooklm":
                print(f"    {item.get('answer', '')[:200]}")
        print()


def unified_search(keyword, deep=False):
    all_results = []

    print(f"🔍 本地项目...")
    all_results.extend(local_search(keyword, search_content=True))

    print(f"🔍 飞书知识库...")
    try:
        all_results.extend(feishu_search(keyword))
    except Exception as e:
        print(f"  ✗ 飞书: {e}")

    print(f"🔍 互联网 (XCrawl)...")
    web_results = []
    try:
        web_results = xcrawl_search(keyword, limit=5)
        all_results.extend(web_results)
    except Exception as e:
        print(f"  ✗ XCrawl: {e}")

    # XCrawl 失败时自动降级到 DuckDuckGo
    if not web_results:
        print(f"🔍 互联网 (DuckDuckGo 备选)...")
        try:
            web_results = ddg_search(keyword, limit=5)
            all_results.extend(web_results)
        except Exception as e:
            print(f"  ✗ DuckDuckGo: {e}")

    # --deep: 读取 TOP 网页内容
    if deep and web_results:
        print(f"🔍 深度读取 TOP 网页 (Jina Reader)...")
        enriched = deep_read(keyword, web_results)
        for item in enriched:
            for r in all_results:
                if r.get("url") == item["url"] and r["source"] == item["source"]:
                    r["deep_summary"] = item["deep_summary"]

    print(f"\n{'='*60}")
    print(f"  「{keyword}」共 {len(all_results)} 个匹配")
    print(f"{'='*60}")
    print_results(all_results, keyword)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    # ─── 全局搜索 ───
    if cmd not in ("feishu", "local", "xcrawl", "ddg", "jina", "notebooklm", "cache", "help"):
        unified_search(cmd, deep=("--deep" in sys.argv))
        return

    # ─── 飞书 ───
    if cmd == "feishu":
        if len(sys.argv) < 3:
            print("用法: search.py feishu <search|read|list|refresh> [args]")
            return
        sub = sys.argv[2]
        if sub == "search" and len(sys.argv) >= 4:
            print_results(feishu_search(sys.argv[3], "--deep" in sys.argv), sys.argv[3])
        elif sub == "read" and len(sys.argv) >= 4:
            title, content = feishu_read(sys.argv[3])
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
        if len(sys.argv) < 3:
            print("用法: search.py local <关键词> [--content]")
            return
        print_results(local_search(sys.argv[2], "--content" in sys.argv), sys.argv[2])

    # ─── XCrawl ───
    elif cmd == "xcrawl":
        if len(sys.argv) < 3:
            print("用法: search.py xcrawl <关键词|scrape|map> [args]")
            return
        sub = sys.argv[2]
        if sub == "scrape" and len(sys.argv) >= 4:
            result = xcrawl_scrape(sys.argv[3])
            data = result.get("data", {})
            print(data.get("markdown", json.dumps(data, ensure_ascii=False, indent=2)))
        elif sub == "map" and len(sys.argv) >= 4:
            result = xcrawl_map(sys.argv[3], int(sys.argv[4]) if len(sys.argv) >= 5 else 100)
            links = result.get("data", {}).get("links", [])
            for link in links:
                print(f"  {link}")
            print(f"\n共 {len(links)} 个 URL")
        else:
            limit = int(sys.argv[3]) if len(sys.argv) >= 4 and sys.argv[3].isdigit() else 10
            print_results(xcrawl_search(sub, limit), sub)

    # ─── DuckDuckGo ───
    elif cmd == "ddg":
        if len(sys.argv) < 3:
            print("用法: search.py ddg <关键词>")
            return
        print_results(ddg_search(sys.argv[2]), sys.argv[2])

    # ─── Jina Reader ───
    elif cmd == "jina":
        if len(sys.argv) < 3:
            print("用法: search.py jina <url>")
            return
        print(jina_read(sys.argv[2]))

    # ─── NotebookLM ───
    elif cmd == "notebooklm":
        if len(sys.argv) < 3:
            print("用法: search.py notebooklm <read|ask> [args]")
            return
        sub = sys.argv[2]
        if sub == "read" and len(sys.argv) >= 4:
            print(nlm_read_url(sys.argv[3]))
        elif sub == "ask" and len(sys.argv) >= 5:
            print(nlm_ask_url(sys.argv[3], sys.argv[4]))
        else:
            print("用法: search.py notebooklm <read|ask> <url> [问题]")

    # ─── 缓存 ───
    elif cmd == "cache":
        if len(sys.argv) >= 3 and sys.argv[2] == "clear":
            cache_clear()
        else:
            cache_stats()

    elif cmd == "help":
        print(__doc__)


if __name__ == "__main__":
    main()
