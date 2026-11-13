"""Facts -> short plain text for the model, and the set of amounts the answer may use."""
from core.money import format_inr


def inr(paise):
    return format_inr(paise).replace(".00", "")


def _spend(label, s, include_payees):
    lines = [f"{label} ({s['start']} to {s['end']}): spent {inr(s['total_paise'])}"]
    lines += [f"  - {name}: {inr(v)}" for name, v in s["by_category"].items()]
    if include_payees and s["top_payees"]:
        lines.append("  top payees: " + "; ".join(f"{n} {inr(v)}" for n, v in s["top_payees"]))
    return lines


def render(facts, include_payees=True):
    out = [f"Today is {facts['today']}. All amounts are in Indian rupees."]
    if facts.get("records_start"):
        out.append(f"Records start on {facts['records_start']}; nothing earlier is known (not zero, unknown).")
    for key, label in (("this_month", "This month so far"), ("last_month_same_days", "Last month, same days"),
                       ("last_month_full", "Last month, whole month")):
        if key in facts:
            out += _spend(label, facts[key], include_payees)
    if "income_this_month" in facts:
        out.append(f"Money received this month (income): {inr(facts['income_this_month']['total_paise'])}")
    if "upcoming_30_days" in facts:
        out.append("Payments due in the next 30 days:" if facts["upcoming_30_days"] else "Nothing due in the next 30 days.")
        for i in facts["upcoming_30_days"]:
            what = {"emi": i.get("name", "EMI") if i.get("name", "").startswith("EMI") else f"EMI {i.get('name', '')}", "card_due": "Credit card bill",
                    "card_due_unpaid": "UNPAID credit card bill (due date passed)"}[i["type"]]
            extra = f", minimum {inr(i['minimum_paise'])}" if i.get("minimum_paise") else ""
            out.append(f"  - {i['date']}: {what} {inr(i['amount_paise'])}{extra}")
    for g in facts.get("goals", []):
        pace = f", needs {inr(g['needed_per_month_paise'])} per month" if g.get("needed_per_month_paise") else ""
        out.append(f"Goal '{g['name']}': saved {inr(g['saved_paise'])} of {inr(g['target_paise'])} ({g['percent']}%), "
                   f"{inr(g['left_paise'])} left, target date {g['target_date'] or 'none'}{pace}")
    if "net_worth" in facts:
        n = facts["net_worth"]
        out.append(f"Net worth now: {inr(n['net_worth_paise'])} (assets {inr(n['assets_paise'])}, "
                   f"money owed {inr(n['liabilities_paise'])})")
    for a in facts.get("accounts", []):
        out.append(f"  - {a['name']} ({a['kind']}): {inr(a['balance_paise'])} [{a['balance_status']}]")
    inv = facts.get("investments")
    if inv:
        parts = ", ".join(f"{k.replace('_', ' ')} {inr(v)}" for k, v in inv["by_kind"].items())
        out.append(f"Investments as per the CDSL statement of {inv['statement_date']}: {inr(inv['total_paise'])} ({parts})")
        out += [f"  - {h['name']} ({h['kind'].replace('_', ' ')}): {inr(h['value_paise'])}" for h in inv.get("holdings", [])]
    if facts.get("open_review_items"):
        out.append(f"{facts['open_review_items']} items are waiting in the review queue.")
    return "\n".join(out)


def amounts(obj):
    """Every money figure (paise) inside a facts structure."""
    found = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key.endswith("_paise") and isinstance(value, int):
                found.add(abs(value))
            elif key == "by_category" and isinstance(value, dict):
                found |= {abs(v) for v in value.values()}
            else:
                found |= amounts(value)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            if isinstance(item, (list, tuple)) and len(item) == 2 and isinstance(item[1], int):
                found.add(abs(item[1]))  # (payee, paise)
            else:
                found |= amounts(item)
    return found


# Topics where a missing item would mislead: the answer always ends with the complete list from code.
TOPICS = {
    "upcoming_30_days": ("due", "pay", "bill", "emi", "instal", "owe"),
    "goals": ("goal", "saving for", "bike", "target", "on track"),
    "net_worth": ("net worth", "worth", "invest", "assets", "fund", "share", "stock", "holding", "portfolio", "sip"),
}


def footnote(question, facts):
    words = question.lower()
    picked = [key for key, keys in TOPICS.items() if any(k in words for k in keys) and key in facts]
    if not picked:
        return ""
    sub = {"today": facts["today"]}
    for key in picked:
        sub[key] = facts[key]
        if key == "net_worth":
            sub["investments"] = facts.get("investments")
    lines = render(sub).splitlines()[1:]  # drop the "Today is" line
    return "\n\nFrom your records:\n" + "\n".join(lines) if lines else ""
