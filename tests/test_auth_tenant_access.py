from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from middleware.auth import ensure_same_shop, normalize_role


def test_matching_shop_is_allowed():
    stakeholder = SimpleNamespace(worker_shop_name="Apex Traders")

    ensure_same_shop(stakeholder, "Apex Traders")


def test_cross_shop_access_is_rejected():
    stakeholder = SimpleNamespace(worker_shop_name="Apex Traders")

    with pytest.raises(HTTPException, match="tenant"):
        ensure_same_shop(stakeholder, "Midnight Stores")


def test_role_aliases_are_normalized():
    assert normalize_role("admin") == "owner"
    assert normalize_role("inventory_manager") == "manager"
    assert normalize_role("cashier") == "cashier"
