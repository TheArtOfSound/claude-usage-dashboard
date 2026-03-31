#!/bin/bash
# Update Claude Code usage data and push to GitHub
#
# Usage:
#   bash scripts/update.sh                              # single machine
#   bash scripts/update.sh --machine2 data/m2           # merge with second machine
#   bash scripts/update.sh --machine2 /path/to/exports  # absolute path
set -e

cd "$(dirname "$0")/.."

# Parse args — pass everything through to merge.py
MERGE_ARGS=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --machine2)
            MERGE_ARGS="--machine2 $2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: bash scripts/update.sh [--machine2 <dir>]"
            exit 1
            ;;
    esac
done

echo "Exporting daily data..."
npx ccusage@latest daily --json > data/daily.json

echo "Exporting session data..."
npx ccusage@latest session --json > data/sessions.json

echo "Exporting monthly data..."
npx ccusage@latest monthly --json > data/monthly.json

echo "Merging into usage.json..."
python3 scripts/merge.py $MERGE_ARGS

echo "Committing and pushing..."
git add data/
git commit -m "Update usage data $(date +%Y-%m-%d)" || echo "No changes to commit"
git push origin main

echo "Done. Dashboard will update on GitHub Pages."
