import httpx
from core.config import get_sms_config
from utils.logger import logger

sms_cfg = get_sms_config()


async def send_sms_via_hubtel(phone_number: str, message: str) -> bool:
    if not sms_cfg.hubtel_client_id or not sms_cfg.hubtel_client_secret:
        logger.warning("Hubtel SMS credentials not configured")
        return False

    url = "https://smsc.hubtel.com/v1/messages/send"
    params = {
        "clientsecret": sms_cfg.hubtel_client_secret,
        "clientid": sms_cfg.hubtel_client_id,
        "from": sms_cfg.hubtel_sender_id,
        "to": phone_number.strip(),
        "content": message.strip(),
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            return response.status_code == 200 or response.status_code == 201
    except Exception as e:
        logger.error(f"Failed to send SMS via Hubtel: {e}")
        return False
