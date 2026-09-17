from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models.lab import Lab
from app.db.session import get_db
from app.schemas.lab import LabCreate, LabOut

router = APIRouter(prefix="/labs", tags=["labs"])


@router.get("", response_model=list[LabOut])
def list_labs(db: Session = Depends(get_db)) -> list[Lab]:
    return db.query(Lab).order_by(Lab.code).all()


@router.post("", response_model=LabOut)
def create_lab(payload: LabCreate, db: Session = Depends(get_db)) -> Lab:
    lab = Lab(**payload.model_dump())
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return lab
