#!/bin/sh

mypy . || exit 1
pylint pom_parser/__init__.py || exit 1
