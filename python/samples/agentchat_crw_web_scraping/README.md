# CRW Web Scraping Tools for AutoGen

This sample shows how to use [CRW](https://github.com/nicholasgasior/crw) web scraping tools with AutoGen agents.

CRW is an open-source web scraper for AI agents — a single Rust binary with a Firecrawl-compatible REST API.

## Tools

| Tool | Function | CRW Endpoint |
|------|----------|-------------|
| `CrwScrapeTool` | Scrape a single URL | `POST /v1/scrape` |
| `CrwCrawlTool` | Crawl a website (multi-page) | `POST /v1/crawl` + `GET /v1/crawl/{id}` |
| `CrwMapTool` | Discover all links on a site | `POST /v1/map` |

## Prerequisites

1. Install CRW: see [CRW installation docs](https://github.com/nicholasgasior/crw)
2. Start the server: `crw --port 3000`
3. Install Python deps: `pip install "autogen-agentchat" "autogen-ext[crw,openai]"`
4. Set `OPENAI_API_KEY` environment variable

## Run

```bash
python app.py
```
