"""Reusable verification helpers — raise ``AssertionError`` with clear messages."""

from __future__ import annotations

from collections.abc import Collection, Sized


def verify(condition: bool, message: str) -> None:
    """Raise ``AssertionError`` when *condition* is false."""
    if not condition:
        raise AssertionError(message)


def verify_true(condition: bool, message: str) -> None:
    """Require *condition* to be true."""
    verify(condition, message)


def verify_not_empty(value: Collection[object] | Sized | str, message: str) -> None:
    """Require a non-empty collection or string."""
    verify(bool(value), message)


def verify_positive(value: float | int, message: str) -> None:
    """Require *value* to be greater than zero."""
    verify(value > 0, message)


def verify_equal(actual: object, expected: object, message: str | None = None) -> None:
    """Require *actual* to equal *expected*."""
    if message is None:
        message = f"Expected {expected!r}, got {actual!r}"
    verify(actual == expected, message)


def verify_greater_than_or_equal(
    actual: float | int,
    minimum: float | int,
    message: str,
) -> None:
    """Require *actual* >= *minimum*."""
    verify(actual >= minimum, message)


def verify_less_than_or_equal(
    actual: float | int,
    maximum: float | int,
    message: str,
) -> None:
    """Require *actual* <= *maximum*."""
    verify(actual <= maximum, message)


def verify_within_tolerance(
    actual: float,
    expected: float,
    tolerance: float,
    message: str | None = None,
) -> None:
    """Require *actual* to be within *tolerance* of *expected*."""
    diff: float = abs(actual - expected)
    if message is None:
        message = (
            f"Expected {expected:.2f} ± {tolerance:.2f}, "
            f"got {actual:.2f} (diff ${diff:.2f})"
        )
    verify(diff <= tolerance, message)


def verify_contains(haystack: str, needle: str, message: str | None = None) -> None:
    """Require *needle* to appear in *haystack*."""
    if message is None:
        message = f"Expected {needle!r} in {haystack!r}"
    verify(needle in haystack, message)
