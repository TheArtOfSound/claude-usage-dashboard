#!/bin/bash
# Update Claude Code usage data and push to GitHub
set -e

cd "$(dirname "$0")/.."

echo "Exporting daily data..."
npx ccusage@latest daily --json > data/daily.json

echo "Exporting session data..."
npx ccusage@latest session --json > data/sessions.json

echo "Exporting monthly data..."
npx ccusage@latest monthly --json > data/monthly.json

echo "Merging into usage.json..."
python3 scripts/merge.py

echo "Committing and pushing..."
git add data/
git commit -m "Update usage data $(date +%Y-%m-%d)" || echo "No changes to commit"
git push origin main

echo "Done. Dashboard will update on GitHub Pages."
