"""Drop messages that carry a secret: OTP, PIN, CVV, password or a verification code.

Runs in memory before anything is stored, logged or queued (CLAUDE.md rule 3).
When in doubt it drops: storing a secret is worse than losing a message, and
every drop is counted per sender per day so it is never silent.

A transaction alert that only *warns* ("Never share your OTP/PIN") is kept,
unless a code-like number sits right next to the keyword.
"""
import re

_KEYWORD = re.compile(
    r"\b(?:otp|one[\s-]?time[\s-]?(?:password|passcode|pin|code)|verification\s+code|security\s+code"
    r"|auth(?:entication|ori[sz]ation)?\s+code|passcode|password|passwd|cvv2?|cvc|m-?pin|t-?pin|i-?pin|pin)\b"
)
# Phrases that hand over a code even without one of the keywords above.
_CODE_GIVEN = [
    re.compile(r"\bcode\s*(?:is|:|-)\s*\d{4,8}\b"),
    re.compile(r"\b\d{4,8}\s+is\s+(?:your|the)\b"),
    re.compile(r"\buse\s+\d{4,8}\s+(?:to|for|as)\b"),
]
_WARNING = re.compile(r"\b(?:never|do\s*not|don'?t|dont|not\s+to)\s+(?:share|disclose|reveal|tell)\b[^.!\n]{0,40}")
_CODE_TOKEN = re.compile(r"(?<![\w.,/:-])\d{4,8}(?![\w,/:-]|\.\d)")
_NOT_A_CODE_BEFORE = re.compile(r"(?:rs\.?|inr|₹|x|\*|ending(?:\s+with)?|a/c(?:\s*no\.?)?|acct|ac|card(?:\s*no\.?)?)\s*$")
_NEAR = 15  # characters either side of a keyword


def _normalise(text):
    return " ".join(text.casefold().split())


def _code_near(text, start, end):
    lo, hi = max(0, start - _NEAR), min(len(text), end + _NEAR)
    for token in _CODE_TOKEN.finditer(text, lo, hi):
        if not _NOT_A_CODE_BEFORE.search(text[max(0, token.start() - 16) : token.start()]):
            return True
    return False


def contains_secret(text):
    t = _normalise(text)
    if any(p.search(t) for p in _CODE_GIVEN):
        return True
    if _KEYWORD.search(_WARNING.sub(" ", t)):
        return True
    return any(_code_near(t, m.start(), m.end()) for m in _KEYWORD.finditer(t))
