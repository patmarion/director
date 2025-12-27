#!/bin/bash

cd $(dirname $0)
uv run --all-extras python manage_docs.py build