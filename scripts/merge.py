"""Merge ccusage JSON exports into a single usage.json with project inference.

Supports multi-machine merging: pass --machine2 <dir> to include a second
machine's exports. Sessions are deduplicated by sessionId so nothing gets
double-counted.

Usage:
    python3 scripts/merge.py                       # single machine (default)
    python3 scripts/merge.py --machine2 data/m2    # merge two machines
"""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
CLAUDE_DIR = Path.home() / ".claude"

# ── Machine labels ──
MACHINE1_LABEL = "Bryan"
MACHINE2_LABEL = "Brandyn"

# ── Keyword lists for content-based project detection ──
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

AUTOHUSTLE_KEYWORDS = ['autohustle', 'shopify', 'solana_sniper', 'dropshipping',
    'orchestrator', 'budget_guard', 'kill_switch', 'circuit_breaker', 'blog_publisher',
    'repo_organizer', 'seo_content', 'stripe_premium']


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
        "auto": "AutoHustle",
        "autohustle": "AutoHustle",
        "claude-usage-dashboard": "Usage Dashboard",
        "portfolio": "Portfolio",
    }

    # Check subagent first — use parent path for project name
    if "subagent" in sid.lower():
        search_str = path.lower().replace("-", " ").replace("/", " ")
        for key, proj in project_map.items():
            if key.replace("-", " ") in search_str:
                return f"{proj} (subagent)"
        return "Subagent"

    # Combine path and sessionId for searching
    search_strs = []
    if path and path != "Unknown Project":
        search_strs.append(path.lower())
    if sid:
        search_strs.append(sid.lower().replace("-", " ").replace("/", " "))

    for search_str in search_strs:
        for key, proj in project_map.items():
            if key.replace("-", " ") in search_str or key in search_str:
                if "worktree" in search_str:
                    return f"{proj} (worktree)"
                return proj

    # Fallback: try to extract a meaningful name from sessionId
    if sid:
        parts = sid.split("-")
        clean = [p for p in parts if p and p.lower() not in (
            "users", "bry", "brandyn", "finky", "documents", "claude", "worktrees", "wor",
            "c", "program files"
        )]
        if clean:
            name = clean[0]
            if len(name) > 3 and not all(c in "0123456789abcdef" for c in name):
                return name.title()

    return "Unknown"


# ── Multi-machine merging helpers ──

def load_json_safe(path):
    """Load a JSON file, return empty structure on failure."""
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception as e:
        print(f"  Warning: could not read {p}: {e}")
        return {}


def merge_daily(daily1, daily2):
    """Merge two daily lists. Same date -> sum the numbers. Different dates -> union."""
    by_date = {}
    for d in daily1:
        by_date[d["date"]] = dict(d)

    for d in daily2:
        date = d["date"]
        if date in by_date:
            existing = by_date[date]
            for key in ("inputTokens", "outputTokens", "cacheCreationTokens",
                        "cacheReadTokens", "totalTokens"):
                existing[key] = existing.get(key, 0) + d.get(key, 0)
            existing["totalCost"] = existing.get("totalCost", 0) + d.get("totalCost", 0)
            # Merge modelsUsed
            models = set(existing.get("modelsUsed", []))
            models.update(d.get("modelsUsed", []))
            existing["modelsUsed"] = sorted(models)
            # Merge modelBreakdowns
            mb_map = {}
            for mb in existing.get("modelBreakdowns", []):
                mb_map[mb["modelName"]] = dict(mb)
            for mb in d.get("modelBreakdowns", []):
                name = mb["modelName"]
                if name in mb_map:
                    for k in ("inputTokens", "outputTokens", "cacheCreationTokens",
                              "cacheReadTokens", "cost"):
                        mb_map[name][k] = mb_map[name].get(k, 0) + mb.get(k, 0)
                else:
                    mb_map[name] = dict(mb)
            existing["modelBreakdowns"] = list(mb_map.values())
        else:
            by_date[date] = dict(d)

    return sorted(by_date.values(), key=lambda x: x["date"])


def merge_sessions(sessions1, sessions2):
    """Merge two session lists from different machines.

    Keeps ALL sessions from both machines. Only deduplicates sessions that
    appear to be truly identical (same sessionId AND similar cost — indicating
    the same session log exists on both machines, e.g. via cloud sync).

    ccusage reports subagent sessions as separate entries all sharing the
    generic sessionId "subagents". These are distinct work and must NOT be
    collapsed.
    """
    result = list(sessions1)  # keep all machine 1 sessions
    dupes = 0

    # Build a fingerprint set from machine 1 for true-duplicate detection.
    # A session is a true duplicate only if sessionId + cost match closely.
    m1_fingerprints = set()
    for s in sessions1:
        sid = s.get("sessionId", "")
        cost = round(s.get("totalCost", 0), 2)
        tokens = s.get("totalTokens", 0)
        m1_fingerprints.add((sid, cost, tokens))

    for s in sessions2:
        sid = s.get("sessionId", "")
        cost = round(s.get("totalCost", 0), 2)
        tokens = s.get("totalTokens", 0)
        fp = (sid, cost, tokens)
        if fp in m1_fingerprints:
            dupes += 1
            # Remove from fingerprints so if M2 has multiple entries with
            # same fingerprint, only one gets deduped per M1 match
            m1_fingerprints.discard(fp)
        else:
            result.append(s)

    if dupes:
        print(f"  Deduped {dupes} truly identical sessions (same ID + cost + tokens)")
    return result


def merge_monthly(monthly1, monthly2):
    """Merge two monthly lists. Same month -> sum. Different months -> union."""
    by_month = {}
    for m in monthly1:
        by_month[m["month"]] = dict(m)

    for m in monthly2:
        month = m["month"]
        if month in by_month:
            existing = by_month[month]
            for key in ("inputTokens", "outputTokens", "cacheCreationTokens",
                        "cacheReadTokens", "totalTokens"):
                existing[key] = existing.get(key, 0) + m.get(key, 0)
            existing["totalCost"] = existing.get("totalCost", 0) + m.get("totalCost", 0)
            models = set(existing.get("modelsUsed", []))
            models.update(m.get("modelsUsed", []))
            existing["modelsUsed"] = sorted(models)
        else:
            by_month[month] = dict(m)

    return sorted(by_month.values(), key=lambda x: x["month"])


def main():
    parser = argparse.ArgumentParser(description="Merge ccusage exports into usage.json")
    parser.add_argument("--machine2", type=str, default=None,
                        help="Path to directory containing machine 2 exports "
                             "(daily_machine2.json, sessions_machine2.json, monthly_machine2.json)")
    args = parser.parse_args()

    # ── Load machine 1 data (always from data/) ──
    daily1 = json.loads((DATA_DIR / "daily.json").read_text())
    sessions1 = json.loads((DATA_DIR / "sessions.json").read_text())
    monthly1 = json.loads((DATA_DIR / "monthly.json").read_text())

    daily_list = daily1.get("daily", [])
    raw_sessions = sessions1.get("sessions", [])
    monthly_list = monthly1.get("monthly", [])

    # Tag machine 1 sessions
    for s in raw_sessions:
        s["_machine"] = MACHINE1_LABEL

    # Tag machine 1 daily
    for d in daily_list:
        d.setdefault("_machines", [MACHINE1_LABEL])

    # Track data sources with sync timestamps
    sources = {
        MACHINE1_LABEL: {
            "synced_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "sessions": len(raw_sessions),
            "daily_records": len(daily_list),
        }
    }

    # ── Load + merge machine 2 data (if provided) ──
    if args.machine2:
        m2_dir = Path(args.machine2)
        print(f"Loading machine 2 data from: {m2_dir}")

        # Look for files with various naming conventions
        daily2_path = None
        sessions2_path = None
        monthly2_path = None

        for name in ("daily_machine2.json", "daily.json"):
            p = m2_dir / name
            if p.exists():
                daily2_path = p
                break
        for name in ("sessions_machine2.json", "sessions.json"):
            p = m2_dir / name
            if p.exists():
                sessions2_path = p
                break
        for name in ("monthly_machine2.json", "monthly.json"):
            p = m2_dir / name
            if p.exists():
                monthly2_path = p
                break

        if daily2_path:
            d2 = load_json_safe(daily2_path)
            d2_list = d2.get("daily", [])
            # Tag machine 2 daily
            for d in d2_list:
                d.setdefault("_machines", [MACHINE2_LABEL])
            # Before merging, tag existing daily records that will get combined
            daily_list = merge_daily(daily_list, d2_list)
            # Update _machines for merged dates
            for d in daily_list:
                machines = d.get("_machines", [])
                if MACHINE1_LABEL not in machines and MACHINE2_LABEL not in machines:
                    d["_machines"] = [MACHINE1_LABEL]
            print(f"  Daily: merged {len(d2_list)} records from machine 2")
        else:
            print(f"  Warning: no daily JSON found in {m2_dir}")

        if sessions2_path:
            s2 = load_json_safe(sessions2_path)
            s2_list = s2.get("sessions", [])
            for s in s2_list:
                s["_machine"] = MACHINE2_LABEL
            before = len(raw_sessions)
            raw_sessions = merge_sessions(raw_sessions, s2_list)
            print(f"  Sessions: {before} + {len(s2_list)} = {len(raw_sessions)} (after dedup)")
        else:
            print(f"  Warning: no sessions JSON found in {m2_dir}")

        if monthly2_path:
            m2 = load_json_safe(monthly2_path)
            m2_list = m2.get("monthly", [])
            monthly_list = merge_monthly(monthly_list, m2_list)
            print(f"  Monthly: merged {len(m2_list)} records from machine 2")
        else:
            print(f"  Warning: no monthly JSON found in {m2_dir}")

        sources[MACHINE2_LABEL] = {
            "synced_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "sessions": len(s2_list) if sessions2_path else 0,
            "daily_records": len(d2_list) if daily2_path else 0,
        }

    # ── Content-based splitting for multi-project directories ──
    session_list = []
    for s in raw_sessions:
        sid = s.get("sessionId", "")
        if sid == "-Users-bry-nous":
            props = scan_session_content("-Users-bry-nous")
            if props:
                splits = split_session(s, props)
                # Preserve machine tag on splits
                for sp in splits:
                    sp["_machine"] = s.get("_machine", MACHINE1_LABEL)
                session_list.extend(splits)
                print(f"Split nous session (${s['totalCost']:.2f}) into {len(splits)} projects:")
                for sp in splits:
                    print(f"  {sp['_split_project']}: ${sp['totalCost']:.2f} ({sp['_split_pct']}%)")
                continue
        session_list.append(s)

    # ── Calculate totals ──
    total_tokens = sum(d["totalTokens"] for d in daily_list)
    total_cost = sum(d["totalCost"] for d in daily_list)
    days_active = len(daily_list)
    num_sessions = len(session_list)

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

    # Friendly display names
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
        "AutoHustle": "AutoHustle",
        "Usage Dashboard": "Usage Dashboard",
        "Portfolio": "Portfolio",
    }

    def canonical(proj_name):
        base = proj_name.replace(" (worktree)", "").replace(" (subagent)", "").strip()
        return display_names.get(base, base)

    # ── Project breakdown (combined) ──
    projects = {}
    for s in session_list:
        proj = canonical(infer_project(s))
        if proj not in projects:
            projects[proj] = {"tokens": 0, "cost": 0, "sessions": 0}
        projects[proj]["tokens"] += s.get("totalTokens", 0)
        projects[proj]["cost"] += s.get("totalCost", 0)
        projects[proj]["sessions"] += 1

    # ── Per-machine project breakdown ──
    projects_by_machine = {}
    for s in session_list:
        machine = s.get("_machine", MACHINE1_LABEL)
        proj = canonical(infer_project(s))
        if machine not in projects_by_machine:
            projects_by_machine[machine] = {}
        if proj not in projects_by_machine[machine]:
            projects_by_machine[machine][proj] = {"tokens": 0, "cost": 0, "sessions": 0}
        projects_by_machine[machine][proj]["tokens"] += s.get("totalTokens", 0)
        projects_by_machine[machine][proj]["cost"] += s.get("totalCost", 0)
        projects_by_machine[machine][proj]["sessions"] += 1

    # Add canonical project name + machine to each session
    for s in session_list:
        s["project"] = canonical(infer_project(s))

    usage = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sources": sources,
        "daily": daily_list,
        "sessions": session_list,
        "monthly": monthly_list,
        "projects": projects,
        "projects_by_machine": projects_by_machine,
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
    print(f"\nExported: {total_tokens:,} tokens, ${total_cost:,.2f}")
    print(f"Projects: {len(projects)}")
    print(f"Sources: {', '.join(sources.keys())}")
    print(f"Burn rate: ${avg_daily:,.0f}/day -> ${monthly_projection:,.0f}/mo -> ${annual_projection:,.0f}/yr")
    print(f"Max plan multiple: {usage_multiple:.1f}x")

    if len(sources) > 1:
        print(f"\nPer-machine breakdown:")
        for machine, projs in projects_by_machine.items():
            m_cost = sum(p["cost"] for p in projs.values())
            m_sessions = sum(p["sessions"] for p in projs.values())
            print(f"  {machine}: ${m_cost:,.2f} across {m_sessions} sessions")


if __name__ == "__main__":
    main()
