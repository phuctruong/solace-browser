"""Tests for structural_extractor.py — CPU-only page structure extraction."""

import sys
from pathlib import Path

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from structural_extractor import strip_to_structure, _classify_page_type, structure_to_text


# ── Title extraction ────────────────────────────────────────────────

def test_title_extraction():
    html = "<html><head><title>Hello World</title></head><body></body></html>"
    result = strip_to_structure(html)
    assert result["title"] == "Hello World"


def test_title_with_whitespace():
    html = "<html><head><title>  Spaced Title  </title></head></html>"
    result = strip_to_structure(html)
    assert result["title"] == "Spaced Title"


def test_title_missing():
    html = "<html><head></head><body>no title</body></html>"
    result = strip_to_structure(html)
    assert result["title"] == ""


# ── Meta description ────────────────────────────────────────────────

def test_meta_description():
    html = '<html><head><meta name="description" content="A good description of the page for search engines"></head></html>'
    result = strip_to_structure(html)
    assert result["meta_description"] == "A good description of the page for search engines"


def test_meta_description_truncated():
    long_desc = "A" * 300
    html = f'<html><head><meta name="description" content="{long_desc}"></head></html>'
    result = strip_to_structure(html)
    assert len(result["meta_description"]) <= 200


def test_meta_description_missing():
    html = "<html><head></head><body></body></html>"
    result = strip_to_structure(html)
    assert result["meta_description"] == ""


# ── Canonical ────────────────────────────────────────────────────────

def test_canonical_href_first():
    html = '<link href="https://example.com/page" rel="canonical">'
    result = strip_to_structure(html)
    assert result["canonical"] == "https://example.com/page"


def test_canonical_rel_first():
    html = '<link rel="canonical" href="https://example.com/page2">'
    result = strip_to_structure(html)
    assert result["canonical"] == "https://example.com/page2"


def test_canonical_missing():
    html = "<html><head></head></html>"
    result = strip_to_structure(html)
    assert result["canonical"] == ""


# ── Headings ─────────────────────────────────────────────────────────

def test_headings_extraction():
    html = "<h1>Main Title</h1><h2>Section A</h2><h3>Sub B</h3>"
    result = strip_to_structure(html)
    assert result["headings"] == ["Main Title", "Section A", "Sub B"]


def test_headings_strips_inner_tags():
    html = "<h1><span>Styled</span> Title</h1>"
    result = strip_to_structure(html)
    assert result["headings"] == ["Styled Title"]


def test_headings_max_10():
    html = "".join(f"<h2>Heading {i}</h2>" for i in range(20))
    result = strip_to_structure(html)
    assert len(result["headings"]) == 10


def test_headings_empty_skipped():
    html = "<h1></h1><h2>Real</h2><h3>  </h3>"
    result = strip_to_structure(html)
    assert result["headings"] == ["Real"]


# ── Nav links ────────────────────────────────────────────────────────

def test_nav_links():
    html = '<a href="/about">About Us</a><a href="/pricing">Pricing</a>'
    result = strip_to_structure(html)
    assert len(result["nav_links"]) == 2
    assert result["nav_links"][0] == {"text": "About Us", "href": "/about"}


def test_nav_links_max_8():
    html = "".join(f'<a href="/p{i}">Page {i}</a>' for i in range(20))
    result = strip_to_structure(html)
    assert len(result["nav_links"]) == 8


def test_nav_links_skip_template():
    html = '<a href="/ok">Good Link</a><a href="/bad">{template_var}</a>'
    result = strip_to_structure(html)
    assert len(result["nav_links"]) == 1
    assert result["nav_links"][0]["text"] == "Good Link"


# ── CTAs ─────────────────────────────────────────────────────────────

def test_ctas_extraction():
    html = '<button class="btn btn-primary">Sign Up</button>'
    result = strip_to_structure(html)
    assert "Sign Up" in result["ctas"]


def test_ctas_max_5():
    html = "".join(f'<button class="btn">CTA {i}</button>' for i in range(10))
    result = strip_to_structure(html)
    assert len(result["ctas"]) == 5


# ── Page type classification ────────────────────────────────────────

def test_classify_auth():
    html = '<form action="/login"><input name="email"><button>Sign In</button></form>'
    result = strip_to_structure(html)
    assert result["page_type"] == "auth"


def test_classify_blog():
    html = "<article><time>2026-01-01</time><h1>My Post</h1><p>Content</p></article>"
    result = strip_to_structure(html)
    assert result["page_type"] == "blog"


def test_classify_docs():
    html = "<h1>API Reference</h1><code>GET /api/v1/users</code><p>Returns a list of users. Parameters: limit, offset.</p>"
    result = strip_to_structure(html)
    assert result["page_type"] == "docs"


def test_classify_landing():
    html = '<h1>Pricing</h1><p>Choose your plan. Subscription tiers available.</p><button class="btn">Buy Now</button><button class="btn">Free Trial</button>'
    result = strip_to_structure(html)
    assert result["page_type"] == "landing"


def test_classify_other():
    html = "<html><body><p>Just a paragraph.</p></body></html>"
    result = strip_to_structure(html)
    assert result["page_type"] == "other"


# ── Empty / malformed HTML ──────────────────────────────────────────

def test_empty_html():
    result = strip_to_structure("")
    assert result["title"] == ""
    assert result["meta_description"] == ""
    assert result["canonical"] == ""
    assert result["headings"] == []
    assert result["nav_links"] == []
    assert result["ctas"] == []
    assert result["page_type"] == "other"


def test_malformed_html():
    html = "<h1>Unclosed heading<h2>Another<p>Random tags"
    result = strip_to_structure(html)
    assert isinstance(result, dict)
    assert "page_type" in result


# ── structure_to_text ────────────────────────────────────────────────

def test_structure_to_text_full():
    structure = {
        "title": "Test Page",
        "meta_description": "A test",
        "canonical": "https://example.com",
        "headings": ["H1", "H2"],
        "nav_links": [{"text": "Home", "href": "/"}],
        "ctas": ["Buy Now"],
        "page_type": "landing",
    }
    text = structure_to_text(structure)
    assert "TITLE: Test Page" in text
    assert "META: A test" in text
    assert "CANONICAL: https://example.com" in text
    assert "H: H1" in text
    assert "H: H2" in text
    assert "LINK: Home -> /" in text
    assert "CTA: Buy Now" in text
    assert "TYPE: landing" in text


def test_structure_to_text_empty():
    structure = {
        "title": "",
        "meta_description": "",
        "canonical": "",
        "headings": [],
        "nav_links": [],
        "ctas": [],
        "page_type": "other",
    }
    text = structure_to_text(structure)
    assert "TYPE: other" in text
    assert "TITLE" not in text
