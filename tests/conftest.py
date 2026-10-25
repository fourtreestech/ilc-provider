import pytest

from ilc_provider import fake


@pytest.fixture(autouse=True)
def clear_unique():
    # pytest-randomly reseeds `random` before every test, so each test draws
    # the same IDs - forget what `fake.unique` has seen in earlier tests
    fake.unique.clear()
