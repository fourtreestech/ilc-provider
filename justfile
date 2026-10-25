# Read version from pyproject.toml
version := `grep '^version = "' pyproject.toml | cut -d'"' -f2`

# Default: list available tasks
default:
    @just --list

# Lint and type-check
check:
    uvx ruff check . --fix && uvx ruff format .
    uvx ty check .

# Run tests
test:
    uv run pytest

# Run tests with coverage and update coverage badge
cov:
    uv run pytest --cov --cov-report term-missing --cov-report json
    uv run cov-badge

# Upgrade dependencies
upgrade:
    uv lock --upgrade
    uv sync
    uv export --no-default-groups --group docs --no-emit-project --no-hashes --no-header --no-annotate -q > docs/requirements.txt
    uvx tox

# Run tox
tox:
    uvx tox

# Build the docs
docs:
    uv run --group docs sphinx-build -W --keep-going -b html docs/source docs/build/html

# Bump patch version
bump:
    uvx bumpver update --patch

# Merge dev into main and push
sync:
    git switch main
    git pull origin main
    git merge --ff-only dev
    git push -u origin main
    git switch dev

# Add version tag
tag:
    git switch main
    git tag -a v{{version}} -m 'v{{version}}'
    git push origin v{{version}}
    git switch dev

# Build and publish to PyPI
publish:
    rm -rf dist
    uv build
    UV_PUBLISH_TOKEN="$(cat .pypi.token)" uv publish
