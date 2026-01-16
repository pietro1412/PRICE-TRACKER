"""Alert routes for CRUD operations."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user
from src.core.database import get_db
from src.models import Alert, AlertStatus, Tour, User
from src.schemas import (
    AlertCreate,
    AlertListResponse,
    AlertResponse,
    AlertUpdate,
    AlertWithTourResponse,
)

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: AlertStatus | None = None,
) -> AlertListResponse:
    """List all alerts for the current user."""
    query = select(Alert).where(Alert.user_id == current_user.id)

    if status_filter:
        query = query.where(Alert.status == status_filter)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Alert.created_at.desc())

    result = await db.execute(query)
    alerts = result.scalars().all()

    return AlertListResponse(
        items=[AlertResponse.model_validate(a) for a in alerts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/with-tours", response_model=list[AlertWithTourResponse])
async def list_alerts_with_tours(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: AlertStatus | None = None,
) -> list[AlertWithTourResponse]:
    """List all alerts with tour information."""
    query = (
        select(Alert, Tour)
        .join(Tour, Alert.tour_id == Tour.id)
        .where(Alert.user_id == current_user.id)
    )

    if status_filter:
        query = query.where(Alert.status == status_filter)

    query = query.order_by(Alert.created_at.desc())

    result = await db.execute(query)
    rows = result.all()

    return [
        AlertWithTourResponse(
            id=alert.id,
            user_id=alert.user_id,
            tour_id=alert.tour_id,
            alert_type=alert.alert_type,
            threshold_price=alert.threshold_price,
            threshold_percentage=alert.threshold_percentage,
            status=alert.status,
            last_triggered_at=alert.last_triggered_at,
            trigger_count=alert.trigger_count,
            created_at=alert.created_at,
            updated_at=alert.updated_at,
            tour_name=tour.name,
            tour_current_price=tour.current_price,
            tour_destination=tour.destination,
        )
        for alert, tour in rows
    ]


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Alert:
    """Get a specific alert."""
    result = await db.execute(
        select(Alert)
        .where(Alert.id == alert_id)
        .where(Alert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    return alert


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: AlertCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Alert:
    """Create a new price alert."""
    # Verify tour exists
    tour_result = await db.execute(select(Tour).where(Tour.id == alert_data.tour_id))
    if not tour_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tour not found",
        )

    # Check if user already has an alert for this tour with same type
    existing = await db.execute(
        select(Alert)
        .where(Alert.user_id == current_user.id)
        .where(Alert.tour_id == alert_data.tour_id)
        .where(Alert.alert_type == alert_data.alert_type)
        .where(Alert.status == AlertStatus.ACTIVE)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active alert of this type for this tour",
        )

    alert = Alert(
        user_id=current_user.id,
        tour_id=alert_data.tour_id,
        alert_type=alert_data.alert_type,
        threshold_price=alert_data.threshold_price,
        threshold_percentage=alert_data.threshold_percentage,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)

    return alert


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    alert_data: AlertUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Alert:
    """Update an alert."""
    result = await db.execute(
        select(Alert)
        .where(Alert.id == alert_id)
        .where(Alert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    update_data = alert_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)

    await db.commit()
    await db.refresh(alert)

    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete an alert."""
    result = await db.execute(
        select(Alert)
        .where(Alert.id == alert_id)
        .where(Alert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    await db.delete(alert)
    await db.commit()


@router.post("/{alert_id}/pause", response_model=AlertResponse)
async def pause_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Alert:
    """Pause an alert."""
    result = await db.execute(
        select(Alert)
        .where(Alert.id == alert_id)
        .where(Alert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    alert.status = AlertStatus.PAUSED
    await db.commit()
    await db.refresh(alert)

    return alert


@router.post("/{alert_id}/resume", response_model=AlertResponse)
async def resume_alert(
    alert_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Alert:
    """Resume a paused alert."""
    result = await db.execute(
        select(Alert)
        .where(Alert.id == alert_id)
        .where(Alert.user_id == current_user.id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found",
        )

    if alert.status != AlertStatus.PAUSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Alert is not paused",
        )

    alert.status = AlertStatus.ACTIVE
    await db.commit()
    await db.refresh(alert)

    return alert
