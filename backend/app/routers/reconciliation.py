import csv
import io
import logging
import re
import zlib
from datetime import datetime
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_db
from ..models import ActionLog, ReconciliationItem, Transaction
from ..schemas import ReconciliationItemOut, TransactionOut

router = APIRouter(prefix="/api/reconciliation", tags=["Conciliação"])
logger = logging.getLogger("cashup.reconciliation")

PORTUGUESE_MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "março": 3,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
DATE_HEADER_RE = re.compile(r"(\d{1,2}) de ([a-zç]+) de (\d{4}),", re.IGNORECASE)
AMOUNT_RE = re.compile(r"(?P<sign>-)?\s*R\$\s*(?P<value>\d{1,3}(?:\.\d{3})*,\d{2})\s*$")
LITERAL_STRING_RE = re.compile(r"\((?:\\.|[^\\()])*\)")
IGNORED_LINE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"^internet banking empresarial$",
        r"^agência:\s*\d+",
        r"^agencia:\s*\d+",
        r"^conta:\s*\d+",
        r"^real precatorio",
        r"^saldo do dia$",
        r"^extrato",
        r"^página \d+",
    )
]


def _decode_pdf_literal(value: str) -> str:
    buffer = []
    index = 0
    while index < len(value):
        char = value[index]
        if char != "\\":
            buffer.append(char)
            index += 1
            continue
        index += 1
        if index >= len(value):
            break
        escaped = value[index]
        simple_escapes = {
            "n": "\n",
            "r": "\r",
            "t": "\t",
            "b": "\b",
            "f": "\f",
            "\\": "\\",
            "(": "(",
            ")": ")",
        }
        if escaped in simple_escapes:
            buffer.append(simple_escapes[escaped])
            index += 1
            continue
        if escaped.isdigit():
            octal = escaped
            for _ in range(2):
                if index + 1 < len(value) and value[index + 1].isdigit():
                    index += 1
                    octal += value[index]
            buffer.append(chr(int(octal, 8)))
            index += 1
            continue
        buffer.append(escaped)
        index += 1
    return "".join(buffer)


def _decompress_pdf_stream(raw_stream: bytes) -> list[bytes]:
    candidates = [raw_stream]
    for wbits in (zlib.MAX_WBITS, -zlib.MAX_WBITS):
        try:
            candidates.append(zlib.decompress(raw_stream, wbits))
        except zlib.error:
            continue
    return candidates


def _build_tounicode_map(content: bytes) -> dict[str, str]:
    glyph_map: dict[str, str] = {}
    object_re = re.compile(rb"\d+\s+\d+\s+obj(.*?)endobj", re.S)
    for object_match in object_re.finditer(content):
        object_body = object_match.group(1)
        if b"begincmap" not in object_body:
            continue
        stream_match = re.search(rb"stream\r?\n(.*?)\r?\nendstream", object_body, re.S)
        if not stream_match:
            continue
        for candidate in _decompress_pdf_stream(stream_match.group(1)):
            decoded = candidate.decode("latin-1", errors="ignore")
            if "begincmap" not in decoded:
                continue
            for src, dst in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", decoded):
                glyph_map[src.upper()] = _decode_pdf_hex_string(dst, {})
            range_pattern = re.compile(
                r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(?:<([0-9A-Fa-f]+)>|\[(.*?)\])",
                re.S,
            )
            for start_hex, end_hex, single_target, target_list in range_pattern.findall(decoded):
                start = int(start_hex, 16)
                end = int(end_hex, 16)
                if single_target:
                    current = int(single_target, 16)
                    for offset, codepoint in enumerate(range(start, end + 1)):
                        glyph_map[f"{codepoint:0{len(start_hex)}X}"] = _decode_pdf_hex_string(
                            f"{current + offset:0{len(single_target)}X}", {}
                        )
                elif target_list:
                    targets = [value.upper() for value in re.findall(r"<([0-9A-Fa-f]+)>", target_list)]
                    for offset, codepoint in enumerate(range(start, end + 1)):
                        if offset >= len(targets):
                            break
                        glyph_map[f"{codepoint:0{len(start_hex)}X}"] = _decode_pdf_hex_string(targets[offset], {})
            break
    return glyph_map


def _decode_pdf_hex_string(value: str, glyph_map: dict[str, str]) -> str:
    normalized = re.sub(r"[^0-9A-Fa-f]", "", value).upper()
    if not normalized:
        return ""

    for chunk_size in (4, 2):
        if len(normalized) % chunk_size != 0:
            continue
        chunks = [normalized[index : index + chunk_size] for index in range(0, len(normalized), chunk_size)]
        if glyph_map and any(chunk in glyph_map for chunk in chunks):
            decoded = []
            for chunk in chunks:
                if chunk in glyph_map:
                    decoded.append(glyph_map[chunk])
                else:
                    decoded.append(_decode_pdf_hex_string(chunk, {}))
            return "".join(decoded)

    try:
        if len(normalized) % 4 == 0:
            decoded_utf16 = bytes.fromhex(normalized).decode("utf-16-be")
            if decoded_utf16.strip("\x00").strip():
                return decoded_utf16
    except Exception:
        pass

    try:
        decoded_latin = bytes.fromhex(normalized).decode("latin-1", errors="ignore")
        if decoded_latin:
            return decoded_latin
    except Exception:
        pass

    return ""


def _decode_pdf_text_token(token: str, glyph_map: dict[str, str]) -> str:
    token = token.strip()
    if token.startswith("(") and token.endswith(")"):
        return _decode_pdf_literal(token[1:-1])
    if token.startswith("<") and token.endswith(">"):
        return _decode_pdf_hex_string(token[1:-1], glyph_map)
    return token


def _extract_generic_text_fragments(stream: str, glyph_map: dict[str, str]) -> list[str]:
    fragments: list[str] = []
    for match in re.finditer(r"\((?:\\.|[^\\()])*\)|<[0-9A-Fa-f\s]{4,}>", stream):
        decoded = _decode_pdf_text_token(match.group(0), glyph_map)
        normalized = re.sub(r"\s+", " ", decoded).strip()
        if normalized and any(char.isalnum() for char in normalized):
            fragments.append(normalized)
    return fragments


def _extract_text_lines_from_stream(stream: str, glyph_map: dict[str, str]) -> list[str]:
    lines: list[str] = []
    current_parts: list[str] = []
    token_re = re.compile(
        r"(?P<array>\[(?:.|\n)*?\]\s*TJ)|"
        r"(?P<text>\((?:\\.|[^\\()])*\)\s*Tj)|"
        r"(?P<hex><[0-9A-Fa-f\s]+>\s*Tj)|"
        r"(?P<newline>T\*)|"
        r"(?P<move>-?\d+(?:\.\d+)?\s+-?\d+(?:\.\d+)?\s+Td)|"
        r"(?P<setmatrix>(?:-?\d+(?:\.\d+)?\s+){6}Tm)|"
        r"(?P<begin>BT)|"
        r"(?P<end>ET)",
        re.S,
    )
    for match in token_re.finditer(stream):
        token = match.group(0)
        if match.lastgroup == "text":
            literal = token[: token.rfind(")")]
            current_parts.append(_decode_pdf_literal(literal[1:]))
        elif match.lastgroup == "hex":
            hex_token = token[: token.rfind(">") + 1]
            decoded = _decode_pdf_text_token(hex_token, glyph_map)
            if decoded:
                current_parts.append(decoded)
        elif match.lastgroup == "array":
            fragments = [
                fragment.group(0)
                for fragment in re.finditer(r"\((?:\\.|[^\\()])*\)|<[0-9A-Fa-f\s]+>", token)
            ]
            text = "".join(_decode_pdf_text_token(fragment, glyph_map) for fragment in fragments)
            if text:
                current_parts.append(text)
        elif match.lastgroup in {"newline", "move", "setmatrix", "end"}:
            line = " ".join(part.strip() for part in current_parts if part.strip()).strip()
            if line:
                lines.append(line)
            current_parts = []
    line = " ".join(part.strip() for part in current_parts if part.strip()).strip()
    if line:
        lines.append(line)
    return lines


def _extract_pdf_pages(content: bytes) -> list[list[str]]:
    pages: list[list[str]] = []
    glyph_map = _build_tounicode_map(content)
    decoded_streams: list[str] = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", content, re.S):
        raw_stream = match.group(1)
        for candidate in _decompress_pdf_stream(raw_stream):
            decoded = candidate.decode("latin-1", errors="ignore")
            decoded_streams.append(decoded)
            if "BT" not in decoded and "Tj" not in decoded and "TJ" not in decoded:
                continue
            lines = [
                re.sub(r"\s+", " ", line).strip()
                for line in _extract_text_lines_from_stream(decoded, glyph_map)
            ]
            lines = [line for line in lines if line]
            if lines:
                pages.append(lines)
                break
    if not pages:
        generic_lines: list[str] = []
        for decoded in decoded_streams:
            generic_lines.extend(_extract_generic_text_fragments(decoded, glyph_map))
        if generic_lines:
            logger.info("Falling back to generic PDF text extraction with %s fragments.", len(generic_lines))
            pages.append(generic_lines)
    logger.info("PDF extraction generated %s text page blocks and %s glyph mappings.", len(pages), len(glyph_map))
    return pages


def _normalize_statement_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip(" \u00a0")


def _line_is_ignored(line: str) -> bool:
    normalized = _normalize_statement_line(line)
    if not normalized:
        return True
    return any(pattern.search(normalized) for pattern in IGNORED_LINE_PATTERNS)


def _extract_amount(line: str):
    match = AMOUNT_RE.search(line)
    if not match:
        return None
    value = float(match.group("value").replace(".", "").replace(",", "."))
    if match.group("sign"):
        value *= -1
    return {
        "value": value,
        "text_before_amount": _normalize_statement_line(line[: match.start()]),
    }


def _parse_santander_pdf_transactions(content: bytes, filename: str) -> list[dict]:
    pages = _extract_pdf_pages(content)
    transactions = []
    for page_number, lines in enumerate(pages, start=1):
        current_date = None
        pending_parts: list[str] = []
        for raw_line in lines:
            line = _normalize_statement_line(raw_line)
            if not line:
                continue
            date_match = DATE_HEADER_RE.search(line.lower())
            if date_match:
                day = int(date_match.group(1))
                month = PORTUGUESE_MONTHS.get(date_match.group(2).lower())
                year = int(date_match.group(3))
                current_date = datetime(year, month, day).date() if month else None
                pending_parts = []
                continue
            if _line_is_ignored(line):
                pending_parts = []
                continue
            if current_date is None:
                continue
            amount_data = _extract_amount(line)
            if not amount_data:
                pending_parts.append(line)
                continue
            parts = [part for part in pending_parts if part]
            if amount_data["text_before_amount"]:
                parts.append(amount_data["text_before_amount"])
            pending_parts = []
            if not parts:
                continue
            description = parts[0]
            detail = " · ".join(parts[1:]) if len(parts) > 1 else None
            if description.lower().startswith("saldo do dia"):
                continue
            value = amount_data["value"]
            transactions.append(
                {
                    "date": current_date,
                    "description": description,
                    "detail": detail,
                    "value": abs(value),
                    "signed_value": value,
                    "transaction_type": "Saída" if value < 0 else "Entrada",
                    "source_page": page_number,
                    "external_id": f"{filename}-{page_number}-{current_date.isoformat()}-{len(transactions) + 1}",
                }
            )
    return transactions


def _parse_ofx(content: str):
    transactions = []
    pattern = re.compile(r"<STMTTRN>(.*?)</STMTTRN>", re.DOTALL)
    for block in pattern.findall(content):
        date_match = re.search(r"<DTPOSTED>(\d{8})", block)
        amount_match = re.search(r"<TRNAMT>([-0-9.]+)", block)
        name_match = re.search(r"<NAME>(.+)", block)
        if date_match and amount_match and name_match:
            date = datetime.strptime(date_match.group(1), "%Y%m%d").date()
            transactions.append(
                {
                    "date": date,
                    "description": name_match.group(1).strip(),
                    "value": float(amount_match.group(1)),
                }
            )
    return transactions


@router.post("/import", response_model=list[ReconciliationItemOut])
def import_statement(file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(require_role("finance"))):
    content = file.file.read()
    decoded = content.decode("utf-8", errors="ignore")
    items = []
    if file.filename.endswith(".ofx"):
        parsed = _parse_ofx(decoded)
        for entry in parsed:
            item = ReconciliationItem(**entry)
            db.add(item)
            items.append(item)
    else:
        reader = csv.DictReader(io.StringIO(decoded))
        for row in reader:
            date = datetime.strptime(row["date"], "%Y-%m-%d").date()
            item = ReconciliationItem(
                date=date,
                description=row["description"],
                value=float(row["value"]),
                external_id=row.get("external_id"),
            )
            db.add(item)
            items.append(item)
    db.commit()
    for item in items:
        db.refresh(item)
    return items


@router.post("/import/pdf", response_model=list[TransactionOut])
def import_pdf_statement(
    file: UploadFile = File(...),
    account_id: int = Form(...),
    income_category_id: int = Form(...),
    expense_category_id: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(require_role("finance")),
):
    filename = file.filename or "extrato.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Envie um arquivo PDF válido.")
    content = file.file.read()
    parsed = _parse_santander_pdf_transactions(content, filename)
    if not parsed:
        logger.warning("PDF import failed to parse statement lines for file %s.", filename)
        raise HTTPException(
            status_code=400,
            detail="Não foi possível localizar lançamentos no PDF. Use um extrato Santander no mesmo layout do template.",
        )
    logger.info("Parsed %s statement lines from %s for account %s.", len(parsed), filename, account_id)
    created_transactions = []
    for entry in parsed:
        category_id = income_category_id if entry["transaction_type"] == "Entrada" else expense_category_id
        notes = f"Importado do extrato PDF {filename} na página {entry['source_page']}."
        if entry["detail"]:
            notes = f"{notes} Detalhes: {entry['detail']}"
        transaction = Transaction(
            transaction_type=entry["transaction_type"],
            date=entry["date"],
            value=entry["value"],
            category_id=category_id,
            account_id=account_id,
            payment_method="Extrato bancário PDF",
            description=entry["description"],
            client_supplier=entry["detail"],
            document_number=entry["external_id"],
            notes=notes,
            invoice_number=None,
            document_path=filename,
            tax_id=None,
        )
        db.add(transaction)
        db.flush()
        db.add(
            ReconciliationItem(
                external_id=entry["external_id"],
                date=entry["date"],
                description=entry["description"],
                value=entry["signed_value"],
                status="Importado",
                matched_transaction_id=transaction.id,
            )
        )
        db.add(ActionLog(user_id=user.id, action="Importou PDF", entity="Transaction", entity_id=transaction.id))
        created_transactions.append(transaction)
    db.commit()
    for transaction in created_transactions:
        db.refresh(transaction)
    return created_transactions


@router.get("", response_model=list[ReconciliationItemOut])
def list_reconciliation(db: Session = Depends(get_db), user=Depends(require_role("viewer"))):
    return db.query(ReconciliationItem).all()
