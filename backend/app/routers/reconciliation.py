import csv
import io
import re
from datetime import datetime
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_db
from ..models import ReconciliationItem
from ..schemas import ReconciliationItemOut

router = APIRouter(prefix="/api/reconciliation", tags=["Conciliação"])


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


@router.get("", response_model=list[ReconciliationItemOut])
def list_reconciliation(db: Session = Depends(get_db), user=Depends(require_role("viewer"))):
    return db.query(ReconciliationItem).all()
