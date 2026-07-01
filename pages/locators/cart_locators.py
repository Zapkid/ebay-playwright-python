"""Locators for the eBay cart page."""

from __future__ import annotations


class CartLocators:
    CART_URL: str = "https://cart.ebay.com"
    ITEM_ROW: str = (
        ".cart-bucket-line-item, "
        "[data-test-id='line-item'], "
        "div.cart-bucket-line-item, "
        "li.cart-bucket-line-item"
    )
    ITEM_TITLE: str = (
        "a[data-test-id='item-title'], "
        ".item-title, "
        "a.it-ttl, "
        "a[href*='/itm/']"
    )
    ITEM_PRICE: str = (
        ".item-price, "
        "span[data-test-id='item-price'], "
        ".cart-item-price, "
        ".cart-bucket-line-item-price, "
        "[class*='item-price']"
    )
    ITEM_QUANTITY: str = (
        "input[data-test-id='quantity-input'], "
        "input[name='quantity'], "
        "[class*='quantity'] input"
    )
    LISTING_LINK: str = "a[href*='/itm/']"
    ORDER_SUMMARY: str = "text=Order summary"
    SUBTOTAL: str = (
        "[data-test-id='TOTAL'], "
        ".cart-subtotal, "
        "div.cart-summary-subtotal"
    )
    CHECKOUT_BTN: str = (
        "button:has-text('Go to checkout'), "
        "a:has-text('Go to checkout'), "
        "button:has-text('Checkout'), "
        "a:has-text('Checkout')"
    )
    EMPTY_CART: str = (
        "h1:has-text('Your shopping cart is empty'), "
        "div:has-text('shopping cart is empty'), "
        "div:has-text(\"You don't have any items in your cart\")"
    )
