#!/bin/zsh

echo
echo "Running ruff check..."
uvx ruff check . --fix

echo
echo "Running ruff format..."
uvx ruff format .

echo
echo "Running mypy..."
uv run mypy

echo
echo "Check complete."
echo