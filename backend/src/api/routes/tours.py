"""Tour routes for CRUD operations and search."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models import Tour
from src.schemas import TourCreate, TourListResponse, TourResponse, TourUpdate

router = APIRouter(prefix="/tours", tags=["Tours"])


@router.get("", response_model=TourListResponse)
async def list_tours(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    destination: str | None = None,
    category: str | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    search: str | None = None,
    is_active: bool = True,
) -> TourListResponse:
    """List tours with filtering and pagination."""
    query = select(Tour).where(Tour.is_active == is_active)

    # Apply filters
    if destination:
        query = query.where(Tour.destination.ilike(f"%{destination}%"))
    if category:
        query = query.where(Tour.category.ilike(f"%{category}%"))
    if min_price is not None:
        query = query.where(Tour.current_price >= min_price)
    if max_price is not None:
        query = query.where(Tour.current_price <= max_price)
    if search:
        query = query.where(
            or_(
                Tour.name.ilike(f"%{search}%"),
                Tour.destination.ilike(f"%{search}%"),
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Tour.last_scraped_at.desc())

    result = await db.execute(query)
    tours = result.scalars().all()

    return TourListResponse(
        items=[TourResponse.model_validate(t) for t in tours],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/destinations", response_model=list[str])
async def list_destinations(
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """Get list of unique destinations."""
    query = (
        select(Tour.destination)
        .where(Tour.destination.isnot(None))
        .where(Tour.is_active == True)  # noqa: E712
        .distinct()
        .order_by(Tour.destination)
    )
    result = await db.execute(query)
    return [r[0] for r in result.all()]


@router.get("/categories", response_model=list[str])
async def list_categories(
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    """Get list of unique categories."""
    query = (
        select(Tour.category)
        .where(Tour.category.isnot(None))
        .where(Tour.is_active == True)  # noqa: E712
        .distinct()
        .order_by(Tour.category)
    )
    result = await db.execute(query)
    return [r[0] for r in result.all()]


@router.get("/{tour_id}", response_model=TourResponse)
async def get_tour(
    tour_id: int,
    db: AsyncSession = Depends(get_db),
) -> Tour:
    """Get a specific tour by ID."""
    result = await db.execute(select(Tour).where(Tour.id == tour_id))
    tour = result.scalar_one_or_none()

    if not tour:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tour not found",
        )

    return tour


@router.post("", response_model=TourResponse, status_code=status.HTTP_201_CREATED)
async def create_tour(
    tour_data: TourCreate,
    db: AsyncSession = Depends(get_db),
) -> Tour:
    """Create a new tour (usually called by scraper)."""
    # Check if civitatis_id already exists
    result = await db.execute(
        select(Tour).where(Tour.civitatis_id == tour_data.civitatis_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tour with civitatis_id {tour_data.civitatis_id} already exists",
        )

    tour = Tour(
        civitatis_id=tour_data.civitatis_id,
        name=tour_data.name,
        current_price=tour_data.current_price,
        currency=tour_data.currency,
        url=tour_data.url,
        destination=tour_data.destination,
        destination_id=tour_data.destination_id,
        category=tour_data.category,
        rating=tour_data.rating,
        min_price=tour_data.current_price,
        max_price=tour_data.current_price,
        avg_price=tour_data.current_price,
    )
    db.add(tour)
    await db.commit()
    await db.refresh(tour)

    return tour


@router.patch("/{tour_id}", response_model=TourResponse)
async def update_tour(
    tour_id: int,
    tour_data: TourUpdate,
    db: AsyncSession = Depends(get_db),
) -> Tour:
    """Update a tour."""
    result = await db.execute(select(Tour).where(Tour.id == tour_id))
    tour = result.scalar_one_or_none()

    if not tour:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tour not found",
        )

    update_data = tour_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tour, field, value)

    await db.commit()
    await db.refresh(tour)

    return tour


@router.delete("/{tour_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tour(
    tour_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a tour (soft delete by setting is_active=False)."""
    result = await db.execute(select(Tour).where(Tour.id == tour_id))
    tour = result.scalar_one_or_none()

    if not tour:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tour not found",
        )

    tour.is_active = False
    await db.commit()
