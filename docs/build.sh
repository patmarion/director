#!/bin/bash

cd $(dirname $0)
uv run python manage_docs.py build