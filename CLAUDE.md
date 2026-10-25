# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`ilc-provider` is a Faker provider that generates fake instances of the `ilc-models` data models (players, teams, matches, leagues, etc.). Python >=3.12, managed with `uv`, built with hatchling. The project aims to keep 100% test coverage (see the coverage badge in the README).

## Commands

Tasks are defined in the `justfile`:

- `just test` — run the test suite (`uv run pytest`)
- `uv run pytest tests/test_provider.py::test_name` — run a single test
- `just cov` — tests with coverage, then regenerates the coverage badge
- `just check` — `ruff check --fix`, `ruff format`, and `ty check` (via `uvx`)
- `just tox` — test matrix across Python 3.12–3.14 plus lowest/highest dependency resolutions
- `just docs` — build Sphinx docs (warnings are errors) into `docs/build/html`
- `just bump` — bump patch version with bumpver. The version lives in `pyproject.toml`, `README.md` badge, `src/ilc_provider/__init__.py` (`__version__`) and `docs/source/conf.py`; bumpver keeps them in sync, so don't edit them by hand.
- `just upgrade` — upgrades the lockfile, re-exports `docs/requirements.txt` (used by Read the Docs) and runs `tox`

Tests run with `pytest-randomly`, so test order is shuffled; tests must not depend on order or on a particular random seed. For the same reason, branches that only some seeds reach are marked `# pragma: no cover` so the coverage figure doesn't vary with the seed; keep that convention.

## Architecture

The whole package is a single module, `src/ilc_provider/__init__.py`:

- Importing it creates a module-level `fake = Faker()` and registers `ILCProvider` on it (`fake.add_provider(ILCProvider)` at the bottom of the file). Users do `from ilc_provider import fake` and call `fake.league()`, `fake.match()`, etc.
- `ILCProvider(BaseProvider)` holds the generator methods. They build on each other: `league()` creates teams (`team()` → `squad()`) and a round-robin schedule, calls `kickoff()` for each fixture's time and `match()` for every fixture, and uses `League.table()` from `ilc-models` to pick the post-split sections; `match()` uses `lineups()`, `sub_window()`/`substitution()`, `card()`, `goal()` and `event_time()`. `table_row()` is a standalone generator for `TableRow` and is not called by the other methods.
- Helper classes `SquadPlayer` and `Team` wrap `ilc_models` objects with extra generation-only state (e.g. selection/scorer weights used to pick lineups and goal scorers). They call back into the module-level `fake` rather than into the provider instance.
- Module-level helpers (`match_schedule`, `invert_schedule`, `players_on`, `_years_before`, `_unique_choices`) are used by the provider methods for scheduling, player selection and dates of birth.
- Player IDs, match IDs, league IDs and team names are drawn through `fake.unique`, which remembers values for the life of the process; `tests/conftest.py` clears it before every test.
- Generated objects are the models from the `ilc-models` dependency; changes to those models may require changes here.
- Docs are Sphinx (`docs/source`, `api.rst` documents the module via docstrings), so public methods need Google-style docstrings (`Args:`/`Returns:`, rendered by napoleon).
