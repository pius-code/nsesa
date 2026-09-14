from beanie import Document, Indexed, before_event, Replace, Insert, SaveChanges
from datetime import datetime, timezone
from typing import Annotated, Literal

PackageTier = Literal["START-UP", "ELITE", "ENTERPRISE"]
SubscriptionStatus = Literal["ACTIVE", "TRIAL", "PAST_DUE", "EXPIRED", "CANCELLED"]


class Subscription(Document):
    shop_name: Annotated[str, Indexed(unique=True)]
    package_tier: Annotated[PackageTier, Indexed()] = "START-UP"
    status: Annotated[SubscriptionStatus, Indexed()] = "ACTIVE"
    max_branches: int = 1
    max_users: int = 3
    max_products: int = 500
    allow_advanced_reports: bool = False
    allow_custom_branding: bool = False
    allow_bulk_import: bool = True
    allow_api_access: bool = False
    starts_at: datetime = datetime.now(timezone.utc)
    expires_at: datetime | None = None
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)

    @before_event([Replace, Insert, SaveChanges])
    def update_timestamp(self):
        self.updated_at = datetime.now(timezone.utc)

    class Settings:
        name = "subscriptions"
