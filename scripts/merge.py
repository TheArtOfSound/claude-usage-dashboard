"""Merge ccusage JSON exports into a single usage.json with project inference."""
import json
import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
CLAUDE_DIR = Path.home() / ".claude"

# Keyword lists for content-based project detection
EGC_KEYWORDS = ['egcstudy', 'egcrate', 'thegate', 'egc', 'expression-gated',
    'r_proxy', 't_drop', 'egc_responses', 'aronson', 'consciousness', 'rater',
    'compressor', 'expander', 'suppressor', 'pearson', 'comfort_gap', 'zenodo',
    'three types', 'schmader', 'pennebaker', 'inzlicht', 'stereotype threat',
    'preprint', 'egc_', 'p_proxy', 'writing_language']

NFET_KEYWORDS = ['nfet', 'kuramoto', 'oscillator', 'bpr', 'az511', 'az-511',
    'traffic', 'kappa', 'ridge_atlas', 'nfet_server', 'nfet_core', 'corridor']

CODEY_KEYWORDS = ['codey', 'vscode-extension', 'saas', 'stripe', 'pricing page',
    'frontend/src', 'codey/codey']

LOLM_KEYWORDS = ['lolm', 'tpu', 'xla', 'fsdp', 'torch_xla', 'c4 dataset', 'qira-hq']


def scan_session_content(project_dir):
    """Scan JSONL session files and return proportional project split."""
    sessions_dir = CLAUDE_DIR / "projects" / project_dir
    if not sessions_dir.exists():
        return None

    totals = {"egc": 0, "nfet": 0, "codey": 0, "lolm": 0, "other": 0, "total": 0}

    for fname in os.listdir(sessions_dir):
        if not fname.endswith(".jsonl"):
            continue
        try:
            with open(sessions_dir / fname) as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        msg = data.get("message", {})
                        text = ""
                        if isinstance(msg, dict):
                            content = msg.get("content", "")
                            if isinstance(content, str):
                                text = content
                            elif isinstance(content, list):
                                for c in content:
                                    if isinstance(c, dict) and c.get("type") == "text":
                                        text += c.get("text", "")
                        if not text:
                            continue
                        chars = len(text)
                        totals["total"] += chars
                        tl = text.lower()
                        if any(kw in tl for kw in EGC_KEYWORDS):
                            totals["egc"] += chars
                        elif any(kw in tl for kw in NFET_KEYWORDS):
                            totals["nfet"] += chars
                        elif any(kw in tl for kw in CODEY_KEYWORDS):
                            totals["codey"] += chars
                        elif any(kw in tl for kw in LOLM_KEYWORDS):
                            totals["lolm"] += chars
                        else:
                            totals["other"] += chars
                    except:
                        continue
        except:
            continue

    if totals["total"] == 0:
        return None
    return {k: v / totals["total"] for k, v in totals.items() if k != "total"}


def split_session(session, proportions):
    """Split a single aggregated session into multiple virtual sessions by proportion."""
    splits = []
    proj_names = {"egc": "EGC", "nfet": "NFET", "codey": "Codey / Nous", "lolm": "LOLM / Latent", "other": "Other (nous)"}
    for key, pct in proportions.items():
        if pct < 0.01:  # skip < 1%
            continue
        virtual = dict(session)
        virtual["sessionId"] = f"{session['sessionId']}--{key}"
        virtual["totalTokens"] = int(session["totalTokens"] * pct)
        virtual["totalCost"] = session["totalCost"] * pct
        virtual["inputTokens"] = int(session.get("inputTokens", 0) * pct)
        virtual["outputTokens"] = int(session.get("outputTokens", 0) * pct)
        virtual["cacheCreationTokens"] = int(session.get("cacheCreationTokens", 0) * pct)
        virtual["cacheReadTokens"] = int(session.get("cacheReadTokens", 0) * pct)
        virtual["_split_project"] = proj_names.get(key, key)
        virtual["_split_pct"] = round(pct * 100, 1)
        splits.append(virtual)
    return splits


def infer_project(session):
    """Infer project name from session path, ID, or any available field."""
    # Check for content-based split override
    if "_split_project" in session:
        return session["_split_project"]

    path = session.get("projectPath", "")
    sid = session.get("sessionId", "")

    if not path and not sid:
        return "Unknown"

    # Map known directory names to project names
    project_map = {
        "nous": "Codey / Nous",
        "codey": "Codey",
        "egcstudy": "EGC Study",
        "nfet": "NFET",
        "armo": "Armo",
        "roro": "Roro",
        "ani": "Ani",
        "capstone": "Capstone",
        "vol-bot": "Vol-bot",
        "vol_bot": "Vol-bot",
        "latent": "Latent",
        "capitalcore": "CapitalCore",
        "new-project": "New Project",
        "new_project": "New Project",
        "liecnesing": "Licensing Dashboard",
        "licensing": "Licensing Dashboard",
        "dahbaord": "Licensing Dashboard",
        "cli": "CLI Tool",
        "bryan": "BRYAN (Personal)",
    }

    # Check subagent first — use parent path for project name
    if "subagent" in sid.lower():
        # Path contains the parent project, e.g. '-Users-bry-Documents-Vol-bot/session-id'
        search_str = path.lower().replace("-", " ").replace("/", " ")
        for key, proj in project_map.items():
            if key.replace("-", " ") in search_str:
                return f"{proj} (subagent)"
        return "Subagent"

    # Combine path and sessionId for searching — sessionId often has
    # the real path encoded as dashes, e.g. '-Users-bry-Documents-Vol-bot'
    search_strs = []
    if path and path != "Unknown Project":
        search_strs.append(path.lower())
    if sid:
        # Convert dash-encoded paths: -Users-bry-Documents-Vol-bot -> users bry documents vol bot
        search_strs.append(sid.lower().replace("-", " ").replace("/", " "))

    for search_str in search_strs:
        for key, proj in project_map.items():
            if key.replace("-", " ") in search_str or key in search_str:
                # Check for worktree suffix
                if "worktree" in search_str:
                    return f"{proj} (worktree)"
                return proj

    # Fallback: try to extract a meaningful name from sessionId
    if sid:
        # Pattern: -Users-bry-{project-name} or -Users-bry-Documents-{project-name}
        parts = sid.split("-")
        # Remove known prefixes
        clean = [p for p in parts if p and p.lower() not in ("users", "bry", "documents", "claude", "worktrees", "wor")]
        if clean:
            # Take the first meaningful part
            name = clean[0]
            if len(name) > 3 and not all(c in "0123456789abcdef" for c in name):
                return name.title()

    return "Unknown"


def main():
    daily = json.loads((DATA_DIR / "daily.json").read_text())
    sessions = json.loads((DATA_DIR / "sessions.json").read_text())
    monthly = json.loads((DATA_DIR / "monthly.json").read_text())

    daily_list = daily.get("daily", [])
    raw_sessions = sessions.get("sessions", [])
    monthly_list = monthly.get("monthly", [])

    # Content-based splitting for multi-project directories
    session_list = []
    for s in raw_sessions:
        sid = s.get("sessionId", "")
        # Split the nous directory session using content analysis
        if sid == "-Users-bry-nous":
            props = scan_session_content("-Users-bry-nous")
            if props:
                splits = split_session(s, props)
                session_list.extend(splits)
                print(f"Split nous session (${s['totalCost']:.2f}) into {len(splits)} projects:")
                for sp in splits:
                    print(f"  {sp['_split_project']}: ${sp['totalCost']:.2f} ({sp['_split_pct']}%)")
                continue
        session_list.append(s)

    # Calculate totals
    total_tokens = sum(d["totalTokens"] for d in daily_list)
    total_cost = sum(d["totalCost"] for d in daily_list)
    days_active = len(daily_list)
    num_sessions = len(session_list)

    # Peak day
    peak = max(daily_list, key=lambda d: d.get("totalCost", 0)) if daily_list else {}

    # Model totals
    model_totals = {}
    for d in daily_list:
        for mb in d.get("modelBreakdowns", []):
            name = mb["modelName"]
            if name not in model_totals:
                model_totals[name] = {"tokens": 0, "cost": 0}
            model_totals[name]["tokens"] += (
                mb.get("inputTokens", 0) + mb.get("outputTokens", 0)
                + mb.get("cacheCreationTokens", 0) + mb.get("cacheReadTokens", 0)
            )
            model_totals[name]["cost"] += mb.get("cost", 0)

    # Token type totals
    input_total = sum(d.get("inputTokens", 0) for d in daily_list)
    output_total = sum(d.get("outputTokens", 0) for d in daily_list)
    cache_create_total = sum(d.get("cacheCreationTokens", 0) for d in daily_list)
    cache_read_total = sum(d.get("cacheReadTokens", 0) for d in daily_list)

    # Burn rate
    avg_daily = total_cost / max(days_active, 1)
    monthly_projection = avg_daily * 30
    annual_projection = avg_daily * 365

    # Max plan comparison
    max_plan_monthly = 200
    max_plan_for_period = max_plan_monthly * (days_active / 30)
    usage_multiple = total_cost / max(max_plan_for_period, 1)

    # Friendly display names for canonical project keys
    display_names = {
        "Latent": "LOLM / Latent",
        "Codey / Nous": "Codey / Nous",
        "Vol-bot": "Vol-bot",
        "BRYAN (Personal)": "Personal",
        "New Project": "New Project",
        "CapitalCore": "CapitalCore",
        "EGC Study": "EGC",
        "EGC": "EGC",
        "Other (nous)": "Other (nous)",
        "Roro": "Roro",
        "Armo": "Armo",
        "NFET": "NFET",
        "Licensing Dashboard": "Licensing Dashboard",
    }

    def canonical(proj_name):
        """Strip (worktree) / (subagent) suffixes to group all sub-sessions under one project."""
        base = proj_name.replace(" (worktree)", "").replace(" (subagent)", "").strip()
        return display_names.get(base, base)

    # Project breakdown — group main + worktree + subagent together
    projects = {}
    for s in session_list:
        proj = canonical(infer_project(s))
        if proj not in projects:
            projects[proj] = {"tokens": 0, "cost": 0, "sessions": 0}
        projects[proj]["tokens"] += s.get("totalTokens", 0)
        projects[proj]["cost"] += s.get("totalCost", 0)
        projects[proj]["sessions"] += 1

    # Add canonical project name to each session
    for s in session_list:
        s["project"] = canonical(infer_project(s))

    usage = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "daily": daily_list,
        "sessions": session_list,
        "monthly": monthly_list,
        "projects": projects,
        "totals": {
            "tokens": total_tokens,
            "cost": round(total_cost, 2),
            "sessions": num_sessions,
            "days_active": days_active,
            "avg_daily_cost": round(avg_daily, 2),
            "monthly_projection": round(monthly_projection, 2),
            "annual_projection": round(annual_projection, 2),
            "peak_day": peak.get("date", ""),
            "peak_day_cost": round(peak.get("totalCost", 0), 2),
            "peak_day_tokens": peak.get("totalTokens", 0),
            "tokens_per_dollar": round(total_tokens / max(total_cost, 1)),
            "max_plan_for_period": round(max_plan_for_period, 2),
            "usage_multiple": round(usage_multiple, 1),
            "model_totals": model_totals,
            "token_types": {
                "input": input_total,
                "output": output_total,
                "cache_create": cache_create_total,
                "cache_read": cache_read_total,
            },
        },
    }

    out = DATA_DIR / "usage.json"
    out.write_text(json.dumps(usage, indent=2))
    print(f"Exported: {total_tokens:,} tokens, ${total_cost:,.2f}")
    print(f"Projects: {len(projects)}")
    print(f"Burn rate: ${avg_daily:,.0f}/day → ${monthly_projection:,.0f}/mo → ${annual_projection:,.0f}/yr")
    print(f"Max plan multiple: {usage_multiple:.1f}x")


if __name__ == "__main__":
    main()
