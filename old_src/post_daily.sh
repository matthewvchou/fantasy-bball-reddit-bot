#!/bin/bash
# EMERGENCY BACKUP: scrapes Basketball Monster (headless Chrome) and posts the daily top 10.
# Usage: ./old_src/post_daily.sh   (can be run from anywhere)

# Run from old_src (flat imports), using the repo's venv
OLD_SRC="$(cd "$(dirname "$0")" && pwd)"
cd "$OLD_SRC"
"$OLD_SRC/../venv/bin/python" daily_top_ten.py

echo "Script completed."
