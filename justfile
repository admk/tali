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
    uv tool install -U .

release:
    twine upload dist/*

all: lint test build
