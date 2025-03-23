### ilc-provider

**Faker provider for *ILC* data models**

Generates fake data for all data models: players, teams, leagues, etc.

When imported the *ilc_provider* package creates a 
[Faker](https://github.com/joke2k/faker/) instance
and adds itself as a provider. It can then be called
like any other provider::

    from ilc_provider import fake
    league = fake.league()

See the documentation for the full list of data that can be generated.

## Installation

    (.venv) $ pip install ilc-provider


