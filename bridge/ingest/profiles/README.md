# Bank and card SMS profiles

One YAML file per bank or card issuer. **Write a pattern only from a real, masked
SMS the owner has sent** (CLAUDE.md rule 9), and add that SMS as a test fixture
in `bridge/tests/ingest/fixtures/<profile id>/`.

```yaml
id: examplebank              # unique
account_kind: bank           # bank | card
senders: [EXMPLB]            # DLT headers: the 6 characters in "VM-EXMPLB-S"
date_formats: ["%d-%m-%y"]   # strptime formats for the (?P<date>) group
patterns:                    # tried in order; first match wins
  - id: failed
    type: ignore
    reason: failed payment
    match: '...'
  - id: upi-debit
    type: transaction        # transaction | balance | ignore
    direction: debit         # debit | credit
    channel: upi             # upi | imps | neft | rtgs | nach | card | atm | other
    kind: payment            # payment | refund | reversal | own_transfer | card_payment
    match: '...(?P<amount>...)...(?P<account>...)...'
```

Named groups the parser understands:

| Group | Meaning |
| --- | --- |
| `amount` | Required for transactions. Indian grouping and a trailing `/-` are fine. |
| `account` | Required. The last four digits are kept; a bank that shows only three (ICICI `XX378`) is matched against accounts whose last four end with them. |
| `date` | Optional. Parsed with `date_formats`; otherwise the SMS time is used. |
| `time` | Optional, with `date`: `HH:MM:SS` or `HH:MM`, Indian time. |
| `ref` | UPI RRN, IMPS/NEFT UTR, or other bank reference. Drives dedup. |
| `vpa`, `counterparty` | Payee or payer. |
| `target` | For `card_payment` from a bank account: the card's last four digits. |
| `balance` | Bank profiles only. Card profiles may not capture a balance: an available limit is not money you have. |

A transaction pattern may set `account: default` when the bank's SMS never names the account; the last digits then come from `BRIDGE_DEFAULT_ACCOUNTS` in `.env` (`profile=last4`). Dates without a year (`15AUG`) take the latest such date not after the SMS.

Matching ignores case and treats any run of whitespace as one space.
