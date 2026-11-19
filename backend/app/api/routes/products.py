from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.product import ProductCreate, ProductPage, ProductRead, ProductUpdate
from app.services import products as product_service


router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductPage)
def get_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    search: str | None = None,
    category: str | None = None,
    include_inactive: bool = False,
    session: Session = Depends(get_db),
):
    rows, total = product_service.list_products(
        session,
        skip=skip,
        limit=limit,
        search=search,
        category=category,
        include_inactive=include_inactive,
    )
    return ProductPage(items=rows, skip=skip, limit=limit, total=total)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def post_product(data: ProductCreate, session: Session = Depends(get_db)):
    return product_service.create_product(session, data)


@router.get("/lookup/{sku}", response_model=ProductRead)
def lookup_product_by_sku(sku: str, session: Session = Depends(get_db)):
    return product_service.get_product_by_sku(session, sku)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: int, session: Session = Depends(get_db)):
    return product_service.get_product(session, product_id)


@router.patch("/{product_id}", response_model=ProductRead)
def patch_product(product_id: int, data: ProductUpdate, session: Session = Depends(get_db)):
    return product_service.update_product(session, product_id, data)


@router.delete("/{product_id}", response_model=ProductRead)
def delete_product(product_id: int, response: Response, session: Session = Depends(get_db)):
    response.status_code = status.HTTP_200_OK
    return product_service.deactivate_product(session, product_id)
