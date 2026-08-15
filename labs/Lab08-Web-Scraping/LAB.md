# Lab 08 — Text Parsing & Web Scraping with LangChain

**Duration** ~45 min · **GPU required** No · **Backend** Ollama (`http://10.79.253.112:11434`), `llama3.1:8b`
**Verified** ⚠️ **9 cell errors** on a stock environment — `playwright` is missing from the
upstream requirements. Fixed by the extra install below.

## What this lab does
Scrapes web content and feeds it to an LLM for structured summarisation: a single page, then
all links on a page, then a PDF embedded in a page, then Wikipedia via LangChain's wrapper.

## Objectives
- Extract text from a webpage and summarise it with an LLM.
- Iteratively scrape all links within a page.
- Extract and process text from a PDF found on the web.
- Use LangChain's Wikipedia API wrapper for structured retrieval.

## 🚨 Missing dependency (upstream defect)
`AsyncChromiumLoader` drives a headless Chromium through **Playwright**, which the upstream
`requirements.txt` never installs:

```
ImportError: playwright is required for AsyncChromiumLoader.
Please install it with `pip install playwright`.
```

Fix — install the package **and** the browser binary:
```bash
pip install playwright
playwright install chromium
playwright install-deps chromium     # may need elevated rights; ask the facilitator
```
`requirements-fdp.txt` includes `playwright`, but the **browser download is a separate step**.

## Environment specifics
- Scraping targets the public internet (`https://edition.cnn.com`). If the notebook has no
  outbound access, use the `AsyncHtmlLoader` path or a local HTML file instead.
- `nest_asyncio.apply()` is required — Jupyter already runs an event loop.

## Walkthrough
1. **Imports** — `AsyncChromiumLoader`, `AsyncHtmlLoader`, `BeautifulSoupTransformer`,
   `Ollama`, `PromptTemplate`, `StrOutputParser`; then `nest_asyncio.apply()`.
2. **Load the LLM** — `Ollama(model='llama3.1:8b', base_url="http://10.79.253.112:11434")`.
3. **Scrape one page** — `AsyncChromiumLoader([...], headless=True)` → `.load()`, then
   `BeautifulSoupTransformer` to pull text out of chosen tags (`<span>` in the notebook).
4. **Summarise** — a prompt instructs the model to find headlines and bodies and return a
   structured summary.
5. **Crawl all links** — `requests` + `BeautifulSoup` gather every `href` starting `https://`,
   then loop the scrape.
6. **PDF from the web** — download and parse with `pypdf`/`PyPDF2`.
7. **Wikipedia** — LangChain's API wrapper for clean structured retrieval.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `ImportError: playwright is required` | Run both playwright commands above. |
| `Executable doesn't exist ... chromium` | You installed the package but not the browser: `playwright install chromium`. |
| Host errors / empty documents | No outbound internet, or the site changed its markup. |
| `RuntimeError: This event loop is already running` | `nest_asyncio.apply()` was not run. |

## Teaching notes
Worth flagging the ethics and legality of scraping (robots.txt, terms of service, rate
limits) — faculty will pass this on to students. Also a good place to note that site markup
changes break scrapers, which is why the CNN selectors may need adjusting on the day.
