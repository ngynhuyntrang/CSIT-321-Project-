from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.db.models.ingestion import IngestionRun
from app.db.models.user import ROLE_ADMIN, User
from app.db.session import get_db
from app.ingestion.service import run_ingestion
from app.schemas.ingestion import IngestionRunSummary

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/upload", response_model=IngestionRunSummary)
async def upload_timetable(
    file: UploadFile,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(ROLE_ADMIN)),
) -> IngestionRun:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    content = await file.read()
    return run_ingestion(db, file.filename, content)


@router.get("/{run_id}/summary", response_model=IngestionRunSummary)
def get_ingestion_summary(
    run_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> IngestionRun:
    ingestion_run = db.get(IngestionRun, run_id)
    if ingestion_run is None:
        raise HTTPException(status_code=404, detail="Ingestion run not found.")
    return ingestion_run
