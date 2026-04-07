# Research Pipeline Fulfillment Server

Stripe webhook server. Fires on `checkout.session.completed` for `prod_UHyrywGEKgA1uG` ($299) and emails the buyer the ZIP download link instantly.

## Deploy to Railway

1. Push this folder to a private GitHub repo
2. Go to [railway.com/new](https://railway.com/new) → Deploy from GitHub → select this repo
3. Go to service → Variables → Raw Editor → paste the env vars below
4. Click Deploy
5. Copy the Railway domain (e.g. `https://xxx.up.railway.app`)
6. Register the Stripe webhook (see below)

## Required Environment Variables

```
STRIPE_SECRET_KEY=sk_live_51T9WVeDKA1ux1Mgu...
STRIPE_WEBHOOK_SECRET=whsec_...  (set after webhook registration)
SMTP_USER=brandonwadepackard@gmail.com
SMTP_PASSWORD=jrtcwraasgvqxhss
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
NOTIFY_EMAIL=brandonwadepackard@gmail.com
RESEARCH_PIPELINE_DOWNLOAD_URL=https://s3.amazonaws.com/...  (set after ZIP upload)
```

## Register Stripe Webhook

After Railway deploys:

```bash
curl -X POST https://api.stripe.com/v1/webhook_endpoints \
  -u sk_live_51T9WVeDKA1ux1Mgu...: \
  -d "url=https://YOUR-RAILWAY-DOMAIN.up.railway.app/webhook" \
  -d "enabled_events[]=checkout.session.completed" \
  -d "description=Research Pipeline Blueprint fulfillment"
```

Copy the `secret` field (`whsec_...`) → add to Railway env vars as `STRIPE_WEBHOOK_SECRET` → redeploy.

## Health Check

```
GET /health → {"status": "ok", "service": "research-pipeline-fulfillment"}
```

## Update Download URL

Once ZIP is uploaded to S3:
1. Update `RESEARCH_PIPELINE_DOWNLOAD_URL` in Railway env vars
2. Redeploy (takes ~30 seconds)
