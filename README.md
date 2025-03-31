### ilc-provider

![version](https://img.shields.io/badge/version-0.1.0-blue)
![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Ffourtreestech%2Filc-provider%2Fmain%2Fpyproject.toml)
![coverage](https://img.shields.io/badge/coverage-100%25-green)

**Faker provider for *ILC* data models**

Generates fake data for all data models: players, teams, leagues, etc.

When imported the *ilc_provider* package creates a 
[Faker](https://github.com/joke2k/faker/) instance
and adds itself as a provider. It can then be called
like any other provider:

    from ilc_provider import fake
    league = fake.league()

See the documentation for the full list of data that can be generated.

## Installation

    (.venv) $ pip install ilc-provider

## Usage

*ilc_provider* can be used as a [Pytest](https://docs.pytest.org/) fixture:

    # conftest.py

    import pytest
    from ilc_provider import fake

    # Any element of the provider can be accessed
    # from this fixture:
    # match = ilc_fake.match()
    @pytest.fixture(scope="session")
    def ilc_fake():
        return fake

    # A fake league is intensive to set up, so it is
    # usually best to make a session-scoped league fixture:
    @pytest.fixture(scope="session")
    def fake_league(ilc_fake):
        return ilc_fake.league()

