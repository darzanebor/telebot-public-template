#!/usr/bin/env bash
export PATH=~/.local/bin:$PATH
./main.py
exec "$@"
