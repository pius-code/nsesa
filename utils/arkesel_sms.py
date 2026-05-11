import httpx
from utils.gen_message_template import gen_template
import os
from dotenv import load_dotenv

load_dotenv()

ARKESEL_API_KEY = os.getenv("ARKESEL_API_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

ARKESEL_URL = "https://sms.arkesel.com/sms/api"


async def send_sms(phone_number: str, tracking_id: str, full_name: str):
    message = gen_template(full_name, tracking_id, "").strip()

    params = {
        "action": "send-sms",
        "api_key": ARKESEL_API_KEY,
        "from": "skyvote",
        "to": phone_number.strip(),
        "sms": message,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(ARKESEL_URL, params=params)
        print(response.text)


async def send_payment_reminder_sms(
    phone_number: str, full_name: str, tracking_id: str
):
    message = (
        f"Hi {full_name}, you're one step away from completing your "
        f"SkyVotes Careers application. Secure your spot now: "
        f"www.careers.skyvotes.org/track/{tracking_id}"
    )

    params = {
        "action": "send-sms",
        "api_key": ARKESEL_API_KEY,
        "from": "skyvote",
        "to": phone_number.strip(),
        "sms": message,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(ARKESEL_URL, params=params)
        print(response.text)


async def blast_payment_reminders_test():
    from repository.internship import get_unpaid_users_for_reminder

    test_numbers = ["233536287642", "233272806050"]
    users = await get_unpaid_users_for_reminder()
    for user in users:
        if user.phone_number.strip() in test_numbers:
            print(f"Found a number: {user.phone_number} — {user.Full_name}")
            await send_payment_reminder_sms(
                user.phone_number, user.Full_name, user.tracking_id
            )


async def blast_payment_reminders():
    from repository.internship import get_unpaid_users_for_reminder

    users = await get_unpaid_users_for_reminder()
    for user in users:
        await send_payment_reminder_sms(
            user.phone_number, user.Full_name, user.tracking_id
        )


async def send_assignment_sms(
    phone_number: str, full_name: str, company: str, tracking_id: str
):
    message = (
        f"Congratulations {full_name}! "
        f"You have been assigned to {company}. "
        f"kindly contact 0545290894 via WhatsApp for further instructions"
        f"Track your application status at: {FRONTEND_URL}/track/{tracking_id}"
    )

    params = {
        "action": "send-sms",
        "api_key": ARKESEL_API_KEY,
        "from": "skyvote",
        "to": phone_number.strip(),
        "sms": message,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(ARKESEL_URL, params=params)
        print(response.text)
