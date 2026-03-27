"""Parse P&L emails (.eml) into structured dicts for database ingestion."""

import email
import email.policy
import quopri
import re
from pathlib import Path

# Month name to number mapping (English)
MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

# P&L label to dict key mapping
PL_LABELS = {
    "TOTAL REVENUE": "revenue",
    "TOTAL REVENUE N-1": "revenue_n1",
    "Rebate": "rebate",
    "- Food cost": "food_cost",
    "- Beverage cost": "beverage_cost",
    "Total F&B Cost": "total_fb_cost",
    "Total Other Ex": "total_other_expenses",
    "TOTAL MONTHLY EXP": "total_monthly_exp",
    "GOP before fee": "gop_before_fee",
    "Other and Special Fee": "other_special_fee",
    "Monthly Provision": "monthly_provision",
    "GOP NET": "gop_net",
}


def _parse_number(s: str) -> int | None:
    """Parse a formatted number like '2,194,431' or '2,194,431.00' into int.
    Returns None if the string is empty or whitespace-only.
    """
    s = s.strip()
    if not s:
        return None
    # Remove commas and trailing decimals
    s = s.replace(",", "")
    # Handle negative numbers
    try:
        val = float(s)
        return int(val)
    except ValueError:
        return None


def _decode_quoted_printable(raw: str) -> str:
    """Decode quoted-printable encoded text, handling iso-8859-1."""
    try:
        decoded_bytes = quopri.decodestring(raw.encode("ascii", errors="replace"))
        return decoded_bytes.decode("iso-8859-1", errors="replace")
    except Exception:
        return raw


def _get_plain_text(msg: email.message.Message) -> str:
    """Extract plain text body from email message, handling MIME structure."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=False)
                cte = part.get("Content-Transfer-Encoding", "")
                if cte.lower() == "quoted-printable":
                    return _decode_quoted_printable(payload)
                if isinstance(payload, bytes):
                    return payload.decode("iso-8859-1", errors="replace")
                return payload
    else:
        payload = msg.get_payload(decode=False)
        cte = msg.get("Content-Transfer-Encoding", "")
        if cte.lower() == "quoted-printable":
            return _decode_quoted_printable(payload)
        if isinstance(payload, bytes):
            return payload.decode("iso-8859-1", errors="replace")
        return payload
    return ""


def _parse_subject(subject: str) -> tuple[str, str]:
    """Parse restaurant name and month from subject line.

    Subject format: 'P&L <restaurant name> <Month> <Year>'
    Returns (restaurant_name, month_str) where month_str is 'YYYY-MM-01'.
    """
    # Match: P&L <name> <month_word> <year>
    m = re.match(r"P&L\s+(.+?)\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})", subject, re.IGNORECASE)
    if not m:
        raise ValueError(f"Cannot parse subject: {subject!r}")
    name = m.group(1).strip()
    month_num = MONTH_MAP[m.group(2).lower()]
    year = int(m.group(3))
    return name, f"{year}-{month_num:02d}-01"


def _extract_restaurant_code(body: str) -> str | None:
    """Extract restaurant code like '27-Parma Central Eastville' from body."""
    # Pattern: digits followed by dash and name, on its own line
    m = re.search(r"^(\d+-[A-Za-z][A-Za-z &]+)\s*$", body, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


def _extract_pl(body: str) -> dict:
    """Extract P&L values from the plain text body.

    The body has labels on separate lines, with values on subsequent lines.
    Lines may be separated by blank lines and tab/whitespace lines.
    """
    lines = body.split("\n")
    pl = {}

    for label, key in PL_LABELS.items():
        # Find the line containing the label
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == label:
                # Look for a number on the same line (after tab) or on subsequent non-empty lines
                # Check remainder of current line after label
                after_label = line[line.index(label) + len(label):]
                num = _parse_number(after_label)
                if num is not None:
                    pl[key] = num
                    break

                # Search subsequent lines for first number
                for j in range(i + 1, min(i + 6, len(lines))):
                    candidate = lines[j].strip()
                    # Skip empty lines and lines that are just tabs/whitespace
                    if not candidate or candidate == "\t":
                        continue
                    # Skip percentage lines
                    if candidate.endswith("%"):
                        continue
                    # Check if this is a known label (stop searching)
                    if any(candidate == lab for lab in PL_LABELS):
                        break
                    num = _parse_number(candidate)
                    if num is not None:
                        pl[key] = num
                        break
                    # If it looks like a non-numeric line, stop
                    if re.match(r"[A-Za-z]", candidate):
                        break
                break

    # Fill in missing fields with 0 or None
    for key in PL_LABELS.values():
        if key not in pl:
            if key == "revenue_n1":
                pl[key] = None
            else:
                pl[key] = 0

    return pl


def _extract_dividend(body: str) -> dict | None:
    """Extract dividend info from profit-sharing table if present.

    Looks for 'Le partage' section, then finds the 'Guillaume' row and
    extracts the THB amount.
    """
    # Check if there's a profit-sharing section
    if "partage" not in body.lower():
        return None

    lines = body.split("\n")
    for i, line in enumerate(lines):
        if line.strip().lower() == "guillaume":
            # Guillaume's percentage and amount are on subsequent lines
            for j in range(i + 1, min(i + 6, len(lines))):
                candidate = lines[j].strip()
                if not candidate:
                    continue
                # Skip percentage
                if candidate.endswith("%"):
                    continue
                # Try to parse as amount (will look like '267,227.56')
                candidate_clean = candidate.replace(",", "")
                try:
                    amount = float(candidate_clean)
                    return {"my_share_thb": amount}
                except ValueError:
                    continue
    return None


def parse_eml_file(filepath: str | Path) -> dict:
    """Parse a P&L email file and return structured data.

    Args:
        filepath: Path to .eml file.

    Returns:
        Dict with keys: restaurant_name, month, restaurant_code, pl, dividend, email_date
    """
    filepath = Path(filepath)
    raw = filepath.read_bytes()
    msg = email.message_from_bytes(raw, policy=email.policy.compat32)

    subject = msg["Subject"]
    email_date = msg["Date"]

    restaurant_name, month = _parse_subject(subject)
    body = _get_plain_text(msg)
    restaurant_code = _extract_restaurant_code(body)
    pl = _extract_pl(body)
    dividend = _extract_dividend(body)

    return {
        "restaurant_name": restaurant_name,
        "month": month,
        "restaurant_code": restaurant_code,
        "pl": pl,
        "dividend": dividend,
        "email_date": email_date,
    }
