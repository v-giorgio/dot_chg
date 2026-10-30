import logging
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://dotgroup.com.br"
BLOG_URL = f"{BASE_URL}/blog"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SemanticSearchBot/1.0)"}
REQUEST_DELAY = 1.5  # polite delay between requests


@dataclass
class BlogPost:
    url: str
    title: str
    content: str


def _fetch(url: str, session: requests.Session) -> BeautifulSoup | None:
    try:
        resp = session.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as exc:
        logger.error("GET %s failed: %s", url, exc)
        return None


def _is_post_url(href: str) -> bool:
    parsed = urlparse(href)
    parts = parsed.path.strip("/").split("/")
    return (
        parsed.netloc in ("dotgroup.com.br", "www.dotgroup.com.br")
        and len(parts) == 2
        and parts[0] == "blog"
        and parts[1] not in ("", "page", "category", "tag", "author", "feed")
    )


def _discover_post_urls(session: requests.Session, max_posts: int | None = None) -> list[str]:
    """Walk listing pages and collect blog post URLs, stopping early if max_posts is set."""
    found: set[str] = set()
    page = 1

    while True:
        url = BLOG_URL if page == 1 else f"{BLOG_URL}/page/{page}"
        logger.info("Crawling listing page %d: %s", page, url)
        soup = _fetch(url, session)
        if soup is None:
            break

        page_posts: set[str] = set()
        for a in soup.find_all("a", href=True):
            full = urljoin(BASE_URL, a["href"]).split("?")[0].rstrip("/")
            if _is_post_url(full):
                page_posts.add(full)

        if not page_posts:
            logger.info("No posts on page %d — stopping pagination.", page)
            break

        new = page_posts - found
        found |= page_posts
        logger.info("Page %d: %d posts found (%d new).", page, len(page_posts), len(new))

        if max_posts and len(found) >= max_posts:
            logger.info("Reached max_posts=%d — stopping pagination.", max_posts)
            break

        time.sleep(REQUEST_DELAY)
        page += 1

    logger.info("Total post URLs discovered: %d", len(found))
    return list(found)


def _scrape_post(url: str, session: requests.Session) -> BlogPost | None:
    soup = _fetch(url, session)
    if soup is None:
        return None

    # Title
    title = ""
    for sel in ["h1.entry-title", "h1.post-title", ".post-title", "h1"]:
        tag = soup.select_one(sel)
        if tag:
            title = tag.get_text(strip=True)
            break

    # Main content container
    content_tag = None
    for sel in [".entry-content", ".post-content", "article .content", "article", "main"]:
        content_tag = soup.select_one(sel)
        if content_tag:
            break

    if not content_tag:
        logger.warning("No content container found at %s", url)
        return None

    for noise in content_tag.find_all(["script", "style", "nav", "footer", "aside", "form"]):
        noise.decompose()

    lines = [ln for ln in content_tag.get_text(separator="\n", strip=True).splitlines() if ln.strip()]
    content = "\n".join(lines)

    if len(content) < 150:
        logger.warning("Content too short (%d chars) at %s — skipped.", len(content), url)
        return None

    return BlogPost(url=url, title=title or url, content=content)


def crawl(max_posts: int | None = None):
    """Yield BlogPost objects scraped from https://dotgroup.com.br/blog."""
    with requests.Session() as session:
        urls = _discover_post_urls(session, max_posts=max_posts)
        if max_posts:
            urls = urls[:max_posts]

        for i, url in enumerate(urls, 1):
            logger.info("Scraping %d/%d: %s", i, len(urls), url)
            post = _scrape_post(url, session)
            if post:
                yield post
            time.sleep(REQUEST_DELAY)
