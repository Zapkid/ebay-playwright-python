"""Locators for eBay product / listing detail pages."""

from __future__ import annotations


class ProductLocators:
    PRICE: str = (
        ".x-price-primary, "
        "[itemprop='price'], "
        "div.x-bin-price__content, "
        "span[itemprop='price']"
    )
    VARIATION_SELECT: str = "select.msku, select[id*='msku'], select[name*='selector']"
    VARIATION_RADIO: str = (
        "input[type='radio'][name*='msku'], "
        "input[type='radio'][class*='msku'], "
        "input[type='radio'][data-testid*='msku']"
    )
    VARIATION_BUTTON: str = (
        ".x-msku__select-box button, "
        "button.msku-option, "
        "[data-testid='ux-swatch'] button, "
        ".listbox-button__combobox, "
        "button[aria-haspopup='listbox']"
    )
    VARIATION_LISTBOX_OPTION: str = (
        "[role='listbox'] [role='option']:not([aria-disabled='true']), "
        ".listbox__option:not([aria-disabled='true'])"
    )
    REQUIRED_INPUT: str = (
        "input[required]:not([type='hidden']):not([type='submit']), "
        "textarea[required]"
    )
    BUY_BOX: str = "[data-testid='x-item-card'], .x-item-title, .vim.x-item-title"
    MODAL_CONTINUE: str = (
        "button:has-text('Continue shopping'), "
        "a:has-text('Continue shopping'), "
        "button[aria-label='Close dialog']"
    )
    QUANTITY_SELECT: str = (
        "select#qtySelect, "
        "select[name='quantity'], "
        "select[aria-label*='Quantity' i], "
        "#qtySubTxt select"
    )
    QUANTITY_INPUT: str = (
        "input#qtyTextBox, "
        "input[name='quantity'], "
        "input[aria-label*='Quantity' i], "
        "input[type='number'][id*='qty' i], "
        ".x-quantity__input input, "
        "#qtySubTxt input"
    )
    QUANTITY_SCOPE: str = (
        "#qtySubTxt, .x-quantity, #vi-rightSummary, [data-testid='x-item-card']"
    )
