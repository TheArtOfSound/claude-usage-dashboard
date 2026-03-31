"""Merge ccusage JSON exports into a single usage.json with project inference."""
import json
import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

def infer_project(session):
    """Infer project name from session path or ID."""
    path = session.get("projectPath", "")
    sid = session.get("sessionId", "")

    if not path and not sid:
        return "Unknown"

    # Extract from path
    if path:
        name = path.rstrip("/").split("/")[-1]
        # Map known directories to project names
        project_map = {
            "nous": "Codey / Nous",
            "codey": "Codey",
            "egcstudy": "EGC Study",
            "nfet": "NFET",
            "armo": "Armo",
            "roro": "Roro",
            "ani": "Ani",
            "capstone": "Capstone",
        }
        for key, proj in project_map.items():
            if key in name.lower() or key in path.lower():
                return proj
        return name if name else "Unknown"

    # Check if it's a subagent
    if "subagent" in sid.lower():
        return "Subagent"

    return sid[:12] + "..."


def main():
    daily = json.loads((DATA_DIR / "daily.json").read_text())
    sessions = json.loads((DATA_DIR / "sessions.json").read_text())
    monthly = json.loads((DATA_DIR / "monthly.json").read_text())

    daily_list = daily.get("daily", [])
    session_list = sessions.get("sessions", [])
    monthly_list = monthly.get("monthly", [])

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

    # Project breakdown
    projects = {}
    for s in session_list:
        proj = infer_project(s)
        if proj not in projects:
            projects[proj] = {"tokens": 0, "cost": 0, "sessions": 0}
        projects[proj]["tokens"] += s.get("totalTokens", 0)
        projects[proj]["cost"] += s.get("totalCost", 0)
        projects[proj]["sessions"] += 1

    # Add project name to each session
    for s in session_list:
        s["project"] = infer_project(s)

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
