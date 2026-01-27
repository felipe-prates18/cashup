from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import require_role
from ..database import get_db
from ..models import Category, CostCenter
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
