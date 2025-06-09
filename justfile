default:
    @just --list

lint:
    isort --atomic --py=311 -m VERTICAL_HANGING_INDENT .
    ruff check --fix
    ruff format

test:
    python -m unittest discover -s tests

build:
    rm -rf dist && python -m build

install:
    uv tool install -U .

release:
    twine upload dist/*

all: test build install release
