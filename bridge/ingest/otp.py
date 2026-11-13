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


# --- Email ------------------------------------------------------------------
# Bank emails end with long safety footers ("never share your OTP, PIN, CVV ...") and
# statement emails explain, with worked examples, how to open a password-protected PDF.
# Neither holds a secret. In bank email bodies "password" and "PIN" appear only in such
# text; real codes are always called OTP / one-time password / verification code.
# So for email: an OTP-like subject drops the message; in the body, warning and
# instruction sentences are removed first, then only OTP-style wording next to a code,
# or a phrase that hands over a code, drops it.

_EMAIL_SUBJECT_SECRET = re.compile(
    r"\b(otp|one[\s-]?time[\s-]?password|verification code|passcode|security code|login code|mpin"
    r"|pin (generation|reset|change))\b"
)
_EMAIL_KEYWORD = re.compile(
    r"\b(?:otp|one[\s-]?time[\s-]?(?:password|passcode|pin|code)|verification\s+code|security\s+code"
    r"|auth(?:entication|ori[sz]ation)?\s+code|cvv2?|cvc)\b"
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_WARNING_SENTENCE = re.compile(
    r"\b(never|do\s*not|don'?t|not to|avoid)\b.{0,80}\b(share|disclose|reveal|tell)\b"
    r"|\b(share|disclose)\b.{0,60}\bwith anyone\b"
    r"|\bpassword[- ]protected\b|\bpassword (is|will be|for opening|to open)\b"
    r"|\b(enter|use)\b.{0,40}\bas (the|your) password\b"
    r"|\bfirst (four|4|\w+) (letters|characters)\b|\b(ddmm|ddmmyy|ddmmyyyy)\b"
)
# Explanations and worked examples: never a real code, even with digits in them.
_INSTRUCTION_SENTENCE = re.compile(
    r"\b(for example|e\.\s?g\.|for instance|illustration)\b"
    r"|\bpassword (configuration|format|protection)\b|\bdefault password\b|\bsecured by a (unique )?password\b"
    r"|\bwill never (contact|ask|call)\b.{0,120}\b(password|pin|otp)\b"
)


def _has_code(sentence):
    return any(
        not _NOT_A_CODE_BEFORE.search(sentence[max(0, m.start() - 16): m.start()])
        for m in _CODE_TOKEN.finditer(sentence)
    )


def contains_secret_email(subject, body):
    """True if an email carries an OTP or similar code. Runs in memory, before anything is stored."""
    subj = _normalise(subject or "")
    if _EMAIL_SUBJECT_SECRET.search(subj):
        return True
    kept = []
    for sentence in _SENTENCE_SPLIT.split(_normalise(body or "")[:6000]):
        if _INSTRUCTION_SENTENCE.search(sentence):
            continue
        if _WARNING_SENTENCE.search(sentence) and not _has_code(sentence):
            continue
        kept.append(sentence)
    text = " ".join(kept)
    if any(p.search(text) for p in _CODE_GIVEN):
        return True
    return any(_code_near(text, m.start(), m.end()) for m in _EMAIL_KEYWORD.finditer(text))
