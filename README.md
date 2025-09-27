# Pick3 Predictions App

A Flask web application for Pick 3 lottery predictions with Stripe subscriptions and magic link authentication.

## Features

- 🟢 **Free Starter Plan** - $0/month (basic doubles predictions)
- 🔵 **VIP Pro Monthly** - $9.99/month (full features)
- 🟡 **VIP Pro Yearly** - $99/year (best value)
- 🔐 **Magic Link Authentication** - No passwords needed
- 💳 **Stripe Integration** - Secure payments and subscriptions
- 📧 **Mailgun Email** - Magic links and notifications
- 🛡️ **VIP Paywall** - Protected premium features

## Tech Stack

- **Backend:** Flask, Python 3.11+
- **Database:** SQLite (local) / PostgreSQL (production)
- **Payments:** Stripe
- **Email:** Mailgun
- **Authentication:** Magic links with itsdangerous
- **Deployment:** Render

## Local Development

```bash
# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Set environment variables
copy .env.example .env
# Edit .env with your keys

# Run locally
flask run --port 5012
```

## Environment Variables

See `.env.example` for required environment variables.

## Deployment

Deploy to Render with the environment variables configured in your Render dashboard.

## License

Private - All rights reserved.



