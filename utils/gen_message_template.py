def gen_template(full_name: str, tracking_id: str, message: str) -> str:
    template = f"""
Dear {full_name},
Your payment has been recieved and your application is currently being reviewed by our team.
Track your application status on
 careers.skyvotes.org/track/{tracking_id}.
Tracking ID: {tracking_id}
"""

    return template
