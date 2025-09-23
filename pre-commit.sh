#!/bin/sh

mypy . || exit 1
pylint pom_parser/__init__.py || exit 1
which doxygen >/dev/null && { doxygen || exit 1; }
python -m unittest tests || exit 1
