"""
Relationship Graph API — Provides nodes and edges for complaint relationship visualization.
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_

from ..database import get_db
from ..dependencies import get_bureau_scope, get_current_user, scope_query_to_bureau
from ..models import (
    Complaint, User, Bureau, Institution, OverlapResult,
    UserRole, ComplaintStatus, PriorityLevel
)

router = APIRouter(prefix="/api/graph", tags=["graph"])


def _build_graph_nodes(
    db: Session,
    focus_complaint_id: Optional[int] = None,
    institution_id: Optional[int] = None,
    bureau_id: Optional[int] = None,
    officer_id: Optional[int] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    relationship_type: Optional[str] = None,
    confirmed_only: bool = False,
    overdue_only: bool = False,
    inactive_only: bool = False,
    authorized_bureau_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Build graph nodes based on filters."""
    nodes = []
    node_ids = set()

    # Complaint nodes
    q = db.query(Complaint).options(
        joinedload(Complaint.institution),
        joinedload(Complaint.bureau),
        joinedload(Complaint.assigned_officer),
    )
    if authorized_bureau_id is not None:
        q = q.filter(Complaint.bureau_id == authorized_bureau_id)

    if focus_complaint_id is not None:
        q = q.filter(Complaint.id == focus_complaint_id)
    else:
        if institution_id is not None:
            q = q.filter(Complaint.institution_id == institution_id)
        if bureau_id is not None:
            q = q.filter(Complaint.bureau_id == bureau_id)
        if officer_id is not None:
            q = q.filter(Complaint.assigned_officer_id == officer_id)
        if category is not None:
            q = q.filter(Complaint.category == category)
        if priority is not None:
            q = q.filter(
                or_(
                    Complaint.assigned_priority_level == priority,
                    Complaint.calculated_priority_level == priority
                )
            )
        if status is not None:
            q = q.filter(Complaint.status == status)
        if overdue_only:
            from datetime import datetime
            q = q.filter(
                Complaint.target_disposal_date < datetime.utcnow(),
                Complaint.status.notin_(["disposed", "closed"])
            )
        if inactive_only:
            from datetime import datetime, timedelta
            cutoff = datetime.utcnow() - timedelta(days=10)
            q = q.filter(
                Complaint.last_action_date < cutoff,
                Complaint.status.notin_(["disposed", "closed"])
            )

    complaints = q.all()

    for c in complaints:
        node_id = f"complaint:{c.id}"
        if node_id in node_ids:
            continue
        node_ids.add(node_id)

        nodes.append({
            "id": node_id,
            "type": "complaint",
            "label": c.complaint_id,
            "title": c.title,
            "status": c.status.value if c.status else None,
            "priority": (c.assigned_priority_level or c.calculated_priority_level).value if (c.assigned_priority_level or c.calculated_priority_level) else None,
            "category": c.category.value if c.category else None,
            "institution_id": c.institution_id,
            "institution_name": c.institution_name_snapshot,
            "bureau_id": c.bureau_id,
            "bureau_name": c.bureau.name if c.bureau else None,
            "officer_id": c.assigned_officer_id,
            "officer_name": c.assigned_officer.full_name if c.assigned_officer else None,
            "registration_date": c.registration_date.isoformat() if c.registration_date else None,
        })

        # Add connected entities
        if c.institution_id and f"institution:{c.institution_id}" not in node_ids:
            node_ids.add(f"institution:{c.institution_id}")
            nodes.append({
                "id": f"institution:{c.institution_id}",
                "type": "institution",
                "label": c.institution.name if c.institution else c.institution_name_snapshot,
                "institution_id": c.institution.institution_id if c.institution else None,
                "state": c.institution.state if c.institution else None,
            })

        if c.bureau_id and f"bureau:{c.bureau_id}" not in node_ids:
            node_ids.add(f"bureau:{c.bureau_id}")
            nodes.append({
                "id": f"bureau:{c.bureau_id}",
                "type": "bureau",
                "label": c.bureau.name if c.bureau else f"Bureau {c.bureau_id}",
                "code": c.bureau.code if c.bureau else None,
            })

        if c.assigned_officer_id and f"officer:{c.assigned_officer_id}" not in node_ids:
            node_ids.add(f"officer:{c.assigned_officer_id}")
            nodes.append({
                "id": f"officer:{c.assigned_officer_id}",
                "type": "officer",
                "label": c.assigned_officer.full_name if c.assigned_officer else f"Officer {c.assigned_officer_id}",
                "bureau_id": c.assigned_officer.bureau_id if c.assigned_officer else None,
            })

    return nodes


def _build_graph_edges(
    db: Session,
    focus_complaint_id: Optional[int] = None,
    relationship_type: Optional[str] = None,
    confirmed_only: bool = False,
    authorized_bureau_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Build graph edges based on complaint relationships."""
    edges = []
    edge_ids = set()

    if focus_complaint_id:
        complaints_query = db.query(Complaint).filter(Complaint.id == focus_complaint_id)
    else:
        complaints_query = db.query(Complaint)
    if authorized_bureau_id is not None:
        complaints_query = complaints_query.filter(Complaint.bureau_id == authorized_bureau_id)
    complaints = complaints_query.all()

    for c in complaints:
        # Complaint -> Institution
        if c.institution_id:
            edge_id = f"complaint:{c.id}-institution:{c.institution_id}"
            if edge_id not in edge_ids:
                edge_ids.add(edge_id)
                edges.append({
                    "id": edge_id,
                    "source": f"complaint:{c.id}",
                    "target": f"institution:{c.institution_id}",
                    "type": "filed_against",
                    "label": "filed against",
                    "confirmed": True,
                })

        # Complaint -> Bureau
        if c.bureau_id:
            edge_id = f"complaint:{c.id}-bureau:{c.bureau_id}"
            if edge_id not in edge_ids:
                edge_ids.add(edge_id)
                edges.append({
                    "id": edge_id,
                    "source": f"complaint:{c.id}",
                    "target": f"bureau:{c.bureau_id}",
                    "type": "handled_by",
                    "label": "handled by",
                    "confirmed": True,
                })

        # Complaint -> Officer
        if c.assigned_officer_id:
            edge_id = f"complaint:{c.id}-officer:{c.assigned_officer_id}"
            if edge_id not in edge_ids:
                edge_ids.add(edge_id)
                edges.append({
                    "id": edge_id,
                    "source": f"complaint:{c.id}",
                    "target": f"officer:{c.assigned_officer_id}",
                    "type": "assigned_to",
                    "label": "assigned to",
                    "confirmed": True,
                })

        # Officer -> Bureau
        if c.assigned_officer and c.assigned_officer.bureau_id:
            edge_id = f"officer:{c.assigned_officer_id}-bureau:{c.assigned_officer.bureau_id}"
            if edge_id not in edge_ids:
                edge_ids.add(edge_id)
                edges.append({
                    "id": edge_id,
                    "source": f"officer:{c.assigned_officer_id}",
                    "target": f"bureau:{c.assigned_officer.bureau_id}",
                    "type": "belongs_to",
                    "label": "belongs to",
                    "confirmed": True,
                })

    # Overlap/duplicate relationships
    overlaps = db.query(OverlapResult).options(
        joinedload(OverlapResult.primary_complaint),
        joinedload(OverlapResult.candidate_complaint),
    )
    if authorized_bureau_id is not None:
        overlaps = overlaps.filter(
            OverlapResult.primary_complaint.has(Complaint.bureau_id == authorized_bureau_id),
            OverlapResult.candidate_complaint.has(Complaint.bureau_id == authorized_bureau_id),
        )

    if focus_complaint_id:
        overlaps = overlaps.filter(
            or_(
                OverlapResult.primary_complaint_id == focus_complaint_id,
                OverlapResult.candidate_complaint_id == focus_complaint_id
            )
        )

    if confirmed_only:
        overlaps = overlaps.filter(OverlapResult.decision.isnot(None))
    else:
        overlaps = overlaps.filter(OverlapResult.review_status == "pending")

    for ov in overlaps.all():
        edge_id = f"complaint:{ov.primary_complaint_id}-complaint:{ov.candidate_complaint_id}"
        if edge_id in edge_ids:
            continue
        edge_ids.add(edge_id)

        edge_type = "possible_duplicate"
        if ov.decision:
            if ov.decision.value == "confirmed_duplicate":
                edge_type = "confirmed_duplicate"
            elif ov.decision.value == "related_independent":
                edge_type = "related_independent"

        if relationship_type and edge_type != relationship_type:
            continue

        edges.append({
            "id": edge_id,
            "source": f"complaint:{ov.primary_complaint_id}",
            "target": f"complaint:{ov.candidate_complaint_id}",
            "type": edge_type,
            "label": edge_type.replace("_", " "),
            "confirmed": ov.decision is not None,
            "similarity_score": ov.similarity_score,
            "decision": ov.decision.value if ov.decision else None,
            "decision_reason": ov.decision_reason,
        })

    return edges


@router.get("")
def get_graph(
    focus_complaint_id: Optional[int] = None,
    institution_id: Optional[int] = None,
    bureau_id: Optional[int] = None,
    officer_id: Optional[int] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    relationship_type: Optional[str] = None,
    confirmed_only: bool = False,
    overdue_only: bool = False,
    inactive_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get graph nodes and edges based on filters."""
    bureau_scope = get_bureau_scope(current_user)
    if bureau_scope is not None and bureau_id is not None and bureau_id != bureau_scope:
        raise HTTPException(status_code=403, detail="Cannot query graph data outside assigned bureau")
    nodes = _build_graph_nodes(
        db=db,
        focus_complaint_id=focus_complaint_id,
        institution_id=institution_id,
        bureau_id=bureau_id,
        officer_id=officer_id,
        category=category,
        priority=priority,
        status=status,
        relationship_type=relationship_type,
        confirmed_only=confirmed_only,
        overdue_only=overdue_only,
        inactive_only=inactive_only,
        authorized_bureau_id=bureau_scope,
    )

    edges = _build_graph_edges(
        db=db,
        focus_complaint_id=focus_complaint_id,
        relationship_type=relationship_type,
        confirmed_only=confirmed_only,
        authorized_bureau_id=bureau_scope,
    )

    # Calculate analytics
    analytics = {
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "complaints": len([n for n in nodes if n["type"] == "complaint"]),
        "institutions": len([n for n in nodes if n["type"] == "institution"]),
        "bureaus": len([n for n in nodes if n["type"] == "bureau"]),
        "officers": len([n for n in nodes if n["type"] == "officer"]),
        "possible_duplicates": len([e for e in edges if e["type"] == "possible_duplicate"]),
        "confirmed_duplicates": len([e for e in edges if e["type"] == "confirmed_duplicate"]),
        "related_independent": len([e for e in edges if e["type"] == "related_independent"]),
        "overdue_complaints": len([n for n in nodes if n.get("status") in ["under_process", "escalated"] and n.get("priority") == "critical"]),
        "unassigned_complaints": len([n for n in nodes if n["type"] == "complaint" and n.get("officer_id") is None]),
    }

    return {
        "nodes": nodes,
        "edges": edges,
        "analytics": analytics,
    }


@router.get("/analytics")
def get_graph_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get high-level graph analytics without full node/edge data."""
    bureau_scope = get_bureau_scope(current_user)
    complaints = scope_query_to_bureau(db.query(Complaint), Complaint.bureau_id, current_user)
    total_complaints = complaints.count()
    if bureau_scope is None:
        total_institutions = db.query(Institution).count()
        total_bureaus = db.query(Bureau).filter(Bureau.is_active == True).count()
        total_officers = db.query(User).filter(
            User.role == UserRole.BUREAU_OFFICER, User.is_active == True
        ).count()
    else:
        total_institutions = db.query(Institution).filter(
            Institution.id.in_(complaints.with_entities(Complaint.institution_id))
        ).distinct().count()
        bureaus_query = db.query(Bureau).filter(Bureau.is_active == True)
        officers_query = db.query(User).filter(User.role == UserRole.BUREAU_OFFICER, User.is_active == True)
        bureaus_query = bureaus_query.filter(Bureau.id == bureau_scope)
        officers_query = officers_query.filter(User.bureau_id == bureau_scope)
        total_bureaus = bureaus_query.count()
        total_officers = officers_query.count()

    overlap_query = db.query(OverlapResult)
    if bureau_scope is not None:
        overlap_query = overlap_query.filter(
            OverlapResult.primary_complaint.has(Complaint.bureau_id == bureau_scope),
            OverlapResult.candidate_complaint.has(Complaint.bureau_id == bureau_scope),
        )
    pending_overlaps = overlap_query.filter(OverlapResult.review_status == "pending").count()
    confirmed_duplicates = overlap_query.filter(OverlapResult.decision.isnot(None)).count()

    unassigned = complaints.filter(Complaint.assigned_officer_id.is_(None)).count()

    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=10)
    inactive = complaints.filter(
        Complaint.last_action_date < cutoff,
        Complaint.status.notin_(["disposed", "closed"])
    ).count()

    return {
        "total_complaints": total_complaints,
        "total_institutions": total_institutions,
        "total_bureaus": total_bureaus,
        "total_officers": total_officers,
        "pending_overlap_reviews": pending_overlaps,
        "confirmed_duplicate_relationships": confirmed_duplicates,
        "unassigned_complaints": unassigned,
        "inactive_complaints": inactive,
    }
