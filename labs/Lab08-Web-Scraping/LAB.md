# Lab 08 — Text Parsing & Web Scraping with LangChain

**Duration** ~45 min · **GPU required** No · **Backend** Ollama (`http://10.79.253.112:11434`), `llama3.1:8b`
**Verified** ✅ Runs clean once the two setup steps below are done. On a stock environment
Playwright's Chromium cannot start (missing system libraries, and `sudo` is unavailable) —
both are solved below **without root**.

## What this lab does
Scrapes web content and feeds it to an LLM for structured summarisation: a single page, then
all links on a page, then a PDF embedded in a page, then Wikipedia via LangChain's wrapper.

## Objectives
- Extract text from a webpage and summarise it with an LLM.
- Iteratively scrape all links within a page.
- Extract and process text from a PDF found on the web.
- Use LangChain's Wikipedia API wrapper for structured retrieval.

## ⚙️ Required setup — browser binary and system libraries
`AsyncChromiumLoader` drives a headless Chromium through **Playwright**. The upstream
`requirements.txt` never installed it, which produced:

```
ImportError: playwright is required for AsyncChromiumLoader.
Please install it with `pip install playwright`.
```

`requirements-fdp.txt` now installs `playwright`, but the **browser binary and its system
libraries are two further steps**:

```bash
playwright install chromium
```

### The system libraries — no root required
`playwright install-deps chromium` needs root, which notebook users do not have
(`sudo` is not on the image). The browser then dies at launch with:

```
chrome-headless-shell: error while loading shared libraries:
libnspr4.so: cannot open shared object file: No such file or directory
```

Install the libraries into an **isolated conda prefix** instead. `/opt/conda` is writable by
`jovyan`, and a separate prefix keeps the base environment's pinned `numpy`/`scipy` untouched:

```bash
conda create -y -p ~/.nsslibs -c conda-forge \
  nspr nss atk-1.0 at-spi2-atk at-spi2-core libcups libdrm libxkbcommon \
  xorg-libxcomposite xorg-libxdamage xorg-libxfixes xorg-libxrandr xorg-libxtst \
  libgbm pango cairo alsa-lib dbus expat
```

Then, in the **first cell of the notebook**, before any Playwright import:

```python
import os
os.environ["LD_LIBRARY_PATH"] = "/home/jovyan/.nsslibs/lib:" + os.environ.get("LD_LIBRARY_PATH", "")
```

Verified on the lab image: `AsyncChromiumLoader` then loads `edition.cnn.com` normally.

> **No-install fallback.** `AsyncHtmlLoader` — already imported by this notebook — fetches over
> plain HTTP and needs **no browser at all**. For the static pages in this lab it produces
> equivalent text. If the conda step is skipped, swap `AsyncChromiumLoader` for it and continue.

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
| `ImportError: playwright is required` | The package is missing: `pip install -r requirements-fdp.txt`. |
| `Executable doesn't exist ... chromium` | You installed the package but not the browser: `playwright install chromium`. |
| `error while loading shared libraries: libnspr4.so` (or `libatk-1.0.so.0`, `libgbm`, …) | System libraries missing. Create the conda prefix above and set `LD_LIBRARY_PATH` **before** importing Playwright. Do not run `install-deps` — it needs root. |
| `LD_LIBRARY_PATH` set but still failing | It must be set *before* the browser process is spawned. Put it in the first cell and restart the kernel. |
| Host errors / empty documents | No outbound internet, or the site changed its markup. |
| `RuntimeError: This event loop is already running` | `nest_asyncio.apply()` was not run. |

## Teaching notes
Worth flagging the ethics and legality of scraping (robots.txt, terms of service, rate
limits) — faculty will pass this on to students. Also a good place to note that site markup
changes break scrapers, which is why the CNN selectors may need adjusting on the day.
