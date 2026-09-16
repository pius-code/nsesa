from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from middleware.auth import ensure_branch_access


def test_matching_branch_is_allowed():
    stakeholder = SimpleNamespace(worker_branch_id="branch-123")

    ensure_branch_access(stakeholder, "branch-123")


def test_cross_branch_access_is_rejected():
    stakeholder = SimpleNamespace(worker_branch_id="branch-123")

    with pytest.raises(HTTPException, match="branch"):
        ensure_branch_access(stakeholder, "branch-999")


def test_unassigned_branch_is_not_blocked():
    stakeholder = SimpleNamespace(worker_branch_id=None)

    ensure_branch_access(stakeholder, "branch-123")
