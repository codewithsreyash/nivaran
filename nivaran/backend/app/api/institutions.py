"""Institution management API routes."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..dependencies import get_current_user, require_not_readonly
from ..models import Institution, User, InstitutionVerificationStatus
from ..schemas import InstitutionCreate, InstitutionUpdate, InstitutionOut
from ..services.audit_service import log_action

router = APIRouter(prefix="/api/institutions", tags=["institutions"])


@router.get("", response_model=dict)
def list_institutions(
    search: Optional[str] = Query(None),
    state: Optional[str] = None,
    region: Optional[str] = None,
    verification_status: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Institution).filter(Institution.is_active == True)
    if search:
        q = q.filter(Institution.name.ilike(f"%{search}%"))
    if state:
        q = q.filter(Institution.state == state)
    if region:
        q = q.filter(Institution.region == region)
    if verification_status:
        q = q.filter(Institution.verification_status == verification_status)
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [InstitutionOut.model_validate(i) for i in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@router.post("", response_model=InstitutionOut, status_code=201)
def create_institution(
    payload: InstitutionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_not_readonly),
):
    existing = db.query(Institution).filter(
        Institution.institution_id == payload.institution_id
    ).first()
    if existing:
        raise HTTPException(400, f"Institution ID '{payload.institution_id}' already exists")
    inst = Institution(**payload.model_dump())
    db.add(inst)
    db.commit()
    db.refresh(inst)
    log_action(db, "institution.created", user_id=current_user.id,
               resource_type="institution", resource_id=inst.id,
               details={"name": inst.name})
    return InstitutionOut.model_validate(inst)


@router.get("/{institution_id}", response_model=InstitutionOut)
def get_institution(
    institution_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(404, "Institution not found")
    return InstitutionOut.model_validate(inst)


@router.patch("/{institution_id}", response_model=InstitutionOut)
def update_institution(
    institution_id: int,
    payload: InstitutionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_not_readonly),
):
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(404, "Institution not found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(inst, k, v)
    db.commit()
    db.refresh(inst)
    log_action(db, "institution.updated", user_id=current_user.id,
               resource_type="institution", resource_id=inst.id)
    return InstitutionOut.model_validate(inst)
