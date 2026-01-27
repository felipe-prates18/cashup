from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_db
from ..models import Account, PayableReceivable, Transaction
from ..schemas import CashflowSummary

router = APIRouter(prefix="/api/cashflow", tags=["Fluxo de Caixa"])


@router.get("/summary", response_model=CashflowSummary)
def cashflow_summary(db: Session = Depends(get_db), user=Depends(require_role("viewer"))):
    accounts = db.query(Account).all()
    transactions = db.query(Transaction).all()
    total_balance = sum(account.initial_balance for account in accounts)
    total_in = 0
    total_out = 0
    for transaction in transactions:
        if transaction.transaction_type == "Entrada":
            total_in += transaction.value
            total_balance += transaction.value
        else:
            total_out += transaction.value
            total_balance -= transaction.value
    return CashflowSummary(total_balance=total_balance, total_in=total_in, total_out=total_out)


@router.get("/projection")
def cashflow_projection(db: Session = Depends(get_db), user=Depends(require_role("viewer"))):
    titles = db.query(PayableReceivable).all()
    projection = []
    for title in titles:
        projection.append(
            {
                "title_id": title.id,
                "due_date": title.due_date,
                "value": title.value,
                "type": title.title_type,
                "status": title.status,
            }
        )
    return {"as_of": date.today(), "projection": projection}
