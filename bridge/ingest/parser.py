"""Per-bank SMS profiles (YAML) and the parser that applies them.

A profile is written only from the owner's real, masked samples (CLAUDE.md rule 9).
See ingest/profiles/README.md for the format.
"""
import datetime as dt
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from django.conf import settings

from core.money import MoneyError, to_paise

IST = ZoneInfo("Asia/Kolkata")
_DLT = re.compile(r"^[A-Z]{2}-([A-Z0-9]{6})(?:-[A-Z])?$")
DIRECTIONS = {"debit", "credit"}
KINDS = {"payment", "refund", "reversal", "own_transfer", "card_payment"}
TYPES = {"transaction", "ignore", "balance", "review"}


class ProfileError(ValueError):
    pass


@dataclass(frozen=True)
class Pattern:
    ref: str
    regex: re.Pattern
    type: str
    direction: str = ""
    channel: str = ""
    kind: str = "payment"
    reason: str = ""
    account_from_default: bool = False
    category: str = ""


@dataclass(frozen=True)
class Profile:
    id: str
    account_kind: str
    senders: frozenset
    date_formats: tuple
    patterns: tuple


@dataclass
class Parsed:
    pattern_ref: str
    type: str  # transaction | balance
    account_last4: str
    occurred_at: dt.datetime
    amount_paise: int = 0
    direction: str = ""
    channel: str = ""
    kind: str = "payment"
    counterparty: str = ""
    vpa: str = ""
    reference: str = ""
    target_last4: str = ""
    balance_paise: int | None = None
    category: str = ""


@dataclass
class ParseResult:
    status: str  # parsed | ignored | unparsed | unknown_sender
    parsed: Parsed | None = None
    reason: str = ""
    pattern_ref: str = ""


def header_of(sender):
    """'VM-HDFCBK-S' -> 'HDFCBK'. Anything else is upper-cased as is."""
    sender = (sender or "").strip().upper()
    match = _DLT.match(sender)
    return match.group(1) if match else sender


def header_of_email(from_header):
    """'HDFC Bank <alerts@hdfcbank.bank.in>' -> 'HDFCBANK.BANK.IN' (the sender's domain)."""
    match = re.search(r"@([\w.-]+)", from_header or "")
    return match.group(1).strip(".").upper() if match else (from_header or "").strip().upper()


def _load_profile(path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    where = path.name
    if not isinstance(data, dict):
        raise ProfileError(f"{where}: not a mapping")
    pid = data.get("id")
    account_kind = data.get("account_kind")
    senders = data.get("senders")
    if not isinstance(pid, str) or not pid:
        raise ProfileError(f"{where}: id is required")
    if account_kind not in ("bank", "card", "document"):
        raise ProfileError(f"{where}: account_kind must be bank, card or document")
    if not isinstance(senders, list) or not senders:
        raise ProfileError(f"{where}: senders must be a non-empty list of DLT headers")
    patterns = []
    for i, raw in enumerate(data.get("patterns") or [], start=1):
        pref = f"{pid}/{raw.get('id', i)}"
        ptype = raw.get("type", "transaction")
        if ptype not in TYPES:
            raise ProfileError(f"{pref}: type must be one of {sorted(TYPES)}")
        try:
            regex = re.compile(raw["match"], re.IGNORECASE)
        except (KeyError, TypeError, re.error) as exc:
            raise ProfileError(f"{pref}: bad or missing match regex ({exc})") from None
        groups = set(regex.groupindex)
        if account_kind == "card" and "balance" in groups:
            # A card's "available limit" is not a balance and never an asset (rule 8).
            raise ProfileError(f"{pref}: card profiles may not capture a balance")
        if account_kind == "document" and ptype not in ("ignore", "review"):
            # Senders of documents only (CAS, credit report): their emails never become transactions.
            raise ProfileError(f"{pref}: document profiles may only ignore or review")
        account_from_default = raw.get("account") == "default"
        if ptype == "transaction":
            # Some banks never name the account (e.g. one Federal Bank account); the owner then
            # sets its last digits in BRIDGE_DEFAULT_ACCOUNTS instead.
            missing = ({"amount"} if account_from_default else {"amount", "account"}) - groups
            if missing:
                raise ProfileError(f"{pref}: transaction patterns need groups {sorted(missing)}")
            if raw.get("direction") not in DIRECTIONS:
                raise ProfileError(f"{pref}: direction must be debit or credit")
            if raw.get("kind", "payment") not in KINDS:
                raise ProfileError(f"{pref}: kind must be one of {sorted(KINDS)}")
        if ptype == "balance" and not {"account", "balance"} <= groups:
            raise ProfileError(f"{pref}: balance patterns need groups account and balance")
        if ptype in ("ignore", "review") and not raw.get("reason"):
            raise ProfileError(f"{pref}: {ptype} patterns need a reason")
        patterns.append(
            Pattern(
                ref=pref,
                regex=regex,
                type=ptype,
                direction=raw.get("direction", ""),
                channel=raw.get("channel", ""),
                kind=raw.get("kind", "payment"),
                reason=raw.get("reason", ""),
                account_from_default=account_from_default,
                category=raw.get("category", ""),
            )
        )
    if not patterns:
        raise ProfileError(f"{where}: no patterns")
    return Profile(
        id=pid,
        account_kind=account_kind,
        senders=frozenset(s.upper() for s in senders),
        date_formats=tuple(data.get("date_formats") or ()),
        patterns=tuple(patterns),
    )


@lru_cache(maxsize=None)
def _profiles_for(dirs):
    by_header = {}
    for directory in dirs:
        for path in sorted(Path(directory).glob("*.yaml")):
            profile = _load_profile(path)
            for header in profile.senders:
                if header in by_header:
                    raise ProfileError(f"sender {header} is claimed by two profiles")
                by_header[header] = profile
    return by_header


def profiles(source="sms"):
    dirs = settings.INGEST_EMAIL_PROFILE_DIRS if source == "email" else settings.INGEST_PROFILE_DIRS
    return _profiles_for(tuple(str(d) for d in dirs))


def clear_cache():
    _profiles_for.cache_clear()


def _paise(text):
    cleaned = text.strip().removesuffix("/-").strip()
    return to_paise(cleaned)


def _last4(text):
    """Last four digits; some banks (e.g. ICICI "XX378") show only three, which are kept as three."""
    digits = "".join(ch for ch in text or "" if ch.isdigit())
    return digits[-4:] if len(digits) >= 3 else ""


def _occurred_at(groups, profile, sent_at):
    date_text = (groups.get("date") or "").strip()
    if not date_text:
        return sent_at
    day, has_year = None, True
    for fmt in profile.date_formats:
        has_year = "%y" in fmt or "%Y" in fmt
        try:
            if has_year:
                day = dt.datetime.strptime(date_text, fmt).date()
            else:  # parse in a leap year so "29FEB" is valid; the real year is set below
                day = dt.datetime.strptime(f"{date_text} 2000", f"{fmt} %Y").date()
            break
        except ValueError:
            continue
    if day is None:
        return sent_at
    if not has_year:  # the SMS gave no year ("15AUG"): the latest such date not after the SMS
        sent_day = sent_at.astimezone(IST).date()
        candidates = []
        for year in range(sent_day.year, sent_day.year - 5, -1):  # 29 Feb may need a leap year
            try:
                candidates.append(day.replace(year=year))
            except ValueError:
                continue
        day = next((c for c in candidates if c <= sent_day + dt.timedelta(days=1)), candidates[-1])
    time_text = (groups.get("time") or "").strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return dt.datetime.combine(day, dt.datetime.strptime(time_text, fmt).time(), tzinfo=IST)
        except ValueError:
            continue
    if sent_at.astimezone(IST).date() == day:
        return sent_at
    # Late SMS: trust the date in the message; the time of day is unknown.
    return dt.datetime.combine(day, dt.time(12, 0), tzinfo=IST)


def parse(header, body, sent_at, source="sms"):
    profile = profiles(source).get(header)
    if profile is None:
        return ParseResult("unknown_sender", reason=f"no profile for sender {header}")
    text = " ".join(body.split())
    for pattern in profile.patterns:
        match = pattern.regex.search(text)
        if not match:
            continue
        if pattern.type == "ignore":
            return ParseResult("ignored", reason=pattern.reason, pattern_ref=pattern.ref)
        if pattern.type == "review":
            # Known message that a person must handle, e.g. a spend in a foreign currency.
            return ParseResult("review", reason=pattern.reason, pattern_ref=pattern.ref)
        g = {k: v for k, v in match.groupdict().items() if v is not None}
        try:
            parsed = Parsed(
                pattern_ref=pattern.ref,
                type=pattern.type,
                account_last4=_last4(g.get("account")),
                occurred_at=_occurred_at(g, profile, sent_at),
                amount_paise=_paise(g["amount"]) if "amount" in g else 0,
                direction=pattern.direction,
                channel=pattern.channel,
                kind=pattern.kind,
                counterparty=(g.get("counterparty") or "").strip()[:200],
                vpa=(g.get("vpa") or "").strip()[:200],
                reference=(g.get("ref") or "").strip()[:64],
                target_last4=_last4(g.get("target")),
                balance_paise=_paise(g["balance"]) if "balance" in g else None,
                category=pattern.category or ("Refunds" if pattern.kind == "refund" else ""),
            )
        except MoneyError as exc:
            return ParseResult("unparsed", reason=f"{pattern.ref}: bad amount ({exc})", pattern_ref=pattern.ref)
        if not parsed.account_last4 and pattern.account_from_default:
            parsed.account_last4 = settings.INGEST_DEFAULT_ACCOUNTS.get(profile.id, "")
            if not parsed.account_last4:
                return ParseResult("parsed", parsed=parsed, pattern_ref=pattern.ref)  # -> review: unknown account
        if not parsed.account_last4:
            return ParseResult("unparsed", reason=f"{pattern.ref}: no account digits", pattern_ref=pattern.ref)
        if parsed.type == "transaction" and parsed.amount_paise <= 0:
            return ParseResult("unparsed", reason=f"{pattern.ref}: amount is zero", pattern_ref=pattern.ref)
        return ParseResult("parsed", parsed=parsed, pattern_ref=pattern.ref)
    return ParseResult("unparsed", reason=f"no {profile.id} pattern matched")
