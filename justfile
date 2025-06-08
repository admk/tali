default:
    @just --list

test:
    python -m unittest discover -s tests

build:
    rm -rf dist && python -m build

install:
    uv tool install -U .

release:
    twine upload dist/*

all: test build install release
