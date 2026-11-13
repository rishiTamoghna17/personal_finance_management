"""Statement layout parsers, one module per bank layout, written from the owner's real statements.
Each module exposes MATCH(pages) -> bool and parse(pages) -> Statement."""
from . import axis_card, hsbc, icici, sbi_card

PARSERS = {"hsbc": [hsbc], "icici": [icici], "sbi-card": [sbi_card], "axis-card": [axis_card]}


def find(key, pages):
    for module in PARSERS.get(key, []):
        if pages and module.MATCH(pages):
            return module.parse
    return None
