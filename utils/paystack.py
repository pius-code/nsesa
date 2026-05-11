import secrets
import httpx
from core.paystack import headers
from repository.internship import get_internship_data_by_tracking_id
from dotenv import load_dotenv
import os

load_dotenv()


frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")


async def generate_paystack_link_for_voting(
    tracking_id: str,
    amount: float,
):  # noqa
    normalized_amount = int(round(amount * 100))
    random_suffix = secrets.token_hex(4)[:7].upper()
    reference = f"internship-{tracking_id}_{random_suffix}"
    data = await get_internship_data_by_tracking_id(tracking_id)

    if data == "Not found":
        raise ValueError(
            f"Internship application with tracking ID {tracking_id} not found"
        )

    async with httpx.AsyncClient() as client:
        body = {
            "reference": reference,
            "amount": normalized_amount,
            "email": f"career_skyvotes{data.tracking_id}@gmail.com",
            "callback_url": f"{frontend_url}/track/{tracking_id}",
            "channels": ["mobile_money"],
            "metadata": {
                "tracking_id": tracking_id,
                "full_name": data.Full_name,
                "phone_number": data.phone_number,
            },
        }
        response = await client.post(
            "https://api.paystack.co/transaction/initialize/",
            headers=headers,
            json=body,
        )
    return response.json(), reference
