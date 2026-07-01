"""Locators for the eBay sign-in page."""

from __future__ import annotations


class LoginLocators:
    SIGN_IN_URL: str = "https://signin.ebay.com/ws/eBayISAPI.dll?SignIn"
    EMAIL_INPUT: str = "#userid, input[name='userid'], input[type='email']"
    CONTINUE_BTN: str = "#signin-continue-btn, button#signin-continue-btn"
    PASSWORD_INPUT: str = "#pass, input[name='pass'], input[type='password']"
    SIGN_IN_BTN: str = "#sgnBt, button#sgnBt, button[type='submit']:has-text('Sign in')"
    ERROR_MSG: str = "div#errormsg, span.error, div[class*='error']"
    LOGGED_IN_SIGNAL: str = "#gh-eb-My, a#gh-eb-My, a[href*='myebay']"
