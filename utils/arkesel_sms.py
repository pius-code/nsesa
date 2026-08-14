import httpx
import asyncio
from utils.gen_message_template import gen_transaction_receipt, gen_refund_notice # noqa
import os
from dotenv import load_dotenv

load_dotenv()

ARKESEL_API_KEY = os.getenv("ARKESEL_API_KEY")
ARKESEL_URL = "https://sms.arkesel.com/sms/api"
SMS_SENDER_ID = os.getenv("SMS_SENDER_ID", "Nsesa")


DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


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

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(ARKESEL_URL, params=params)
            print(f"[SMS] {phone_number} — {response.text}")
            return response
    except Exception as e:
        print(f"[SMS Error] Failed to send receipt SMS to {phone_number}: {e}")
        return None


async def send_refund_notice_sms(
    phone_number: str,
    customer_name: str,
    transaction_id: str,
    shop_name: str,
    total_price: float,
    receipt_url: str,
):
    message = gen_refund_notice(
        customer_name=customer_name,
        transaction_id=transaction_id,
        shop_name=shop_name,
        total_price=total_price,
        receipt_url=receipt_url,
    )

    params = {
        "action": "send-sms",
        "api_key": ARKESEL_API_KEY,
        "from": SMS_SENDER_ID,
        "to": phone_number.strip(),
        "sms": message,
    }

    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(ARKESEL_URL, params=params)
            print(f"[SMS] refund notice {phone_number} — {response.text}")
            return response
    except Exception as e:
        print(f"[SMS Error] Failed to send refund notice SMS to {phone_number}: {e}") # noqa
        return None


async def _send_raw_sms(phone_number: str, message: str):
    params = {
        "action": "send-sms",
        "api_key": ARKESEL_API_KEY,
        "from": SMS_SENDER_ID,
        "to": phone_number.strip(),
        "sms": message,
    }
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            response = await client.get(ARKESEL_URL, params=params)
            print(f"[SMS] broadcast {phone_number} — {response.text}")
            return response
    except Exception as e:
        print(f"[SMS Error] Failed to send broadcast SMS to {phone_number}: {e}") # noqa
        return None


async def send_broadcast_sms(phone_numbers: list[str], message: str):
    # Runs as a background task — fires all sends concurrently so a large
    # customer list doesn't hold up the request or take minutes to work through. # noqa
    await asyncio.gather(
        *(_send_raw_sms(number, message) for number in phone_numbers),
        return_exceptions=True,
    )

