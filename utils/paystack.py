import httpx
from core.config import get_payment_config
from utils.logger import logger

payment_cfg = get_payment_config()


class PaystackClient:
    def __init__(self):
        self.secret_key = payment_cfg.paystack_secret_key
        self.base_url = "https://api.paystack.co"

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.secret_key or ''}",
            "Content-Type": "application/json",
        }

    async def initialize_transaction(
        self,
        email: str,
        amount: float,
        reference: str,
        callback_url: str | None = None,
        channels: list[str] | None = None,
        metadata: dict | None = None,
    ) -> dict:
        if not self.secret_key:
            return {"status": False, "message": "Paystack secret key not configured"}

        amount_kobo_pesewas = int(round(amount * 100))
        payload = {
            "email": email,
            "amount": amount_kobo_pesewas,
            "currency": "GHS",
            "reference": reference,
            "channels": channels or ["mobile_money", "card"],
            "metadata": metadata or {},
        }
        if callback_url:
            payload["callback_url"] = callback_url

        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                f"{self.base_url}/transaction/initialize",
                headers=self._get_headers(),
                json=payload,
            )
            return res.json()

    async def verify_transaction(self, reference: str) -> dict:
        if not self.secret_key:
            return {"status": False, "message": "Paystack secret key not configured"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.get(
                f"{self.base_url}/transaction/verify/{reference}",
                headers=self._get_headers(),
            )
            return res.json()


paystack_client = PaystackClient()
