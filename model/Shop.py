from beanie import Document, Indexed, before_event, Replace, Insert, SaveChanges
from datetime import datetime, timezone
from typing import Annotated


class Shop(Document):
    name: Annotated[str, Indexed(unique=True)]
    business_type: str = "retail"  # retail, supermarket, pharmacy, restaurant, fuel_station, wholesale, other
    currency: str = "GHS"
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    logo_url: str | None = None
    tax_rate: float = 0.0  # percentage, e.g. 0.0 or 15.0
    tax_name: str = "VAT/NHIL"
    is_tax_inclusive: bool = False
    allow_negative_stock: bool = False
    package_tier: str = "START-UP"  # START-UP, ELITE, ENTERPRISE
    status: str = "active"  # active | suspended | deleted
    status_reason: str | None = None
    status_changed_by: str | None = None
    status_changed_at: datetime | None = None
    onboarding_completed: bool = True
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

    @before_event([Replace, Insert, SaveChanges])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "shops"
