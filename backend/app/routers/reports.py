from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_db
from ..models import Account, Category, PayableReceivable, Transaction
from ..schemas import ReportItem

router = APIRouter(prefix="/api/reports", tags=["Relatórios"])


@router.get("/cashflow", response_model=list[ReportItem])
def report_cashflow(db: Session = Depends(get_db), user=Depends(require_role("viewer"))):
    totals = (
        db.query(Transaction.transaction_type, func.sum(Transaction.value))
        .group_by(Transaction.transaction_type)
        .all()
    )
    return [ReportItem(label=kind, value=float(total)) for kind, total in totals]


@router.get("/by-category", response_model=list[ReportItem])
def report_by_category(db: Session = Depends(get_db), user=Depends(require_role("viewer"))):
    totals = (
        db.query(Category.name, func.sum(Transaction.value))
        .join(Transaction, Transaction.category_id == Category.id)
        .group_by(Category.name)
        .all()
    )
    return [ReportItem(label=name, value=float(total)) for name, total in totals]


@router.get("/by-account", response_model=list[ReportItem])
def report_by_account(db: Session = Depends(get_db), user=Depends(require_role("viewer"))):
    totals = (
        db.query(Account.name, func.sum(Transaction.value))
        .join(Transaction, Transaction.account_id == Account.id)
        .group_by(Account.name)
        .all()
    )
    return [ReportItem(label=name, value=float(total)) for name, total in totals]


@router.get("/overdue")
def report_overdue(db: Session = Depends(get_db), user=Depends(require_role("viewer"))):
    today = date.today()
    overdue = (
        db.query(PayableReceivable)
        .filter(PayableReceivable.due_date < today, PayableReceivable.status == "Pendente")
        .all()
    )
    return overdue
