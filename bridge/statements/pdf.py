"""Open a password-protected statement PDF in memory only. No unlocked copy is ever written to disk."""
import io
import warnings

import pdfplumber
import pikepdf


class PdfError(Exception):
    pass


def unlock(path, candidates):
    """Return (index of the password that worked, list of page texts). Raises PdfError if none works."""
    tried = [""] + list(candidates)  # some statements are not protected
    for index, password in enumerate(tried):
        try:
            with pikepdf.open(path, password=password) as pdf:
                buffer = io.BytesIO()
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")  # harmless notes about form widgets
                    pdf.save(buffer)  # decrypted bytes stay in memory
        except pikepdf.PasswordError:
            continue
        except pikepdf.PdfError as exc:
            raise PdfError(f"not a readable PDF ({type(exc).__name__})") from None
        buffer.seek(0)
        with pdfplumber.open(buffer) as doc:
            pages = [page.extract_text(layout=False) or "" for page in doc.pages]
        buffer.close()
        return index - 1, pages  # -1 means it opened without a password
    raise PdfError("none of the saved passwords opened this PDF")
