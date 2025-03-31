Usage
=====

*ilc_provider* can be used as a `Pytest <https://docs.pytest.org/>`_ fixture::

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
