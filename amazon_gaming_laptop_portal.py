#!/usr/bin/env python3
"""
Amazon Gaming Laptop Search Portal Handler
Integrates with persistent_browser_server.py
Provides Mermaid diagram generation and portal mapping
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any
from aiohttp import web
from dataclasses import dataclass, asdict

logger = logging.getLogger('amazon-portal')


@dataclass
class PortalMapping:
    """Portal definition with metadata"""
    name: str
    selector: str
    portal_type: str
    strength: float
    description: str = ""
    wait_for: str = None
    expect_navigation: bool = False


class AmazonGamingLaptopAnalyzer:
    """
    Analyzes Amazon gaming laptop search page structure
    Generates Mermaid diagrams and portal mappings
    """

    # Portal definitions mapped from search results
    PORTALS: Dict[str, PortalMapping] = {
        'results_grid': PortalMapping(
            name='results_grid',
            selector='.s-result-item',
            portal_type='grid_container',
            strength=0.98,
            description='Main results grid (48 items per page)'
        ),
        'product_detail': PortalMapping(
            name='product_detail',
            selector='.s-result-item h2 a',
            portal_type='navigate',
            strength=0.99,
            description='Click product title to view detail page',
            expect_navigation=True
        ),
        'add_to_cart': PortalMapping(
            name='add_to_cart',
            selector='button[aria-label*="Add to Cart"]',
            portal_type='click',
            strength=0.94,
            description='Add product to shopping cart',
            wait_for='.a-cart-added'
        ),
        'price_filter': PortalMapping(
            name='price_filter',
            selector='#priceRangeSlider',
            portal_type='range_filter',
            strength=0.91,
            description='Filter by price range'
        ),
        'brand_filter': PortalMapping(
            name='brand_filter',
            selector='input[aria-label*="Brand"]',
            portal_type='checkbox_filter',
            strength=0.96,
            description='Filter by brand (ASUS, MSI, HP, etc)'
        ),
        'spec_filter': PortalMapping(
            name='spec_filter',
            selector='input[aria-label*="GPU|RAM|CPU"]',
            portal_type='checkbox_filter',
            strength=0.93,
            description='Filter by GPU, RAM, CPU specifications'
        ),
        'rating_filter': PortalMapping(
            name='rating_filter',
            selector='.a-star-small span',
            portal_type='indicator',
            strength=0.97,
            description='Product star rating'
        ),
        'prime_badge': PortalMapping(
            name='prime_badge',
            selector='i.a-icon-prime',
            portal_type='indicator',
            strength=0.89,
            description='Amazon Prime eligible indicator'
        ),
        'next_page': PortalMapping(
            name='next_page',
            selector='.s-pagination-next a',
            portal_type='navigate',
            strength=0.95,
            description='Navigate to next results page',
            expect_navigation=True
        ),
        'pagination_pages': PortalMapping(
            name='pagination_pages',
            selector='.a-pagination li a',
            portal_type='navigate',
            strength=0.94,
            description='Direct page number navigation',
            expect_navigation=True
        )
    }

    @staticmethod
    def generate_mermaid_flowchart() -> str:
        """Generate Mermaid flowchart for Amazon search flow"""
        mermaid = '''graph TD
    A["Amazon.com/s?k=gaming laptops"]:::entry -->|Load| B["Results Grid<br/>48 items per page"]:::grid
    A -->|Browse| C["Left Sidebar<br/>Filters"]:::sidebar

    C -->|Price Filter| D["$500-$1000<br/>$1000-$1500<br/>$1500+"]:::filter
    C -->|Brand Filter| E["ASUS<br/>MSI<br/>HP<br/>Lenovo<br/>Razer"]:::filter
    C -->|Spec Filter| F["GPU: RTX 4060+<br/>CPU: i7/Ryzen 7+<br/>RAM: 16GB+"]:::filter
    C -->|Rating Filter| G["4+ Stars<br/>Prime Eligible"]:::filter

    D --> B
    E --> B
    F --> B
    G --> B

    B -->|Product Card| H["Product Detail Tile<br/>Image, Price, Rating"]:::card
    H -->|Click| I["Product Detail Page"]:::detail
    H -->|Add to Cart| J["Shopping Cart"]:::cart
    I -->|View Reviews| K["Reviews Section"]:::review
    I -->|Add to Cart| J

    B -->|Pagination| L["Next Page >"]:::pagination
    L --> B

    classDef entry fill:#bbdefb,stroke:#1976d2,stroke-width:3px
    classDef grid fill:#c8e6c9,stroke:#388e3c,stroke-width:2px
    classDef sidebar fill:#ffe0b2,stroke:#f57c00,stroke-width:2px
    classDef filter fill:#fff9c4,stroke:#fbc02d,stroke-width:2px
    classDef card fill:#f0f4c3,stroke:#827717,stroke-width:1px
    classDef detail fill:#d1c4e9,stroke:#512da8,stroke-width:2px
    classDef cart fill:#ffccbc,stroke:#d84315,stroke-width:2px
    classDef review fill:#b2dfdb,stroke:#00796b,stroke-width:1px
    classDef pagination fill:#f8bbd0,stroke:#c2185b,stroke-width:2px'''
        return mermaid

    @staticmethod
    def generate_portal_mapping_diagram() -> str:
        """Generate Mermaid diagram showing portal relationships"""
        mermaid = '''graph LR
    Search["Search Results Page"]:::page

    Search -->|Header| HeaderNav["Navigation<br/>Search Bar"]:::header
    Search -->|Left| Sidebar["Filters Panel<br/>Price, Brand, Specs,<br/>Rating, Prime"]:::sidebar
    Search -->|Center| Content["Results Grid<br/>s-result-item x 48"]:::content
    Search -->|Footer| Footer["Links, Copyright"]:::footer

    Content -->|Per Item| Card["Product Card<br/>Image, Title, Price,<br/>Rating, CTA"]:::card
    Card -->|Actions| Actions["Click: Detail<br/>Button: Cart<br/>Icon: Wishlist"]:::actions
    Card -->|Portals| CardPortals["Portal to Detail<br/>Portal to Cart<br/>Portal to Reviews"]:::portals

    classDef page fill:#eceff1,stroke:#37474f,stroke-width:3px
    classDef header fill:#b3e5fc,stroke:#0277bd,stroke-width:2px
    classDef sidebar fill:#fff9c4,stroke:#fbc02d,stroke-width:2px
    classDef content fill:#c8e6c9,stroke:#388e3c,stroke-width:2px
    classDef footer fill:#eeeeee,stroke:#616161,stroke-width:1px
    classDef card fill:#f0f4c3,stroke:#827717,stroke-width:1px
    classDef actions fill:#ffccbc,stroke:#d84315,stroke-width:1px
    classDef portals fill:#d1c4e9,stroke:#512da8,stroke-width:2px'''
        return mermaid

    @staticmethod
    async def analyze_page_structure(page) -> Dict[str, Any]:
        """Extract page structure from current page"""
        try:
            structure = await page.evaluate('''
            () => {
                const results = [];
                document.querySelectorAll('.s-result-item').forEach((item, idx) => {
                    results.push({
                        index: idx,
                        asin: item.getAttribute('data-asin'),
                        title: item.querySelector('h2 span')?.textContent?.trim(),
                        price: item.querySelector('.a-price-whole')?.textContent?.trim(),
                        rating: item.querySelector('.a-star-small span')?.textContent?.trim(),
                        isPrime: !!item.querySelector('i.a-icon-prime'),
                        isSponsored: !!item.querySelector('[aria-label*="Sponsored"]')
                    });
                });

                return {
                    pageTitle: document.title,
                    url: window.location.href,
                    resultsCount: results.length,
                    products: results.slice(0, 5),  // First 5 for preview
                    hasNextPage: !!document.querySelector('.s-pagination-next a'),
                    filterOptions: {
                        brands: Array.from(
                            document.querySelectorAll('input[aria-label*="Brand"]')
                        ).map(x => x.parentElement?.textContent?.trim()).filter(Boolean),
                        priceRanges: Array.from(
                            document.querySelectorAll('input[aria-label*="price"]')
                        ).map(x => x.parentElement?.textContent?.trim()).filter(Boolean)
                    }
                };
            }
            ''')
            return structure
        except Exception as e:
            logger.error(f"Failed to analyze page structure: {e}")
            return {'error': str(e)}

    @staticmethod
    async def extract_portals(page) -> Dict[str, List[Dict[str, Any]]]:
        """Extract all portal definitions from current page"""
        portals = {}

        for portal_name, portal_def in AmazonGamingLaptopAnalyzer.PORTALS.items():
            try:
                elements = await page.query_selector_all(portal_def.selector)
                count = len(elements) if elements else 0

                portals[portal_name] = {
                    'name': portal_def.name,
                    'selector': portal_def.selector,
                    'type': portal_def.portal_type,
                    'strength': portal_def.strength,
                    'count': count,
                    'found': count > 0,
                    'description': portal_def.description
                }
            except Exception as e:
                logger.warning(f"Failed to extract portal {portal_name}: {e}")
                portals[portal_name] = {
                    'name': portal_def.name,
                    'selector': portal_def.selector,
                    'error': str(e),
                    'strength': portal_def.strength
                }

        return portals


class AmazonPortalHTTPHandler:
    """HTTP request handlers for Amazon portal endpoints"""

    def __init__(self, browser_server):
        """
        Initialize handler
        Args:
            browser_server: Reference to PersistentBrowserServer instance
        """
        self.browser_server = browser_server

    async def handle_analyze_amazon_page(self, request):
        """
        POST /analyze-amazon-page
        Analyze current page and return structure + portals
        """
        try:
            if not self.browser_server.page:
                return web.json_response(
                    {'error': 'No page loaded'},
                    status=400
                )

            # Extract structure
            structure = await AmazonGamingLaptopAnalyzer.analyze_page_structure(
                self.browser_server.page
            )

            # Extract portals
            portals = await AmazonGamingLaptopAnalyzer.extract_portals(
                self.browser_server.page
            )

            # Generate Mermaid diagrams
            flowchart = AmazonGamingLaptopAnalyzer.generate_mermaid_flowchart()
            portal_diagram = AmazonGamingLaptopAnalyzer.generate_portal_mapping_diagram()

            return web.json_response({
                'success': True,
                'page_structure': structure,
                'portals': portals,
                'mermaid': {
                    'flowchart': flowchart,
                    'portal_map': portal_diagram
                },
                'cached_at': datetime.now().isoformat(),
                'url': self.browser_server.page.url
            })

        except Exception as e:
            logger.error(f"Error analyzing Amazon page: {e}")
            return web.json_response(
                {'error': str(e)},
                status=500
            )

    async def handle_get_portal_mapping(self, request):
        """
        GET /amazon/portal-mapping
        Return all portal mappings as JSON
        """
        try:
            portals_data = {}
            for name, portal in AmazonGamingLaptopAnalyzer.PORTALS.items():
                portals_data[name] = {
                    'name': portal.name,
                    'selector': portal.selector,
                    'type': portal.portal_type,
                    'strength': portal.strength,
                    'description': portal.description,
                    'wait_for': portal.wait_for,
                    'expect_navigation': portal.expect_navigation
                }

            return web.json_response({
                'success': True,
                'portals': portals_data,
                'total_portals': len(portals_data),
                'page': 'amazon-gaming-laptop-search'
            })

        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def handle_get_mermaid_diagram(self, request):
        """
        GET /amazon/mermaid-diagram?type=flowchart|portal_map
        Return Mermaid diagram code
        """
        try:
            diagram_type = request.query.get('type', 'flowchart')

            if diagram_type == 'portal_map':
                diagram = AmazonGamingLaptopAnalyzer.generate_portal_mapping_diagram()
            else:  # Default to flowchart
                diagram = AmazonGamingLaptopAnalyzer.generate_mermaid_flowchart()

            return web.json_response({
                'success': True,
                'diagram_type': diagram_type,
                'mermaid_code': diagram,
                'rendered_url': f'https://mermaid.live/edit#pako/...',
                'usage': 'Paste mermaid_code into Mermaid Live Editor or markdown'
            })

        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def handle_extract_product_cards(self, request):
        """
        POST /amazon/extract-products
        Extract all product cards from current results page
        """
        try:
            if not self.browser_server.page:
                return web.json_response({'error': 'No page loaded'}, status=400)

            products = await self.browser_server.page.evaluate('''
            () => {
                const products = [];
                document.querySelectorAll('.s-result-item').forEach(item => {
                    products.push({
                        asin: item.getAttribute('data-asin'),
                        title: item.querySelector('h2 span')?.textContent?.trim(),
                        price: item.querySelector('.a-price-whole')?.textContent?.trim(),
                        rating: item.querySelector('.a-star-small span')?.textContent?.trim(),
                        reviewCount: item.querySelector('[aria-label*="review"]')?.textContent?.trim(),
                        isPrime: !!item.querySelector('i.a-icon-prime'),
                        isSponsored: !!item.querySelector('[aria-label*="Sponsored"]'),
                        detailPageUrl: item.querySelector('h2 a')?.href
                    });
                });
                return products;
            }
            ''')

            return web.json_response({
                'success': True,
                'product_count': len(products),
                'products': products,
                'extracted_at': datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Error extracting products: {e}")
            return web.json_response({'error': str(e)}, status=500)


# Integration helper function
def setup_amazon_portal_routes(app, browser_server):
    """
    Register Amazon portal routes with aiohttp application

    Usage in persistent_browser_server.py:
        from amazon_gaming_laptop_portal import setup_amazon_portal_routes
        # In __init__ or setup_routes():
        setup_amazon_portal_routes(self.app, self)
    """
    handler = AmazonPortalHTTPHandler(browser_server)

    app.router.add_post('/analyze-amazon-page', handler.handle_analyze_amazon_page)
    app.router.add_get('/amazon/portal-mapping', handler.handle_get_portal_mapping)
    app.router.add_get('/amazon/mermaid-diagram', handler.handle_get_mermaid_diagram)
    app.router.add_post('/amazon/extract-products', handler.handle_extract_product_cards)

    logger.info("Amazon portal routes registered")
