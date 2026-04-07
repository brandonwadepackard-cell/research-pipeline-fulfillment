"""
Autonomous Research Pipeline Blueprint — Stripe Fulfillment Webhook Server
Fires on checkout.session.completed, emails buyer the ZIP download link.
"""
import os
import json
import hmac
import hashlib
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import stripe

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# --- Config from env vars ---
STRIPE_SECRET_KEY     = os.environ["STRIPE_SECRET_KEY"]
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
SMTP_HOST             = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT             = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER             = os.environ["SMTP_USER"]
SMTP_PASSWORD         = os.environ["SMTP_PASSWORD"]
NOTIFY_EMAIL          = os.environ.get("NOTIFY_EMAIL", SMTP_USER)

stripe.api_key = STRIPE_SECRET_KEY

# --- Product fulfillment map ---
PRODUCT_FULFILLMENT = {
    "prod_UHyrywGEKgA1uG": {
        "name": "Autonomous Research Pipeline Blueprint",
        "price": "$299",
        "download_url": os.environ.get("RESEARCH_PIPELINE_DOWNLOAD_URL", "PENDING_UPLOAD"),
        "email_subject": "Your Autonomous Research Pipeline Blueprint — Download Inside",
        "email_body": """Hi {customer_name},

Thank you for purchasing the Autonomous Research Pipeline Blueprint!

Your download is ready:

  {download_url}

What's included in your ZIP:
  - agent_research_daemon.py  — The persistent background watcher
  - research_coordinator.py  — The orchestration + summarization engine
  - request_research.py      — CLI to inject new research tasks
  - start_research_daemon.sh — Deployment shell script
  - README.md                — Customer Quickstart (Supabase setup + API wiring)

Getting started:
  1. Unzip the file
  2. Follow README.md to set up your Supabase tables
  3. Add your Perplexity API key and Supabase credentials
  4. Run: bash start_research_daemon.sh

Questions? Reply to this email.

— Brandon Packard / MYTHOS Systems
"""
    }
}


def send_email(to_email: str, subject: str, body: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SMTP_USER
    msg["To"]      = to_email
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, to_email, msg.as_string())
    logger.info(f"Email sent to {to_email}")


def get_product_id_from_session(session) -> str | None:
    try:
        line_items = stripe.checkout.Session.list_line_items(session["id"], limit=1)
        if line_items.data:
            price_id = line_items.data[0].price.id
            price = stripe.Price.retrieve(price_id)
            return price.product
    except Exception as e:
        logger.error(f"Could not get product ID: {e}")
    return None


@app.get("/health")
def health():
    return {"status": "ok", "service": "research-pipeline-fulfillment"}


@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload    = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        event = json.loads(payload)

    if event["type"] != "checkout.session.completed":
        return JSONResponse({"received": True})

    session        = event["data"]["object"]
    customer_email = session.get("customer_details", {}).get("email", "")
    customer_name  = session.get("customer_details", {}).get("name", "Valued Customer") or "Valued Customer"
    amount_total   = session.get("amount_total", 0)

    product_id  = get_product_id_from_session(session)
    fulfillment = PRODUCT_FULFILLMENT.get(product_id) if product_id else None

    if not fulfillment:
        for pid, config in PRODUCT_FULFILLMENT.items():
            if amount_total == 29900:
                fulfillment = config
                break

    if not fulfillment:
        return JSONResponse({"received": True, "fulfilled": False})

    if customer_email:
        body = fulfillment["email_body"].format(
            customer_name=customer_name,
            download_url=fulfillment["download_url"]
        )
        send_email(customer_email, fulfillment["email_subject"], body)

    notify_body = f"""New sale!

Product:  {fulfillment['name']}
Price:    {fulfillment['price']}
Buyer:    {customer_name} <{customer_email}>
Session:  {session.get('id')}
"""
    send_email(NOTIFY_EMAIL, f"[SALE] {fulfillment['name']} — {fulfillment['price']}", notify_body)
    return JSONResponse({"received": True, "fulfilled": True})
