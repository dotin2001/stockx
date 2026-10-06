from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentAdminUser, CurrentSupremeAdminUser, DbSession
from app.schemas.admin_user import AdminUserPage, AdminUserPromoteByEmail, AdminUserRead
from app.schemas.customer_message import CustomerMessagePage, CustomerMessageRead
from app.schemas.listing import (
    AdminListingCreate,
    ListingInventoryUpdate,
    ListingManagementRead,
    ListingPage,
    ListingQuantityAdjustment,
    ListingStatusUpdate,
)
from app.schemas.product import (
    AdminProductPage,
    AdminProductRead,
    ProductCreate,
    ProductUpdate,
    ProductVariantCreate,
    ProductVariantRead,
    ProductVariantUpdate,
)
from app.services import admin_products
from app.services import admin_users
from app.services import customer_messages
from app.services import listings as listing_service

router = APIRouter()


@router.get("/users", response_model=AdminUserPage)
def list_users(
    db: DbSession,
    _admin: CurrentSupremeAdminUser,
    search: str | None = Query(default=None, min_length=1, max_length=320),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AdminUserPage:
    users, total = admin_users.list_users(db, search=search, limit=limit, offset=offset)
    return AdminUserPage(
        items=[AdminUserRead.model_validate(user) for user in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/users/promote", response_model=AdminUserRead)
def promote_user_by_email(
    payload: AdminUserPromoteByEmail,
    db: DbSession,
    _admin: CurrentSupremeAdminUser,
) -> AdminUserRead:
    user = admin_users.promote_user_by_email(db, email=payload.email)
    db.commit()
    return AdminUserRead.model_validate(user)


@router.post("/users/{user_id}/promote", response_model=AdminUserRead)
def promote_user_by_id(user_id: UUID, db: DbSession, _admin: CurrentSupremeAdminUser) -> AdminUserRead:
    user = admin_users.promote_user_by_id(db, user_id=user_id)
    db.commit()
    return AdminUserRead.model_validate(user)


@router.post("/users/{user_id}/demote", response_model=AdminUserRead)
def demote_user(user_id: UUID, db: DbSession, admin: CurrentSupremeAdminUser) -> AdminUserRead:
    user = admin_users.demote_user(db, user_id=user_id, actor=admin)
    db.commit()
    return AdminUserRead.model_validate(user)


@router.get("/messages", response_model=CustomerMessagePage)
def list_customer_messages(
    db: DbSession,
    _admin: CurrentAdminUser,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> CustomerMessagePage:
    messages, total = customer_messages.list_admin_messages(db, limit=limit, offset=offset)
    return CustomerMessagePage(
        items=[customer_messages.serialize_message(message) for message in messages],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/messages/{message_id}", response_model=CustomerMessageRead)
def get_customer_message(message_id: UUID, db: DbSession, _admin: CurrentAdminUser) -> CustomerMessageRead:
    message = customer_messages.get_admin_message(db, message_id=message_id)
    return customer_messages.serialize_message(message)


@router.post("/messages/{message_id}/read", response_model=CustomerMessageRead)
def mark_customer_message_read(message_id: UUID, db: DbSession, _admin: CurrentAdminUser) -> CustomerMessageRead:
    message = customer_messages.mark_admin_message_read(db, message_id=message_id)
    db.commit()
    return customer_messages.serialize_message(message)


@router.get("/listings", response_model=ListingPage)
def list_listings(
    db: DbSession,
    _admin: CurrentAdminUser,
    status_filter: str | None = Query(default=None, alias="status", pattern="^(active|sold|cancelled)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ListingPage:
    listings, total = listing_service.list_managed_listings(db, status_filter=status_filter, limit=limit, offset=offset)
    return ListingPage(
        items=[ListingManagementRead.model_validate(listing) for listing in listings],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/listings/{listing_id}/cancel", response_model=ListingManagementRead)
def cancel_listing(listing_id: UUID, db: DbSession, _admin: CurrentAdminUser) -> ListingManagementRead:
    listing = listing_service.cancel_managed_listing(db, listing_id=listing_id)
    db.commit()
    return ListingManagementRead.model_validate(listing)


@router.get("/products", response_model=AdminProductPage)
def list_products(
    db: DbSession,
    _admin: CurrentAdminUser,
    archived: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AdminProductPage:
    products, total = admin_products.list_managed_products(db, archived=archived, limit=limit, offset=offset)
    return AdminProductPage(
        items=[admin_products.serialize_admin_product(product) for product in products],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/products", response_model=AdminProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: DbSession, _admin: CurrentAdminUser) -> AdminProductRead:
    product = admin_products.create_product(db, payload)
    db.commit()
    return admin_products.serialize_admin_product(product)


@router.patch("/products/{product_id}", response_model=AdminProductRead)
def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    db: DbSession,
    _admin: CurrentAdminUser,
) -> AdminProductRead:
    product = admin_products.update_product(db, product_id=product_id, payload=payload)
    db.commit()
    return admin_products.serialize_admin_product(product)


@router.post("/products/{product_id}/archive", response_model=AdminProductRead)
def archive_product(product_id: UUID, db: DbSession, admin: CurrentAdminUser) -> AdminProductRead:
    product = admin_products.archive_product(db, product_id=product_id, admin=admin)
    db.commit()
    return admin_products.serialize_admin_product(product)


@router.post("/products/{product_id}/restore", response_model=AdminProductRead)
def restore_product(product_id: UUID, db: DbSession, _admin: CurrentAdminUser) -> AdminProductRead:
    product = admin_products.restore_product(db, product_id=product_id)
    db.commit()
    return admin_products.serialize_admin_product(product)


@router.post("/products/{product_id}/listings", response_model=ListingManagementRead, status_code=status.HTTP_201_CREATED)
def create_product_listing(
    product_id: UUID,
    payload: AdminListingCreate,
    db: DbSession,
    admin: CurrentSupremeAdminUser,
) -> ListingManagementRead:
    listing = listing_service.create_managed_listing(
        db,
        actor=admin,
        product_id=product_id,
        product_variant_id=payload.product_variant_id,
        price_cents=payload.price_cents,
        currency=payload.currency,
        available_quantity=payload.available_quantity,
        listing_status=payload.status,
    )
    db.commit()
    return ListingManagementRead.model_validate(listing)


@router.post("/listings/{listing_id}/inventory/quantity", response_model=ListingManagementRead)
def adjust_listing_inventory_quantity(
    listing_id: UUID,
    payload: ListingQuantityAdjustment,
    db: DbSession,
    admin: CurrentSupremeAdminUser,
) -> ListingManagementRead:
    listing = listing_service.adjust_managed_listing_quantity(
        db,
        listing_id=listing_id,
        adjustment=payload.adjustment,
        actor=admin,
    )
    db.commit()
    return ListingManagementRead.model_validate(listing)


@router.patch("/listings/{listing_id}/inventory/status", response_model=ListingManagementRead)
def update_listing_inventory_status(
    listing_id: UUID,
    payload: ListingStatusUpdate,
    db: DbSession,
    admin: CurrentSupremeAdminUser,
) -> ListingManagementRead:
    listing = listing_service.change_managed_listing_status(
        db,
        listing_id=listing_id,
        next_status=payload.status,
        actor=admin,
    )
    db.commit()
    return ListingManagementRead.model_validate(listing)


@router.patch("/listings/{listing_id}/inventory", response_model=ListingManagementRead)
def update_listing_inventory(
    listing_id: UUID,
    payload: ListingInventoryUpdate,
    db: DbSession,
    admin: CurrentSupremeAdminUser,
) -> ListingManagementRead:
    listing = listing_service.update_managed_listing_inventory(
        db,
        listing_id=listing_id,
        product_variant_id=payload.product_variant_id,
        price_cents=payload.price_cents,
        currency=payload.currency,
        available_quantity=payload.available_quantity,
        next_status=payload.status,
        actor=admin,
    )
    db.commit()
    return ListingManagementRead.model_validate(listing)


@router.post("/products/{product_id}/variants", response_model=ProductVariantRead, status_code=status.HTTP_201_CREATED)
def create_variant(
    product_id: UUID,
    payload: ProductVariantCreate,
    db: DbSession,
    _admin: CurrentAdminUser,
) -> ProductVariantRead:
    variant = admin_products.create_variant(db, product_id=product_id, payload=payload)
    db.commit()
    return ProductVariantRead.model_validate(variant)


@router.patch("/product-variants/{variant_id}", response_model=ProductVariantRead)
def update_variant(
    variant_id: UUID,
    payload: ProductVariantUpdate,
    db: DbSession,
    _admin: CurrentAdminUser,
) -> ProductVariantRead:
    variant = admin_products.update_variant(db, variant_id=variant_id, payload=payload)
    db.commit()
    return ProductVariantRead.model_validate(variant)


@router.delete("/product-variants/{variant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_variant(variant_id: UUID, db: DbSession, _admin: CurrentAdminUser) -> None:
    admin_products.delete_variant(db, variant_id=variant_id)
    db.commit()
    return None
