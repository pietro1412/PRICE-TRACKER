"""Price history routes."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models import PriceHistory, Tour
from src.schemas import PriceHistoryListResponse, PriceHistoryResponse, PriceStatsResponse

router = APIRouter(prefix="/tours/{tour_id}/prices", tags=["Price History"])


@router.get("", response_model=PriceHistoryListResponse)
async def list_price_history(
    tour_id: int,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    days: int | None = Query(None, ge=1, le=365),
) -> PriceHistoryListResponse:
    """Get price history for a tour."""
    # Verify tour exists
    tour_result = await db.execute(select(Tour).where(Tour.id == tour_id))
    if not tour_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tour not found",
        )

    query = select(PriceHistory).where(PriceHistory.tour_id == tour_id)

    # Filter by date range if specified
    if days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        query = query.where(PriceHistory.recorded_at >= cutoff)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(PriceHistory.recorded_at.desc())

    result = await db.execute(query)
    history = result.scalars().all()

    return PriceHistoryListResponse(
        items=[PriceHistoryResponse.model_validate(h) for h in history],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=PriceStatsResponse)
async def get_price_stats(
    tour_id: int,
    db: AsyncSession = Depends(get_db),
) -> PriceStatsResponse:
    """Get price statistics for a tour."""
    # Get tour
    tour_result = await db.execute(select(Tour).where(Tour.id == tour_id))
    tour = tour_result.scalar_one_or_none()

    if not tour:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tour not found",
        )

    # Get total records
    count_query = select(func.count()).where(PriceHistory.tour_id == tour_id)
    count_result = await db.execute(count_query)
    total_records = count_result.scalar() or 0

    # Calculate price changes
    now = datetime.now(timezone.utc)

    async def get_price_change(days: int):
        cutoff = now - timedelta(days=days)
        query = (
            select(PriceHistory.price)
            .where(PriceHistory.tour_id == tour_id)
            .where(PriceHistory.recorded_at >= cutoff)
            .order_by(PriceHistory.recorded_at.asc())
            .limit(1)
        )
        result = await db.execute(query)
        old_price = result.scalar_one_or_none()
        if old_price and tour.current_price:
            return tour.current_price - old_price
        return None

    price_change_24h = await get_price_change(1)
    price_change_7d = await get_price_change(7)
    price_change_30d = await get_price_change(30)

    return PriceStatsResponse(
        tour_id=tour_id,
        current_price=tour.current_price,
        min_price=tour.min_price,
        max_price=tour.max_price,
        avg_price=tour.avg_price,
        price_change_24h=price_change_24h,
        price_change_7d=price_change_7d,
        price_change_30d=price_change_30d,
        total_records=total_records,
    )


@router.get("/latest", response_model=PriceHistoryResponse)
async def get_latest_price(
    tour_id: int,
    db: AsyncSession = Depends(get_db),
) -> PriceHistory:
    """Get the latest price record for a tour."""
    query = (
        select(PriceHistory)
        .where(PriceHistory.tour_id == tour_id)
        .order_by(PriceHistory.recorded_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    price = result.scalar_one_or_none()

    if not price:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No price history found for this tour",
        )

    return price
