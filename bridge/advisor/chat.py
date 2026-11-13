"""The advisor chat. The model writes words; the numbers come from facts computed by code, and an answer with an
amount the facts do not support is retried once, then replaced by the facts themselves."""
import datetime as dt
import logging

from django.conf import settings
from django.utils import timezone

from firefly.client import FireflyClient
from llm import providers

from . import check, facts, render

log = logging.getLogger(__name__)
MAX_HISTORY = 6
MAX_TEXT = 1000
MAX_TOOL_ROUNDS = 2

SYSTEM = (
    "You are a private personal finance assistant for one person in India. Money is in Indian rupees (write ₹, "
    "and use lakh/crore grouping like ₹1,25,000). Answer in a few short sentences, plainly and kindly.\n"
    "Rules:\n"
    "1. Use only the FACTS below and tool results. Never guess or make up a number. If something is not in the facts, "
    "say you do not have that information.\n"
    "2. When you compare or add, show the figures you used.\n"
    "3. You cannot make payments, transfers or any changes; you only read summaries.\n"
    "4. You are not a licensed financial adviser. You may explain the facts and suggest general good habits "
    "(spend less in a category, keep an emergency fund, pay card bills in full), but do not tell the person to buy "
    "or sell any specific fund or share.\n"
    "5. 'money owed' and negative card balances are debts; a credit limit is never money they have.\n"
    "6. Investments, goals, dues and balances are all in the FACTS. Use the tools only for spending or income in "
    "a date range the FACTS do not cover."
)

TOOLS = [
    {"type": "function", "function": {
        "name": "spending_between",
        "description": "Spending by category and top payees between two dates (for any month or range not in the facts)",
        "parameters": {"type": "object", "properties": {
            "start": {"type": "string", "description": "YYYY-MM-DD"}, "end": {"type": "string", "description": "YYYY-MM-DD"}},
            "required": ["start", "end"]}}},
    {"type": "function", "function": {
        "name": "income_between",
        "description": "Money received (income) between two dates",
        "parameters": {"type": "object", "properties": {
            "start": {"type": "string", "description": "YYYY-MM-DD"}, "end": {"type": "string", "description": "YYYY-MM-DD"}},
            "required": ["start", "end"]}}},
]


def _run_tool(call, client, today):
    fn = call.get("function") or {}
    args = fn.get("arguments") or {}
    try:
        start, end = dt.date.fromisoformat(str(args["start"])), dt.date.fromisoformat(str(args["end"]))
    except (KeyError, ValueError):
        return "Error: start and end must be dates like 2026-10-01.", {}
    start, end = min(start, end), min(max(start, end), today)
    ledger_start = dt.date.fromisoformat(settings.INGEST_LEDGER_START)
    if end < ledger_start:
        return (f"No records before {ledger_start} (tracking started then), so spending and income for "
                f"{start} to {end} are not known. Do not say they were zero."), {}
    start = max(start, ledger_start)
    if (end - start).days > 400:
        return "Error: ask for at most about one year at a time.", {}
    if fn.get("name") == "spending_between":
        data = facts.spending(start, end, client)
        return render.render({"today": today.isoformat(), "this_month": data}).replace("This month so far", "Spending"), data
    if fn.get("name") == "income_between":
        data = facts.income(start, end, client)
        return f"Income {start} to {end}: {render.inr(data['total_paise'])}", data
    return "Error: unknown tool.", {}


def _history(history):
    turns = []
    for item in (history or [])[-MAX_HISTORY:]:
        if isinstance(item, dict) and item.get("role") in ("user", "assistant") and isinstance(item.get("content"), str):
            turns.append({"role": item["role"], "content": item["content"][:MAX_TEXT]})
    return turns


def fallback_answer(sheet):
    return ("I could not word an answer I can stand behind, so here are the figures I have:\n"
            + render.render(sheet, include_payees=True))


def answer(message, history=None, today=None, client=None, transport=None):
    today = today or timezone.localdate()
    client = client or FireflyClient.from_settings()
    sheet = facts.fact_sheet(today, client)
    known = render.amounts(sheet)
    messages = [{"role": "system", "content": SYSTEM + "\n\nFACTS:\n" + render.render(sheet)},
                *_history(history), {"role": "user", "content": message[:MAX_TEXT]}]
    tools_used = []
    reply = providers.chat(messages, TOOLS, transport=transport)
    for _ in range(MAX_TOOL_ROUNDS):
        if not reply["tool_calls"]:
            break
        messages.append({"role": "assistant", "content": reply["content"], "tool_calls": reply["tool_calls"]})
        for call in reply["tool_calls"]:
            text, data = _run_tool(call, client, today)
            known |= render.amounts(data)
            tools_used.append((call.get("function") or {}).get("name", "?"))
            messages.append({"role": "tool", "content": text})
        reply = providers.chat(messages, TOOLS, transport=transport)
    text = reply["content"].strip()
    bad = check.unsupported(text, known)
    if bad or not text:
        log.info("advisor: answer had %s unsupported amounts; retrying once", len(bad))
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": "Some amounts in your answer are not in the FACTS. Answer again using "
                                                 "only amounts that appear in the FACTS or tool results."}]
        text = providers.chat(messages, transport=transport)["content"].strip()
        bad = check.unsupported(text, known)
        if bad or not text:
            return {"answer": fallback_answer(sheet), "checked": False, "tools_used": tools_used}
    return {"answer": text + render.footnote(message, sheet), "checked": True, "tools_used": tools_used}
