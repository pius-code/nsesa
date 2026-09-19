# import httpx
# from utils.gen_message_template import gen_template
#
#
# async def send_sms(phone_number: str, tracking_id: str, full_name: str):
#     full_name = full_name.strip()
#     tracking_id = tracking_id.strip()
#
#     message = gen_template(full_name, tracking_id, "").strip()
#
#     url = "https://smsc.hubtel.com/v1/messages/send"
#     params = {
#         "clientsecret": "ufoudpug",
#         "clientid": "pvztmqbv",
#         "from": "233536287642",
#         "to": phone_number.strip(),
#         "content": message,
#     }
#
#     async with httpx.AsyncClient() as client:
#         response = await client.get(url, params=params)
#         print(response.text)
