"""Statement layout parsers, one module per bank layout, written from the owner's real statements.
Each module exposes MATCH(pages) -> bool and parse(pages) -> Statement (or, for M5 documents, EmiLetter / CasDocument)."""
from . import axis_card, axis_emi, cdsl_cas, hsbc, icici, sbi_card

PARSERS = {"hsbc": [hsbc], "icici": [icici], "sbi-card": [sbi_card], "axis-card": [axis_card, axis_emi], "cdsl": [cdsl_cas]}


def find(key, pages):
    for module in PARSERS.get(key, []):
        if pages and module.MATCH(pages):
            return module.parse
    return None
