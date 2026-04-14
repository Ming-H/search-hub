# Search Hub

**[English](README.md)** | 中文

个人专业搜索引擎，整合 6 大搜索渠道，一条命令搜遍所有知识源。

## 引擎

| 引擎 | 用途 | 成本 | 说明 |
|------|------|------|------|
| **local** | 本地项目搜索 | 免费 | 扫描 1300+ 篇本地文档，匹配文件名和内容 |
| **feishu** | 飞书知识库 | 免费 | 通过飞书开放平台 API 读取文档 |
| **xcrawl** | 互联网搜索 | 积分 | 主力搜索引擎，支持搜索/抓取/站点地图 |
| **ddg** | DuckDuckGo | 免费 | XCrawl 失败时自动降级的备选引擎 |
| **jina** | 网页读取 | 免费 | 将任意 URL 转为 Markdown |
| **notebooklm** | 深度问答 | 免费 | 基于网页内容的 AI 深度问答 |

## 快速开始

### 前置依赖

```bash
pip install ddgs
uv tool install notebooklm-mcp-cli && nlm login
```

### 配置

编辑 `.env` 文件：

```
FEISHU_APP_ID=your_app_id
FEISHU_APP_SECRET=your_app_secret
XCRAWL_API_KEY=your_xcrawl_key
```

飞书应用需要开通 `wiki:wiki:readonly` 和 `docx:document:readonly` 权限。XCrawl 在 [dash.xcrawl.com](https://dash.xcrawl.com/) 注册，免费 1000 积分。

### 飞书应用权限

需要在飞书开放平台开通：
- `wiki:wiki:readonly` — 读取知识库
- `docx:document:readonly` — 读取文档内容
- 将应用添加为知识库空间的协作者

### 初始化飞书索引

```bash
python3 search.py feishu refresh
```

## 用法

### 全局搜索（推荐）

```bash
python3 search.py <关键词>          # 本地 + 飞书 + XCrawl
python3 search.py <关键词> --deep   # 额外用 Jina 读取 TOP 网页内容
```

### 单引擎搜索

```bash
# 本地
python3 search.py local <关键词>
python3 search.py local <关键词> --content

# 飞书
python3 search.py feishu search <关键词>
python3 search.py feishu search <关键词> --deep
python3 search.py feishu read <wiki链接或token>
python3 search.py feishu list
python3 search.py feishu refresh

# XCrawl
python3 search.py xcrawl <关键词>
python3 search.py xcrawl <关键词> 20          # 指定结果数
python3 search.py xcrawl scrape <url>         # 抓取网页
python3 search.py xcrawl map <url>            # 站点地图
python3 search.py xcrawl map <url> 200        # 限制 URL 数

# DuckDuckGo
python3 search.py ddg <关键词>

# Jina Reader
python3 search.py jina <url>

# NotebookLM
python3 search.py notebooklm read <url>
python3 search.py notebooklm ask <url> "问题"
```

### 缓存管理

```bash
python3 search.py cache          # 查看缓存统计
python3 search.py cache clear    # 清空缓存
```

## 架构

```
search.py <关键词>
    │
    ├─ 1. local ──── 扫描本地 6 个项目的 .md/.txt/.json
    │
    ├─ 2. feishu ─── 匹配飞书知识库索引
    │
    ├─ 3. xcrawl ─── 互联网搜索（主力）
    │     └─ 失败自动降级 → ddg（免费备选）
    │
    └─ 4. [--deep] ── jina 读取 TOP 3 结果的网页内容
```

### 降级策略

```
XCrawl 失败/超时 → 自动切换 DuckDuckGo
```

### 缓存机制

| 规则 | 值 |
|------|------|
| 搜索结果缓存 | 1 小时 |
| Jina 网页内容缓存 | 24 小时 |
| 最大缓存空间 | 50 MB |
| 过期清理 | 读取时自动删除过期文件 |
| 超限清理 | 写入前清理，按最旧优先删除 |

## 本地搜索覆盖的项目

| 项目 | 路径 | 内容 |
|------|------|------|
| content-forge-ai | data/ | AI 日报 + 技术系列（711 篇） |
| ai-insights | content/ | Hugo 博客（411 篇） |
| yinxiang-migration | obsidian-vault | 印象笔记迁移（189 篇） |
| personal-wiki | wiki/ | 个人知识库 |
| devfox-pulse | output/ | 发布内容 |
| devfox-vision | prompt_libs/ | AI 提示词库 |

## 文件结构

```
search-hub/
├── .env           # API 凭证（飞书 + XCrawl）
├── .cache/        # 自动缓存目录
├── config.json    # 飞书知识库索引
└── search.py      # 唯一入口
```

## 示例

```bash
# 搜一个技术话题
$ python3 search.py "AI Agent"
🔍 本地项目...
🔍 飞书知识库...
🔍 互联网 (XCrawl)...
==================================================
  「AI Agent」共 70 个匹配
==================================================

  [本地项目] 65 个结果：
    ...

  [XCrawl] 5 个结果：
    ...

# 读取飞书文档
$ python3 search.py feishu read MBiJwF5QhiwAvQk0c8LckGZOnec
# HappyHorse 学习手册
# ...

# 用 NotebookLM 对网页提问
$ python3 search.py notebooklm ask https://example.com "这个产品的核心竞争力是什么"
```
