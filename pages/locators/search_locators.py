"""Locators for eBay search results pages."""

from __future__ import annotations


class SearchLocators:
    PRODUCT_CARDS: str = "li.s-item"
    PRODUCT_CARD_FALLBACK: str = "li:has(a[href*='/itm/'])"
    CARD_LINK: str = "a.s-item__link, a[href*='/itm/']"
    CARD_PRICE: str = ".s-card__price, .s-item__price, .s-item__detail--primary .s-item__price"
    CARD_TITLE: str = ".s-item__title span[role='heading'], .s-item__title"
    NEXT_PAGE: str = "a.pagination__next, nav[role='navigation'] a:has-text('Next')"
    PREV_PAGE: str = "a.pagination__prev, nav[role='navigation'] a:has-text('Previous')"
