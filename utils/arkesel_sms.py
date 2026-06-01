import httpx
from utils.gen_message_template import gen_transaction_receipt
import os
from dotenv import load_dotenv

load_dotenv()

ARKESEL_API_KEY = os.getenv("ARKESEL_API_KEY")
ARKESEL_URL = "https://sms.arkesel.com/sms/api"
SMS_SENDER_ID = os.getenv("SMS_SENDER_ID", "Nsesa")


async def send_transaction_receipt_sms(
    phone_number: str,
    customer_name: str,
    transaction_id: str,
    shop_name: str,
    total_price: float,
    items: list,
    receipt_url: str,
    payment_mode: str | None = None,
):
    message = gen_transaction_receipt(
        customer_name=customer_name,
        transaction_id=transaction_id,
        shop_name=shop_name,
        total_price=total_price,
        items=items,
        receipt_url=receipt_url,
        payment_mode=payment_mode,
    )

    params = {
        "action": "send-sms",
        "api_key": ARKESEL_API_KEY,
        "from": SMS_SENDER_ID,
        "to": phone_number.strip(),
        "sms": message,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(ARKESEL_URL, params=params)
        print(f"[SMS] {phone_number} — {response.text}")
