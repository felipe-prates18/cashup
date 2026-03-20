from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_db
from ..models import Category, CostCenter, Transaction
from ..schemas import CategoryCreate, CategoryOut, CostCenterCreate, CostCenterOut

router = APIRouter(prefix="/api/categories", tags=["Categorias"])


@router.post("", response_model=CategoryOut)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db), user=Depends(require_role("finance"))):
    category = Category(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db), user=Depends(require_role("viewer"))):
    return db.query(Category).all()


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_role("finance"))
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoria não encontrada.")

    has_children = db.query(Category).filter(Category.parent_id == category_id).first()
    if has_children:
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir uma categoria que possui subcategorias."
        )

    has_transactions = db.query(Transaction).filter(Transaction.category_id == category_id).first()
    if has_transactions:
        raise HTTPException(
            status_code=400,
            detail="Não é possível excluir uma categoria com lançamentos vinculados."
        )

    db.delete(category)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/cost-centers", response_model=CostCenterOut)
def create_cost_center(payload: CostCenterCreate, db: Session = Depends(get_db), user=Depends(require_role("finance"))):
    center = CostCenter(**payload.model_dump())
    db.add(center)
    db.commit()
    db.refresh(center)
    return center


@router.get("/cost-centers", response_model=list[CostCenterOut])
def list_cost_centers(db: Session = Depends(get_db), user=Depends(require_role("viewer"))):
    return db.query(CostCenter).all()
