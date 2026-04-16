# Search Hub

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-2.0.0-green.svg)](https://github.com/Ming-H/search-hub)

免费开源聚合搜索引擎 CLI。一条命令并发搜索 17 个引擎，其中 12 个开箱即用、无需任何配置。

**[English](README.md)** | 中文

## 特性

- **17 个搜索引擎** 聚合为一条命令
- **12 个引擎开箱即用** -- 零配置、无需 API Key
- **并发执行** ThreadPoolExecutor（8 线程）
- **4 种搜索模式**：`all`、`--web`、`--academic`、`--tech`
- **`--deep` 模式** 通过 Jina Reader 读取 TOP 网页全文
- **`--json` 输出** 机器可读的 JSON 格式
- **内置缓存**（搜索 1 小时、网页 24 小时、上限 50 MB）
- **自动中文检测** Wikipedia 自动切换中/英文
- **单文件** 无外部依赖（DuckDuckGo 可选安装 `ddgs`）

## 引擎一览

| 引擎 | 类别 | 费用 | 配置 | 说明 |
|------|------|------|------|------|
| SearXNG | 网页 | 免费 | 零配置 | 元搜索（Google、Bing 等） |
| DuckDuckGo | 网页 | 免费 | 可选 `ddgs` | 隐私优先的网页搜索 |
| Wikipedia | 网页 | 免费 | 零配置 | 百科全书（自动中/英文） |
| arXiv | 学术 | 免费 | 零配置 | CS / 物理预印本 |
| Semantic Scholar | 学术 | 免费 | 零配置 | AI 侧重的论文搜索 |
| CrossRef | 学术 | 免费 | 零配置 | 学术 DOI 元数据 |
| OpenAlex | 学术 | 免费 | 零配置 | 开放学术作品目录 |
| Hacker News | 技术 | 免费 | 零配置 | 技术新闻与讨论 |
| GitHub | 技术 | 免费 | 零配置 | 代码仓库 |
| Reddit | 技术 | 免费 | 零配置 | 社区讨论 |
| Stack Overflow | 技术 | 免费 | 零配置 | 编程问答 |
| Internet Archive | 网页 | 免费 | 零配置 | 数字图书馆 |
| Jina Reader | 工具 | 免费 | 零配置 | 读取任意 URL 为 Markdown |
| NotebookLM | 工具 | 免费 | 需 `nlm` CLI | 网页 AI 深度问答 |
| XCrawl | 网页 | 付费 | API Key | 高级搜索与抓取 |
| Feishu Wiki | 本地 | 免费 | 应用凭证 | 飞书知识库文档 |
| Local files | 本地 | 免费 | `config.json` | 本地项目文件搜索 |

**12 个引擎无需配置即可使用**：SearXNG、DDG、Wikipedia、arXiv、Hacker News、GitHub、Reddit、Stack Overflow、Semantic Scholar、CrossRef、OpenAlex、Internet Archive。

## 快速开始

```bash
git clone https://github.com/Ming-H/search-hub.git
cd search-hub
pip install -r requirements.txt   # 可选，用于 DuckDuckGo
python3 search.py "你的关键词"     # 直接使用！
```

如果不使用 DuckDuckGo，无需 `pip install`。脚本仅依赖 Python 3.8+ 标准库。

## 用法

### 全局搜索（所有引擎并发）

```bash
python3 search.py "transformer"              # 搜索全部引擎
python3 search.py "RAG" --academic           # 仅学术论文
python3 search.py "python async" --tech      # 仅技术社区
python3 search.py "GPT-4" --web              # 仅网页搜索
python3 search.py "AI Agent" --deep          # + 读取 TOP 3 网页内容
python3 search.py "AI Agent" --json          # JSON 格式输出
```

### 单引擎搜索

```bash
python3 search.py wiki "深度学习"            # Wikipedia（自动中文）
python3 search.py arxiv "attention mechanism"
python3 search.py github "web crawler"
python3 search.py hn "startup"
python3 search.py reddit "side project"
python3 search.py stackoverflow "python async"
python3 search.py scholar "large language model"
python3 search.py crossref "machine learning"
python3 search.py openalex "neural network"
python3 search.py searxng "2025 最佳笔记本"
python3 search.py ddg "天气"
python3 search.py archive "old website"
python3 search.py jina https://example.com   # 读取任意 URL
python3 search.py local "项目笔记"
```

### 管理命令

```bash
python3 search.py init          # 生成 config.json
python3 search.py engines       # 查看引擎状态
python3 search.py cache         # 查看缓存统计
python3 search.py cache clear   # 清空缓存
```

## 配置

运行 `python3 search.py init` 自动生成 `config.json`：

```json
{
  "work_dir": "",
  "local_projects": {
    "my-notes": { "path": "/path/to/notes", "desc": "我的笔记" }
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

可选环境变量（`.env`）：

```
FEISHU_APP_ID=xxx         # 飞书知识库访问
FEISHU_APP_SECRET=xxx     # 飞书知识库访问
XCRAWL_API_KEY=xxx        # XCrawl 搜索（付费，免费 1000 积分）
```

## 架构

```
search.py <关键词>
    |
    +-- 并发线程池（8 线程）
    |   +-- SearXNG ---- 元搜索（Google/Bing/...）
    |   +-- DDG -------- DuckDuckGo（降级备选）
    |   +-- XCrawl ----- 网页搜索（可选，付费）
    |   +-- Wikipedia -- 百科全书（自动中/英文）
    |   +-- arXiv ------ CS/物理论文
    |   +-- Scholar ---- Semantic Scholar
    |   +-- CrossRef --- 学术元数据
    |   +-- OpenAlex --- 学术作品
    |   +-- HN --------- Hacker News
    |   +-- GitHub ----- 代码仓库
    |   +-- Reddit ----- 社区讨论
    |   +-- StackOverflow -- 问答
    |   +-- Archive ---- Internet Archive
    |   +-- Local ------ 本地文件（可配置）
    |   +-- Feishu ----- 飞书知识库（可选）
    |
    +-- [--deep] Jina Reader 读取 TOP 3 网页内容
```

### 搜索模式

| 参数 | 引擎范围 |
|------|----------|
| （默认） | 全部 15+ 引擎并发 |
| `--web` | SearXNG、XCrawl、DuckDuckGo |
| `--academic` | arXiv、Semantic Scholar、CrossRef、OpenAlex、Wikipedia |
| `--tech` | Hacker News、GitHub、Reddit、Stack Overflow |

### 缓存策略

| 规则 | 值 |
|------|-----|
| 搜索结果缓存 | 1 小时 |
| 网页内容缓存（`--deep`） | 24 小时 |
| 最大缓存空间 | 50 MB |
| 过期清理 | 读取时自动删除 |
| 超限清理 | 按最旧优先淘汰 |

## 许可证

[MIT](LICENSE) (c) 2025 Ming-H
