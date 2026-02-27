#!/bin/bash

cd "$(dirname "$0")/../../.."   # Go to repo root
export PYTHONPATH="$PWD"
venv/bin/python -m src.bot.daily.daily_top_ten

echo "Script completed."
