import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import re
from .models import PageContent

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def clean_url(url):
    """Normalize URL: remove duplicate slashes in path, avoid trailing slash for .php files."""
    parsed = urlparse(url)
    cleaned_path = re.sub(r'/{2,}', '/', parsed.path)
    if not cleaned_path.endswith('/') and not cleaned_path.endswith('.php'):
        cleaned_path += '/'
    return urlunparse((parsed.scheme, parsed.netloc, cleaned_path, '', '', ''))


def scrape_and_sync(domain):
    results = []
    visited = set()

    def scrape_page(url):
        if url in visited:
            return
        visited.add(url)

        try:
            print(f"Scraping: {url}")
            resp = requests.get(url, headers=HEADERS, timeout=10, verify=False)
            print(resp.status_code)
            if resp.status_code != 200:
                results.append((url, "failed"))
                return

            soup = BeautifulSoup(resp.text, "html.parser")
            page_text = " ".join(soup.stripped_strings)

            obj, created = PageContent.objects.update_or_create(
                url=url,
                defaults={"content": page_text}
            )
            results.append((url, "created" if created else "updated"))

            # Extract and visit all internal links
            for a in soup.select("a[href]"):
                link = urljoin(domain, a["href"])
                parsed_link = urlparse(link)
                if urlparse(domain).netloc == parsed_link.netloc and link not in visited:
                    scrape_page(link)

        except Exception as e:
            print(f"Error scraping {url}: {e}")
            results.append((url, "failed"))

    scrape_page(domain)
    return results
