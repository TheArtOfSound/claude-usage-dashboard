# Claude Code Usage Dashboard

**Live:** [theartofsound.github.io/claude-usage-dashboard](https://theartofsound.github.io/claude-usage-dashboard)

A 3D animated, immersive data visualization of my Claude Code token usage and costs. Updated periodically with fresh data from [ccusage](https://github.com/ryoppippi/ccusage).

## The Numbers

| Metric | Value |
|--------|-------|
| Total tokens | 9.3 billion |
| Total cost | $6,865 |
| Days active | 32 |
| Sessions | 32 |
| Daily burn rate | $215/day |
| Annual projection | $78,314/year |
| vs Max plan ($200/mo) | **32x** |
| vs average dev ($6/day) | **19x** |
| vs 90th percentile ($12/day) | **9.5x** |
| Estimated percentile | **Top 0.01-0.1%** |

## Why I Built This

I'm Bryan Leonard. I run Qira LLC out of Phoenix, Arizona. Over the last two months I've used Claude Code to simultaneously build:

- **Codey** -- a full SaaS coding AI with structural health analysis, 22,000+ lines of Python, 18 pages, 73 API endpoints
- **EGC (Expression-Gated Consciousness)** -- a theoretical physics framework on consciousness with a live study at 43+ subjects
- **NFET** -- a traffic flow simulation validated on real city networks (Phoenix, LA, Chicago)
- **Vol-bot** -- a volume analysis trading bot
- **Armo, Roro, Ani** -- various other projects

9.3 billion tokens is what building all of that simultaneously looks like. $6,865 in compute over 32 days. That's 32x what the Max plan costs. Not because I'm wasteful -- because I'm building things that matter and Claude Code is the tool that keeps up.

This dashboard exists because I wanted to see what that actually looks like as data. And because I think more people should be transparent about what real AI-assisted development costs and produces.

## What's Visualized

- **3D Particle Globe** -- each particle represents 1M tokens, color-coded by type
- **Daily Usage Timeline** -- cost and token bars for every active day
- **Model Breakdown** -- Opus vs Haiku vs Sonnet distribution
- **Project Breakdown** -- cost per project (Codey, EGC, NFET, Vol-bot, etc.) with per-machine toggle
- **Burn Rate Projection** -- daily, monthly, annual cost trajectory
- **Cost Heatmap** -- GitHub-style calendar colored by daily spend
- **Token Flow** -- horizontal bar showing input/output/cache distribution
- **Session Explorer** -- all sessions ranked by cost with model details and machine attribution
- **Comparison** -- concrete numbers vs Claude Max plan pricing

## Tech Stack

Single HTML file, zero build step:
- **Three.js** (CDN) -- 3D particle globe
- **Chart.js** (CDN) -- all 2D charts
- **Vanilla JS** -- data loading, animated counters, interactivity
- **CSS** -- dark theme, glassmorphism, responsive

## Updating the Data

### Single machine

```bash
# Run from repo root
bash scripts/update.sh
```

This exports fresh data from ccusage, merges it with project inference, commits, and pushes. The GitHub Pages site updates automatically.

### Adding a second machine

If you're running Claude Code on two machines and want combined usage data:

**Step 1: Export data on the second machine**

```bash
# On the second machine (wherever Claude Code session logs live in ~/.claude/)
npx ccusage@latest daily --json > daily_machine2.json
npx ccusage@latest session --json > sessions_machine2.json
npx ccusage@latest monthly --json > monthly_machine2.json
```

**Step 2: Copy the exports into the repo**

Copy the three JSON files into a directory inside the repo. For example:

```bash
mkdir -p data/m2
# Copy daily_machine2.json, sessions_machine2.json, monthly_machine2.json into data/m2/
```

Or use any path -- USB drive, scp, cloud sync, whatever.

**Step 3: Run the merge**

```bash
# From the repo root on your primary machine
python3 scripts/merge.py --machine2 data/m2
```

This will:
- Load machine 1 data from `data/daily.json`, `data/sessions.json`, `data/monthly.json`
- Load machine 2 data from the specified directory
- Deduplicate sessions by sessionId (no double-counting)
- Combine daily totals (same date = summed, different dates = union)
- Combine monthly aggregates
- Output a single `data/usage.json` with per-machine metadata

**Step 4: Push to GitHub**

```bash
git add data/
git commit -m "Update usage data with both machines $(date +%Y-%m-%d)"
git push origin main
```

Or use the combined script:

```bash
bash scripts/update.sh --machine2 data/m2
```

### What the merge handles

- **Session deduplication**: Sessions are matched by `sessionId`. If both machines somehow have the same session, it's counted once.
- **Daily merging**: If both machines have data for the same date, the token counts and costs are summed. Model breakdowns are combined.
- **Monthly merging**: Same-month records are summed.
- **Machine attribution**: Each session is tagged with its source machine. The dashboard shows which machines contributed data and when each was last synced.
- **Per-machine toggle**: The Project Breakdown chart has a toggle to view Combined / Machine 1 only / Machine 2 only.

### File naming

The merge script looks for files with these names in the `--machine2` directory:

| Priority | Filename |
|----------|----------|
| 1st | `daily_machine2.json` |
| 2nd | `daily.json` |

Same pattern for `sessions_machine2.json`/`sessions.json` and `monthly_machine2.json`/`monthly.json`.

### Machine labels

Edit `MACHINE1_LABEL` and `MACHINE2_LABEL` at the top of `scripts/merge.py` to customize the names shown on the dashboard (defaults: "Bryan" and "Brandyn").

## Data Source

All data comes from [ccusage](https://github.com/ryoppippi/ccusage) which reads Claude Code's local JSONL session files. No API keys or network access required for the analysis -- ccusage works entirely offline against local data.

---

Bryan Leonard -- [bryan@qira.ai](mailto:bryan@qira.ai) -- Qira LLC -- Phoenix, Arizona -- 2026
