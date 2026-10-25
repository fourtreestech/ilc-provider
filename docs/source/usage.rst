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


Users
-----

Fake users can be generated too. Any of ``email``, ``password``,
``username`` and ``status`` can be supplied; the rest are generated.
Generated emails (and the usernames derived from them) are unique::

    user = ilc_fake.user(status="active")
    assert user.username == user.email.split("@")[0]

Hashing a password with Argon2 is deliberately slow. When generating many
users, hash once and reuse the hash::

    password_hash = ilc_fake.user().password_hash
    users = [ilc_fake.user(password_hash=password_hash) for _ in range(100)]
