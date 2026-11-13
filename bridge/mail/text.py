"""Turn a Gmail API message into (subject, text, pdf attachments) with the standard library only."""
import base64
import html
import re


def _decode(data):
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")


def safe_filename(name):
    """Banks put full card or account numbers in attachment names. Keep only the last 4 digits of any long number."""
    return re.sub(r"\d{9,}", lambda m: "X" * (len(m.group()) - 4) + m.group()[-4:], name)


def _walk(part, plain, rich, pdfs):
    mime = part.get("mimeType", "")
    body = part.get("body", {})
    filename = part.get("filename") or ""
    if filename:
        if mime == "application/pdf" or filename.lower().endswith(".pdf"):
            pdfs.append({"filename": safe_filename(filename)[:255], "attachment_id": body.get("attachmentId", ""), "size": body.get("size", 0)})
    elif body.get("data"):
        if mime == "text/plain":
            plain.append(_decode(body["data"]))
        elif mime == "text/html":
            rich.append(_decode(body["data"]))
    for sub in part.get("parts", []) or []:
        _walk(sub, plain, rich, pdfs)


def html_to_text(markup):
    markup = re.sub(r"(?is)<(script|style|head).*?</\1>", " ", markup)
    markup = re.sub(r"(?i)<br\s*/?>|</p>|</tr>|</div>|</li>|</h\d>", "\n", markup)
    return html.unescape(re.sub(r"<[^>]+>", " ", markup))


def message_parts(message):
    payload = message.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
    plain, rich, pdfs = [], [], []
    _walk(payload, plain, rich, pdfs)
    text = "\n".join(plain) if plain else html_to_text("\n".join(rich))
    text = "\n".join(" ".join(line.split()) for line in text.splitlines() if line.strip())
    return headers.get("from", ""), headers.get("subject", ""), text[:20000], pdfs
