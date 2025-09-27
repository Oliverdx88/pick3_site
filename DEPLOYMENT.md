# 🚀 Production Deployment Checklist

## Pre-Deployment Setup

### 1. GitHub Repository
- [ ] Create GitHub repository: `pick3_site`
- [ ] Push code to GitHub
- [ ] Verify all files are uploaded

### 2. Stripe Setup
- [ ] Create 3 products in Stripe Dashboard:
  - Free Starter: $0/month
  - VIP Pro Monthly: $9.99/month  
  - VIP Pro Yearly: $99/year
- [ ] Copy all Price IDs
- [ ] Get TEST API keys (pk_test_... and sk_test_...)

### 3. Mailgun Setup
- [ ] Create Mailgun account
- [ ] Add domain: mg.unthinkabledeal.com
- [ ] Verify domain (SPF, DKIM, MX records)
- [ ] Get API key
- [ ] Test email sending

## Render Deployment

### 1. Create Web Service
- [ ] Go to render.com
- [ ] New + → Web Service
- [ ] Connect GitHub repository
- [ ] Use these settings:
  - **Build Command:** `pip install -r requirements.txt`
  - **Start Command:** `gunicorn wsgi:app --workers=2 --threads=4 --timeout=120`

### 2. Environment Variables
Set these in Render → Service → Settings → Environment:

```
SECRET_KEY = [long random string]
BASE_URL = https://your-service.onrender.com
STRIPE_SECRET_KEY = sk_test_...
STRIPE_PUBLISHABLE_KEY = pk_test_...
STRIPE_PRICE_ID_FREE = price_...
STRIPE_PRICE_ID_VIP_MONTHLY = price_...
STRIPE_PRICE_ID_VIP_YEARLY = price_...
STRIPE_PORTAL_RETURN_URL = https://your-service.onrender.com/account
MAILGUN_API_KEY = key-...
MAILGUN_DOMAIN = mg.unthinkabledeal.com
MAIL_FROM = Pick3 App <mail@mg.unthinkabledeal.com>
STRIPE_WEBHOOK_SECRET = [leave blank for now]
```

### 3. Deploy and Test
- [ ] Deploy service
- [ ] Visit /health endpoint (should return {"status":"ok"})
- [ ] Test homepage loads
- [ ] Test magic link login
- [ ] Test Stripe checkout (use test card: 4242 4242 4242 4242)

## Custom Domain Setup

### 1. Add Domain to Render
- [ ] Render → Service → Custom Domains
- [ ] Add: unthinkabledeal.com
- [ ] Add: www.unthinkabledeal.com

### 2. DNS Configuration
- [ ] At your domain registrar, add DNS records:
  - CNAME: www → your-service.onrender.com
  - ALIAS/ANAME: @ → your-service.onrender.com (or A record)
- [ ] Wait for SSL certificate (green lock)

### 3. Update Environment Variables
- [ ] Update BASE_URL to: https://unthinkabledeal.com
- [ ] Update STRIPE_PORTAL_RETURN_URL to: https://unthinkabledeal.com/account

## Stripe Webhooks

### 1. Create Webhook
- [ ] Stripe Dashboard → Developers → Webhooks
- [ ] Add endpoint: https://unthinkabledeal.com/webhook
- [ ] Select events:
  - checkout.session.completed
  - customer.subscription.created
  - customer.subscription.updated
  - customer.subscription.deleted
  - invoice.payment_succeeded
- [ ] Copy signing secret (whsec_...)

### 2. Update Render
- [ ] Add STRIPE_WEBHOOK_SECRET to Render environment variables
- [ ] Redeploy service
- [ ] Test webhook by completing a test purchase

## Go Live Checklist

- [ ] All tests pass on production
- [ ] Magic link emails work
- [ ] Stripe checkout works (test mode)
- [ ] Webhooks return 200 status
- [ ] Custom domain with SSL
- [ ] VIP paywall works
- [ ] Customer portal works

## Switch to Live Payments

When ready to accept real money:

### 1. Create Live Products
- [ ] Stripe → Toggle to Live mode
- [ ] Create live versions of all 3 products
- [ ] Copy live Price IDs

### 2. Update Environment Variables
- [ ] STRIPE_SECRET_KEY = sk_live_...
- [ ] STRIPE_PUBLISHABLE_KEY = pk_live_...
- [ ] Update all Price IDs to live versions

### 3. Create Live Webhook
- [ ] Create new webhook for live mode
- [ ] URL: https://unthinkabledeal.com/webhook
- [ ] Copy live signing secret
- [ ] Update STRIPE_WEBHOOK_SECRET

### 4. Test Live Payment
- [ ] Make small real purchase ($1-2)
- [ ] Verify webhook works
- [ ] Refund test purchase

## Post-Launch

- [ ] Monitor webhook logs
- [ ] Set up error tracking
- [ ] Add analytics (Google Analytics/Plausible)
- [ ] Plan Postgres migration for scale
- [ ] Set up monitoring and alerts



