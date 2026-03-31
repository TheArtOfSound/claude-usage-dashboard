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
| Estimated percentile | **Top 0.1%** |

## Why I Built This

I'm Bryan Leonard. I run Qira LLC out of Phoenix, Arizona. Over the last two months I've used Claude Code to simultaneously build:

- **Codey** — a full SaaS coding AI with structural health analysis, 22,000+ lines of Python, 18 pages, 73 API endpoints
- **EGC (Expression-Gated Consciousness)** — a theoretical physics framework on consciousness with a live study at 43+ subjects
- **NFET** — a traffic flow simulation validated on real city networks (Phoenix, LA, Chicago)
- **Vol-bot** — a volume analysis trading bot
- **Armo, Roro, Ani** — various other projects

9.3 billion tokens is what building all of that simultaneously looks like. $6,865 in compute over 32 days. That's 32x what the Max plan costs. Not because I'm wasteful — because I'm building things that matter and Claude Code is the tool that keeps up.

This dashboard exists because I wanted to see what that actually looks like as data. And because I think more people should be transparent about what real AI-assisted development costs and produces.

## What's Visualized

- **3D Particle Globe** — each particle represents 1M tokens, color-coded by type
- **Daily Usage Timeline** — cost and token bars for every active day
- **Model Breakdown** — Opus vs Haiku vs Sonnet distribution
- **Project Breakdown** — cost per project (Codey, EGC, NFET, Vol-bot, etc.)
- **Burn Rate Projection** — daily, monthly, annual cost trajectory
- **Cost Heatmap** — GitHub-style calendar colored by daily spend
- **Token Flow** — horizontal bar showing input/output/cache distribution
- **Session Explorer** — all 32 sessions ranked by cost with model details
- **Comparison** — concrete numbers vs Claude Max plan pricing

## Tech Stack

Single HTML file, zero build step:
- **Three.js** (CDN) — 3D particle globe
- **Chart.js** (CDN) — all 2D charts
- **Vanilla JS** — data loading, animated counters, interactivity
- **CSS** — dark theme, glassmorphism, responsive

## Updating the Data

```bash
# Run from repo root
bash scripts/update.sh
```

This exports fresh data from ccusage, merges it with project inference, commits, and pushes. The GitHub Pages site updates automatically.

## Data Source

All data comes from [ccusage](https://github.com/ryoppippi/ccusage) which reads Claude Code's local JSONL session files. No API keys or network access required for the analysis — ccusage works entirely offline against local data.

---

Bryan Leonard · [bryan@qira.ai](mailto:bryan@qira.ai) · Qira LLC · Phoenix, Arizona · 2026
