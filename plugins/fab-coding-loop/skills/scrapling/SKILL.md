---
name: scrapling
description: /scrapling — Adaptive Web Scraping with Scrapling
---

# /scrapling — Adaptive Web Scraping with Scrapling

Use Scrapling (48K stars, D4Vinci/Scrapling) for web scraping tasks. Handles anti-bot detection, adaptive element selection, and full-scale crawling. Installed at `~/.venvs/scrapling/`.

## Quick Reference

```bash
# Always activate the venv first
source ~/.venvs/scrapling/bin/activate
```

## Fetcher Modes

### 1. Fetcher (basic HTTP, fast)
For pages that don't need JavaScript rendering or anti-bot bypass:
```python
from scrapling.fetchers import Fetcher
page = Fetcher.get('https://example.com')
items = page.css('h1::text').getall()
```

### 2. StealthyFetcher (bypasses Cloudflare, anti-bot)
For pages behind Cloudflare Turnstile or other bot detection:
```python
from scrapling.fetchers import StealthyFetcher
StealthyFetcher.adaptive = True
page = StealthyFetcher.fetch('https://example.com', headless=True, network_idle=True)
items = page.css('.product-title::text').getall()
```

### 3. DynamicFetcher (full browser, renders JS)
For JavaScript-heavy SPWs:
```python
from scrapling.fetchers import DynamicFetcher
page = DynamicFetcher.fetch('https://example.com', headless=True, wait_selector='div.content')
```

### 4. AsyncFetcher (concurrent requests)
```python
import asyncio
from scrapling.fetchers import AsyncFetcher

async def main():
    pages = await AsyncFetcher.async_get(['https://example.com/page1', 'https://example.com/page2'])
    for page in pages:
        print(page.css('h1::text').get())

asyncio.run(main())
```

## Selection (CSS selectors + auto_adapt)

```python
# Standard CSS selectors (like BeautifulSoup/lxml)
page.css('div.product')           # All matching elements
page.css_first('h1.title')        # First match (or None)
page.css('a::attr(href)').getall() # Attributes
page.css('span.price::text').getall() # Text content

# Adaptive selection — survives page structure changes
products = page.css('.product', auto_save=True)   # First run: save element signatures
products = page.css('.product', adaptive=True)     # Later: find elements even if selectors changed
```

## Spider (full-scale crawling)

```python
from scrapling.spiders import Spider, Response

class MySpider(Spider):
    name = "example"
    start_urls = ["https://example.com/products"]

    async def parse(self, response: Response):
        for item in response.css('.product'):
            yield {
                "title": item.css('h2::text').get(),
                "price": item.css('.price::text').get(),
                "url": item.css('a::attr(href)').get(),
            }
        # Follow pagination
        next_page = response.css('a.next::attr(href)').get()
        if next_page:
            yield response.follow(next_page, self.parse)

MySpider().start()
```

## Common Patterns

### Scrape a list of URLs and extract structured data
```bash
source ~/.venvs/scrapling/bin/activate
python3 << 'PYEOF'
from scrapling.fetchers import Fetcher
import json

urls = ["https://example.com/1", "https://example.com/2"]
results = []
for url in urls:
    page = Fetcher.get(url)
    results.append({
        "url": url,
        "title": page.css('h1::text').get(),
        "body": page.css('article p::text').getall(),
    })
print(json.dumps(results, indent=2))
PYEOF
```

### Bypass Cloudflare-protected page
```bash
source ~/.venvs/scrapling/bin/activate
python3 << 'PYEOF'
from scrapling.fetchers import StealthyFetcher
page = StealthyFetcher.fetch('https://protected-site.com', headless=True, network_idle=True)
print(page.css('title::text').get())
PYEOF
```

### Extract all links from a page
```python
links = page.css('a::attr(href)').getall()
unique_links = list(set(links))
```

### Get clean text from a page
```python
text = page.get_all_text()  # All visible text
```

## Notes

- **Venv location:** `~/.venvs/scrapling/` — always `source` before use
- **StealthyFetcher needs Playwright browsers:** run `playwright install chromium` if not already done
- **Adaptive mode** stores element signatures in `~/.scrapling/` — useful for long-running scrapers that revisit pages
- **Rate limiting:** use `time.sleep()` between requests for polite scraping
- **For research tasks:** prefer `Fetcher` first (fastest). Fall back to `StealthyFetcher` only when you get 403s or CAPTCHAs
