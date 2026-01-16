"""
Civitatis Web Scraper

Extracts tour data from Civitatis.com by parsing the GTMData JSON
embedded in the page source. This approach is reliable because
Civitatis uses structured data for analytics tracking.
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.config import get_settings
from src.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


@dataclass
class TourData:
    """Structured tour data extracted from Civitatis."""
    civitatis_id: int
    name: str
    price: Decimal
    currency: str = "EUR"
    category: str | None = None
    url: str | None = None
    rating: Decimal | None = None
    position: int | None = None
    brand_id: int | None = None
    destination: str | None = None
    destination_id: int | None = None
    scraped_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "civitatis_id": self.civitatis_id,
            "name": self.name,
            "price": float(self.price),
            "currency": self.currency,
            "category": self.category,
            "url": self.url,
            "rating": float(self.rating) if self.rating else None,
            "position": self.position,
            "brand_id": self.brand_id,
            "destination": self.destination,
            "destination_id": self.destination_id,
            "scraped_at": self.scraped_at.isoformat(),
        }


class CivitatisScraperError(Exception):
    """Base exception for Civitatis scraper errors."""
    pass


class CivitatisScraper:
    """
    Scraper for Civitatis.com tour listings.

    Extracts tour data from the GTMData JavaScript variable which contains
    structured product impressions data used for Google Tag Manager.
    """

    BASE_URL = "https://www.civitatis.com"

    def __init__(self):
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._playwright = None
        self._last_request_time: float = 0
        self._lock = asyncio.Lock()

    async def _ensure_browser(self) -> Browser:
        """Initialize browser if not already running."""
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu",
                ]
            )
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="en-US",
            )
            logger.info("Browser initialized for Civitatis scraper")
        return self._browser

    async def close(self) -> None:
        """Close browser and cleanup resources."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Browser closed")

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            delay = settings.scrape_rate_limit_seconds

            if elapsed < delay and self._last_request_time > 0:
                wait_time = delay - elapsed
                logger.info(f"Rate limiting: waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

            self._last_request_time = asyncio.get_event_loop().time()

    async def _get_page(self) -> Page:
        """Get a new browser page."""
        await self._ensure_browser()
        return await self._context.new_page()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _fetch_page(self, url: str) -> str:
        """Fetch page content with rate limiting and retries."""
        await self._rate_limit()

        page = await self._get_page()
        try:
            logger.info(f"Fetching: {url}")
            await page.goto(url, wait_until="networkidle", timeout=30000)

            # Wait for content to be fully loaded
            await page.wait_for_timeout(2000)

            # Try to close cookie banner if present
            try:
                cookie_selectors = [
                    "button:has-text('Accept')",
                    "button:has-text('Aceptar')",
                    "[class*='cookie'] button",
                    "#onetrust-accept-btn-handler",
                ]
                for selector in cookie_selectors:
                    btn = page.locator(selector)
                    if await btn.count() > 0:
                        await btn.first.click()
                        await page.wait_for_timeout(500)
                        break
            except Exception:
                pass  # Cookie banner not found or already closed

            html = await page.content()
            logger.info(f"Fetched {len(html):,} bytes from {url}")
            return html
        finally:
            await page.close()

    def _extract_gtm_data(self, html: str) -> dict[str, Any] | None:
        """Extract GTMData JSON from page HTML."""
        # Look for GTMData variable assignment
        patterns = [
            r'var\s+GTMData\s*=\s*({.*?});',
            r'GTMData\s*=\s*({.*?});',
            r'dataLayer\.push\(({.*?"ecommerce".*?})\)',
        ]

        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                try:
                    json_str = match.group(1)
                    # Clean up potential issues
                    json_str = re.sub(r',\s*}', '}', json_str)
                    json_str = re.sub(r',\s*]', ']', json_str)
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse GTMData: {e}")
                    continue

        return None

    def _parse_impressions(
        self,
        gtm_data: dict[str, Any],
        destination: str | None = None,
        destination_id: int | None = None,
    ) -> list[TourData]:
        """Parse tour impressions from GTMData."""
        tours = []

        ecommerce = gtm_data.get("ecommerce", {})
        impressions = ecommerce.get("impressions", [])
        currency = ecommerce.get("currencyCode", "EUR")

        for imp in impressions:
            try:
                tour_id = imp.get("id")
                if not tour_id or tour_id == -1:
                    continue  # Skip invalid entries

                name = imp.get("name", "").replace("39s", "'s")  # Fix encoding
                price = imp.get("price", 0)

                if not name or price <= 0:
                    continue

                tour = TourData(
                    civitatis_id=int(tour_id),
                    name=name,
                    price=Decimal(str(price)),
                    currency=currency,
                    category=imp.get("category"),
                    url=imp.get("url"),
                    rating=Decimal(str(imp.get("dimension32", 0))) if imp.get("dimension32") else None,
                    position=imp.get("position"),
                    brand_id=imp.get("brand"),
                    destination=destination or imp.get("list"),
                    destination_id=destination_id or (int(imp.get("list_id")) if imp.get("list_id") else None),
                )
                tours.append(tour)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse tour impression: {e}")
                continue

        return tours

    async def get_destination_tours(
        self,
        destination_slug: str,
        language: str = "en",
    ) -> list[TourData]:
        """
        Get all tours for a specific destination.

        Args:
            destination_slug: URL slug (e.g., "rome", "paris", "barcelona")
            language: Language code (default: "en")

        Returns:
            List of TourData objects
        """
        url = f"{self.BASE_URL}/{language}/{destination_slug}/"
        html = await self._fetch_page(url)

        gtm_data = self._extract_gtm_data(html)
        if not gtm_data:
            logger.warning(f"No GTMData found for {destination_slug}")
            return []

        tours = self._parse_impressions(
            gtm_data,
            destination=destination_slug.title(),
        )

        logger.info(f"Found {len(tours)} tours for {destination_slug}")
        return tours

    async def search_tours(
        self,
        query: str,
        language: str = "en",
    ) -> list[TourData]:
        """
        Search for tours by keyword.

        Args:
            query: Search query
            language: Language code (default: "en")

        Returns:
            List of TourData objects
        """
        from urllib.parse import quote_plus
        url = f"{self.BASE_URL}/{language}/search/?q={quote_plus(query)}"
        html = await self._fetch_page(url)

        gtm_data = self._extract_gtm_data(html)
        if not gtm_data:
            logger.warning(f"No GTMData found for search: {query}")
            return []

        tours = self._parse_impressions(gtm_data)

        logger.info(f"Found {len(tours)} tours for search '{query}'")
        return tours

    async def get_tour_details(self, tour_url: str) -> TourData | None:
        """
        Get detailed information for a specific tour.

        Args:
            tour_url: Full URL or path to tour page

        Returns:
            TourData object or None if not found
        """
        if not tour_url.startswith("http"):
            tour_url = f"{self.BASE_URL}{tour_url}"

        html = await self._fetch_page(tour_url)

        # Extract price from page
        price_match = re.search(r'"price":\s*([\d.]+)', html)
        name_match = re.search(r'"name":\s*"([^"]+)"', html)
        id_match = re.search(r'"id":\s*(\d+)', html)

        if not all([price_match, name_match, id_match]):
            logger.warning(f"Could not extract tour details from {tour_url}")
            return None

        return TourData(
            civitatis_id=int(id_match.group(1)),
            name=name_match.group(1),
            price=Decimal(price_match.group(1)),
            url=tour_url,
        )


# Global scraper instance
civitatis_scraper = CivitatisScraper()
