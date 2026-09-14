from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from model.Shop import Shop
from model.Branch import Branch
from model.Stakeholder import Stakeholder
from model.Subscription import Subscription
from schema.onboarding import MerchantOnboardingRequest, MerchantOnboardingResponse
from utils.hasher import hashPwd
from helpers.auth import generate_token
from repository.subscription import TIER_LIMITS

onboarding_router = APIRouter(prefix="/api/v1/onboarding", tags=["Merchant Onboarding"])


@onboarding_router.post("/register", response_model=MerchantOnboardingResponse)
async def onboard_merchant(payload: MerchantOnboardingRequest):
    # 1. Check if shop name already exists
    existing_shop = await Shop.find_one(Shop.name == payload.business_name.strip())
    if existing_shop:
        raise HTTPException(status_code=400, detail="A business with this name is already registered.")

    # 2. Check if email already registered
    existing_user = await Stakeholder.find_one(Stakeholder.worker_email == payload.email.strip().lower())
    if existing_user:
        raise HTTPException(status_code=400, detail="This email address is already registered.")

    # 3. Create Business (Shop)
    shop = Shop(
        name=payload.business_name.strip(),
        business_type=payload.business_type,
        currency="GHS",
        phone=payload.phone.strip(),
        email=payload.email.strip().lower(),
        address=payload.address,
        package_tier=payload.package_tier if payload.package_tier in TIER_LIMITS else "START-UP",
        tax_rate=payload.tax_rate,
        status="active",
        onboarding_completed=True,
        created_at=datetime.now(timezone.utc),
    )
    await shop.insert()

    # 4. Create Main Branch
    branch = Branch(
        business_id=shop.name,
        shop_name=shop.name,
        branch_name=payload.main_branch_name.strip() or "Main Branch",
        location=payload.address or "Main Location",
        phone=payload.phone.strip(),
        is_main=True,
        is_active=True,
        created_by=payload.owner_name.strip(),
        created_at=datetime.now(timezone.utc),
    )
    await branch.insert()

    # 5. Create Owner Stakeholder
    hashed = hashPwd(payload.password)
    owner = Stakeholder(
        worker_name=payload.owner_name.strip(),
        worker_shop_name=shop.name,
        worker_branch_name=branch.branch_name,
        worker_branch_id=str(branch.id),
        worker_role="owner",
        permissions=["ALL"],
        worker_email=payload.email.strip().lower(),
        worker_phone=payload.phone.strip(),
        worker_hashed_password=hashed,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    await owner.insert()

    # 6. Initialize Subscription Plan
    tier = payload.package_tier if payload.package_tier in TIER_LIMITS else "START-UP"
    limits = TIER_LIMITS[tier]
    subscription = Subscription(
        shop_name=shop.name,
        package_tier=tier,
        status="ACTIVE",
        **limits,
        created_at=datetime.now(timezone.utc),
    )
    await subscription.insert()

    # 7. Generate Auth Token
    token = generate_token(str(owner.id))

    return MerchantOnboardingResponse(
        message="Merchant onboarding completed successfully. Welcome to FJ Pay!",
        business_name=shop.name,
        token=token,
        owner_id=str(owner.id),
        branch_id=str(branch.id),
    )
