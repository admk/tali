default:
    @just --list

lint:
    isort .
    ruff check --fix
    ruff format

test:
    python -m unittest discover -s tests

build:
    python -m build

install:
    uv tool install --force-reinstall -e .

release:
    twine upload dist/*

all: lint test build
