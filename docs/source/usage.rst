Usage
=====

*ilc_provider* can be used as a `Pytest <https://docs.pytest.org/>`_ fixture::

    # conftest.py

    import pytest
    from ilc_provider import fake

    # Any element of the provider can be accessed
    # from this fixture:
    @pytest.fixture(scope="session")
    def ilc_fake():
        return fake

    # A fake league is intensive to set up, so it is
    # usually best to make a session-scoped league fixture:
    @pytest.fixture(scope="session")
    def fake_league(ilc_fake):
        return ilc_fake.league()

Use as you would any other fixture::

    # test_fixtures.py

    def test_fake(ilc_fake):
        player = ilc_fake.player()
        assert player.name

    def test_fake_league(fake_league):
        assert fake_league.matches
