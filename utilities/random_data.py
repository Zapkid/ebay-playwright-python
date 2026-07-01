"""Random test-data generators backed by Faker."""

from __future__ import annotations

import random
import string

from faker import Faker

_faker = Faker("en_US")


def short_name(max_len: int = 12) -> str:
    """A plausible first-name string suitable for personalisation fields."""
    return _faker.first_name()[:max_len]


def short_phrase(words: int = 3) -> str:
    """A short random phrase for open-text personalisation inputs."""
    return " ".join(_faker.words(words))


def random_alphanumeric(length: int = 8) -> str:
    """Purely alphanumeric string — useful for reference codes."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def random_initials() -> str:
    """Two or three uppercase initials."""
    return "".join(random.choices(string.ascii_uppercase, k=random.randint(2, 3)))
