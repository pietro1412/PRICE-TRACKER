"""
Civitatis Web Scraper

Extracts tour data from Civitatis.com by combining:
1. GTMData JSON for tour metadata (ID, name, category, rating)
2. HTML-displayed prices ("From €XX") for accurate pricing

GTMData prices may differ from displayed prices, so we extract
the actual visible prices from HTML elements.
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

    async def _fetch_page_with_prices(self, url: str) -> tuple[str, dict[str, Decimal]]:
        """
        Fetch page content and extract displayed prices from HTML.

        Returns:
            Tuple of (html_content, {tour_url: displayed_price})
        """
        await self._rate_limit()

        page = await self._get_page()
        prices_by_url: dict[str, Decimal] = {}

        try:
            logger.info(f"Fetching with price extraction: {url}")
            await page.goto(url, wait_until="networkidle", timeout=30000)
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
                pass

            # Extract prices from tour cards
            # Civitatis tour cards have links with href and price elements
            tour_cards = page.locator("article.comfort-card, .o-search-list__item, [data-gtm-click]")
            card_count = await tour_cards.count()
            logger.info(f"Found {card_count} tour cards")

            for i in range(card_count):
                try:
                    card = tour_cards.nth(i)

                    # Get tour URL from the card's link
                    link = card.locator("a[href*='/en/'], a[href*='/it/'], a[href*='/es/']").first
                    href = await link.get_attribute("href") if await link.count() > 0 else None

                    if not href:
                        # Try alternative selectors
                        link = card.locator("a").first
                        href = await link.get_attribute("href") if await link.count() > 0 else None

                    if not href:
                        continue

                    # Extract displayed price from the card
                    # Try multiple selectors for price elements
                    price_selectors = [
                        ".comfort-card__price__current",
                        ".m-activity-card__price",
                        "[class*='price'] span",
                        ".price-tag",
                        "span[class*='Price']",
                    ]

                    price_text = None
                    for selector in price_selectors:
                        price_elem = card.locator(selector).first
                        if await price_elem.count() > 0:
                            price_text = await price_elem.text_content()
                            if price_text:
                                break

                    # If no specific price element, try to find price pattern in card text
                    if not price_text:
                        card_text = await card.text_content()
                        # Look for price pattern like "€59" or "59 €" or "From €59"
                        price_match = re.search(r'(?:From\s*)?[€$£]\s*(\d+(?:[.,]\d{2})?)|(\d+(?:[.,]\d{2})?)\s*[€$£]', card_text or "")
                        if price_match:
                            price_text = price_match.group(1) or price_match.group(2)

                    if price_text:
                        # Clean and parse price
                        price_clean = re.sub(r'[^\d.,]', '', price_text)
                        price_clean = price_clean.replace(',', '.')
                        if price_clean:
                            try:
                                price_value = Decimal(price_clean)
                                if price_value > 0:
                                    prices_by_url[href] = price_value
                                    logger.debug(f"Extracted price {price_value} for {href}")
                            except Exception:
                                pass

                except Exception as e:
                    logger.debug(f"Error extracting price from card {i}: {e}")
                    continue

            logger.info(f"Extracted {len(prices_by_url)} prices from HTML")
            html = await page.content()
            return html, prices_by_url

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
        html_prices: dict[str, Decimal] | None = None,
    ) -> list[TourData]:
        """
        Parse tour impressions from GTMData, using HTML prices when available.

        Args:
            gtm_data: GTMData dictionary from page
            destination: Destination name override
            destination_id: Destination ID override
            html_prices: Dictionary mapping tour URLs to displayed prices

        Returns:
            List of TourData objects with accurate prices
        """
        tours = []
        html_prices = html_prices or {}

        ecommerce = gtm_data.get("ecommerce", {})
        impressions = ecommerce.get("impressions", [])
        currency = ecommerce.get("currencyCode", "EUR")

        for imp in impressions:
            try:
                tour_id = imp.get("id")
                if not tour_id or tour_id == -1:
                    continue  # Skip invalid entries

                name = imp.get("name", "").replace("39s", "'s")  # Fix encoding
                tour_url = imp.get("url")

                # Prefer HTML-displayed price over GTMData price
                price = None
                if html_prices:
                    # Try to match by URL or tour name
                    tour_url_slug = tour_url.rstrip('/').split('/')[-1] if tour_url else None

                    for url_key, html_price in html_prices.items():
                        url_key_slug = url_key.rstrip('/').split('/')[-1]

                        # Match by URL slug (last part of URL path)
                        if tour_url_slug and tour_url_slug == url_key_slug:
                            price = html_price
                            logger.debug(f"Using HTML price {price} for {name} (URL match)")
                            break

                        # Match by tour name similarity (normalize both)
                        name_normalized = name.lower().replace(' ', '-').replace('&', '').replace("'", '')
                        url_normalized = url_key_slug.lower()
                        if name_normalized in url_normalized or url_normalized in name_normalized:
                            price = html_price
                            logger.debug(f"Using HTML price {price} for {name} (name match)")
                            break

                # Fall back to GTMData price if no HTML price found
                if price is None:
                    gtm_price = imp.get("price", 0)
                    if gtm_price and gtm_price > 0:
                        price = Decimal(str(gtm_price))
                        logger.debug(f"Using GTMData price {price} for {name} (no HTML price)")

                if not name or not price or price <= 0:
                    continue

                tour = TourData(
                    civitatis_id=int(tour_id),
                    name=name,
                    price=price,
                    currency=currency,
                    category=imp.get("category"),
                    url=tour_url,
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

        Uses HTML price extraction for accurate "From €XX" prices,
        with GTMData as fallback for metadata and backup pricing.

        Args:
            destination_slug: URL slug (e.g., "rome", "paris", "barcelona")
            language: Language code (default: "en")

        Returns:
            List of TourData objects with accurate displayed prices
        """
        url = f"{self.BASE_URL}/{language}/{destination_slug}/"

        # Fetch page and extract HTML prices simultaneously
        html, html_prices = await self._fetch_page_with_prices(url)

        gtm_data = self._extract_gtm_data(html)
        if not gtm_data:
            logger.warning(f"No GTMData found for {destination_slug}")
            return []

        # Parse tours using HTML prices where available
        tours = self._parse_impressions(
            gtm_data,
            destination=destination_slug.title(),
            html_prices=html_prices,
        )

        # Log price source statistics
        html_priced = sum(1 for t in tours if any(t.url and (t.url in k or k.endswith(t.url)) for k in html_prices.keys()))
        logger.info(f"Found {len(tours)} tours for {destination_slug} ({html_priced} with HTML prices)")
        return tours

    async def search_tours(
        self,
        query: str,
        language: str = "en",
    ) -> list[TourData]:
        """
        Search for tours by keyword.

        Uses HTML price extraction for accurate displayed prices.

        Args:
            query: Search query
            language: Language code (default: "en")

        Returns:
            List of TourData objects with accurate prices
        """
        from urllib.parse import quote_plus
        url = f"{self.BASE_URL}/{language}/search/?q={quote_plus(query)}"

        # Fetch page and extract HTML prices
        html, html_prices = await self._fetch_page_with_prices(url)

        gtm_data = self._extract_gtm_data(html)
        if not gtm_data:
            logger.warning(f"No GTMData found for search: {query}")
            return []

        tours = self._parse_impressions(gtm_data, html_prices=html_prices)

        logger.info(f"Found {len(tours)} tours for search '{query}'")
        return tours

    async def get_tour_details(self, tour_url: str) -> TourData | None:
        """
        Get detailed information for a specific tour.

        Extracts the displayed "From €XX" price from the tour detail page.

        Args:
            tour_url: Full URL or path to tour page

        Returns:
            TourData object or None if not found
        """
        if not tour_url.startswith("http"):
            tour_url = f"{self.BASE_URL}{tour_url}"

        await self._rate_limit()
        page = await self._get_page()

        try:
            await page.goto(tour_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)

            # Close cookie banner if present
            try:
                for selector in ["button:has-text('Accept')", "#onetrust-accept-btn-handler"]:
                    btn = page.locator(selector)
                    if await btn.count() > 0:
                        await btn.first.click()
                        await page.wait_for_timeout(500)
                        break
            except Exception:
                pass

            html = await page.content()

            # Extract metadata from GTMData/JSON for ID and name
            name_match = re.search(r'"name":\s*"([^"]+)"', html)
            id_match = re.search(r'"id":\s*(\d+)', html)

            if not all([name_match, id_match]):
                logger.warning(f"Could not extract tour details from {tour_url}")
                return None

            # Extract displayed price from HTML
            # Try multiple selectors for the main price display
            price = None
            price_selectors = [
                ".m-activity-info__price-container .price",
                ".o-activity-price__amount",
                "[class*='price'] [class*='amount']",
                ".m-activity-card__price",
                "span[class*='Price']",
            ]

            for selector in price_selectors:
                try:
                    price_elem = page.locator(selector).first
                    if await price_elem.count() > 0:
                        price_text = await price_elem.text_content()
                        if price_text:
                            price_clean = re.sub(r'[^\d.,]', '', price_text)
                            price_clean = price_clean.replace(',', '.')
                            if price_clean:
                                price = Decimal(price_clean)
                                break
                except Exception:
                    continue

            # Fallback: search for price pattern in visible text
            if not price:
                body_text = await page.locator("body").text_content()
                price_match = re.search(r'(?:From|A partire da)\s*[€$£]\s*(\d+(?:[.,]\d{2})?)', body_text or "")
                if price_match:
                    price_str = price_match.group(1).replace(',', '.')
                    price = Decimal(price_str)

            # Final fallback to GTMData price (though less accurate)
            if not price:
                gtm_price_match = re.search(r'"price":\s*([\d.]+)', html)
                if gtm_price_match:
                    price = Decimal(gtm_price_match.group(1))
                    logger.warning(f"Using GTMData price as fallback for {tour_url}")

            if not price:
                logger.warning(f"Could not extract price from {tour_url}")
                return None

            return TourData(
                civitatis_id=int(id_match.group(1)),
                name=name_match.group(1),
                price=price,
                url=tour_url,
            )

        finally:
            await page.close()


# Global scraper instance
civitatis_scraper = CivitatisScraper()
