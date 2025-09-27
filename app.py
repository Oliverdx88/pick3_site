import os
import time
import stripe
import requests
from flask import Flask, jsonify, request, render_template, redirect, session, abort, url_for
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from config import Settings
from db import init_db, upsert_user, get_user

def create_app():
    app = Flask(__name__)
    app.config.from_object(Settings)
    app.secret_key = app.config["SECRET_KEY"]

    init_db()  # ensure SQLite table exists
    stripe.api_key = app.config["STRIPE_SECRET_KEY"]
    
    # Magic link authentication
    signer = URLSafeTimedSerializer(app.secret_key)
    MAGIC_LINK_TTL = 15 * 60  # 15 minutes

    # ---------- helpers ----------
    def is_vip(email):
        u = get_user(email)
        if not u:
            return False
        if u["status"] not in ("active", "trialing"):
            return False
        return u["plan"] in ("vip_monthly", "vip_yearly")

    def require_login():
        if "user_email" not in session:
            # send them to home or a sign-in page (Phase 2 can add magic-link login)
            return redirect(url_for("index"))
        return None

    def require_vip(f):
        # decorator to guard VIP features
        from functools import wraps
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user_email" not in session:
                return redirect(url_for("index"))
            if not is_vip(session["user_email"]):
                return abort(402)  # Payment Required (or redirect to pricing)
            return f(*args, **kwargs)
        return wrapper

    # ---------- routes ----------
    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/")
    def index():
        email = session.get("user_email")
        user = get_user(email) if email else None
        return render_template(
            "index.html",
            publishable_key=app.config["STRIPE_PUBLISHABLE_KEY"],
            user=user
        )

    # Choose plan: free | vip_monthly | vip_yearly
    @app.post("/create-checkout-session/<plan>")
    def create_checkout_session(plan):
        price_map = {
            "free": app.config.get("STRIPE_PRICE_ID_FREE"),
            "vip_monthly": app.config.get("STRIPE_PRICE_ID_VIP_MONTHLY"),
            "vip_yearly": app.config.get("STRIPE_PRICE_ID_VIP_YEARLY"),
        }
        price_id = price_map.get(plan)
        if not price_id:
            return jsonify({"error": "Invalid plan"}), 400

        try:
            session_obj = stripe.checkout.Session.create(
                mode="subscription",
                payment_method_types=["card"] if plan != "free" else ["card"],  # card still okay, but free won't charge
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=f"{app.config['BASE_URL']}/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{app.config['BASE_URL']}/cancel",
            )
            return jsonify({"id": session_obj.id})
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    # After Stripe Checkout returns
    @app.get("/success")
    def success():
        csid = request.args.get("session_id")
        if not csid:
            return "Missing session_id", 400

        try:
            cs = stripe.checkout.Session.retrieve(csid, expand=["customer", "subscription", "line_items"])
        except Exception as e:
            return f"Error retrieving checkout session: {e}", 400

        # Extract email & customer
        email = (cs.get("customer_details") or {}).get("email") or cs.get("customer_email")
        customer = cs.get("customer")
        customer_id = customer.id if hasattr(customer, 'id') else customer
        sub = cs.get("subscription")

        # Determine plan label from price used
        plan = "free"
        status = "active"
        current_period_end = None
        if sub:
            # pull live state from subscription
            sub_obj = stripe.Subscription.retrieve(sub) if isinstance(sub, str) else sub
            status = sub_obj.get("status", "active")
            current_period_end = sub_obj.get("current_period_end")
            # read first item price to map plan name
            try:
                price_id = sub_obj["items"]["data"][0]["price"]["id"]
            except Exception:
                price_id = None
            if price_id == app.config.get("STRIPE_PRICE_ID_VIP_MONTHLY"):
                plan = "vip_monthly"
            elif price_id == app.config.get("STRIPE_PRICE_ID_VIP_YEARLY"):
                plan = "vip_yearly"
            else:
                plan = "free"

        # Persist / update user record
        if email:
            upsert_user(
                email=email,
                stripe_customer_id=customer_id,
                plan=plan,
                status=status,
                current_period_end=current_period_end
            )
            # "Log them in" for this browser
            session["user_email"] = email

        return render_template("success.html")

    @app.get("/cancel")
    def cancel():
        return render_template("cancel.html")

    @app.get("/account")
    def account():
        if "user_email" not in session:
            return redirect(url_for("index"))
        user = get_user(session["user_email"])
        return render_template("account.html", user=user)

    # Stripe Customer Portal to manage/cancel
    @app.post("/create-portal-session")
    def create_portal_session():
        if "user_email" not in session:
            return jsonify({"error": "Not logged in"}), 401
        user = get_user(session["user_email"])
        if not user or not user["stripe_customer_id"]:
            return jsonify({"error": "No Stripe customer"}), 400
        return_url = app.config.get("STRIPE_PORTAL_RETURN_URL") or f"{app.config['BASE_URL']}/account"
        ps = stripe.billing_portal.Session.create(
            customer=user["stripe_customer_id"],
            return_url=return_url,
        )
        return jsonify({"url": ps.url})

    # Example VIP-only API (SmartScore, Singles)
    @app.get("/api/v1/smartscore")
    @require_vip
    def smartscore_api():
        return jsonify({"ok": True, "message": "VIP access granted", "data": {"score": 0.92}})

    # ---------- Magic Link Authentication ----------
    @app.get("/login")
    def login_get():
        return render_template("login.html")

    @app.post("/login")
    def login_post():
        email = (request.form.get("email") or "").strip().lower()
        if not email:
            return "Email required", 400

        # Create signed token with email
        token = signer.dumps({"email": email})
        link = f"{app.config['BASE_URL']}/auth/verify?token={token}"

        # Send email via Mailgun
        subject = "Your Pick3 App sign-in link"
        text = f"Click to sign in:\n\n{link}\n\nThis link expires in 15 minutes."
        try:
            send_email(app, to=email, subject=subject, text=text)
        except Exception as e:
            return f"Email error: {e}", 500

        return render_template("check_email.html", email=email)

    @app.get("/auth/verify")
    def auth_verify():
        token = request.args.get("token", "")
        if not token:
            return "Missing token", 400
        try:
            data = signer.loads(token, max_age=MAGIC_LINK_TTL)
        except SignatureExpired:
            return "This link has expired. Please request a new one.", 400
        except BadSignature:
            return "Invalid link.", 400

        email = (data.get("email") or "").strip().lower()
        if not email:
            return "Invalid link.", 400

        # Ensure user exists; if new, create with plan=None (or 'free' if you want)
        # You can also choose to auto-create as free plan here.
        upsert_user(email=email)

        # Log them in
        session["user_email"] = email

        # Optional: redirect VIPs to VIP page, others to pricing
        u = get_user(email)
        if u and u.get("plan") in ("vip_monthly", "vip_yearly") and u.get("status") in ("active","trialing"):
            return redirect(url_for("account"))
        return redirect(url_for("index"))

    @app.get("/logout")
    def logout():
        session.pop("user_email", None)
        return redirect(url_for("index"))

    # ---------- webhook: keep DB in sync ----------
    @app.post("/webhook")
    def webhook():
        endpoint_secret = app.config["STRIPE_WEBHOOK_SECRET"]
        payload = request.data
        sig_header = request.headers.get("Stripe-Signature", "")

        if not endpoint_secret:
            # In dev, you can return 200 to avoid noise; in prod use the real secret
            return "Webhook not configured", 200

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except Exception as e:
            return str(e), 400

        t = event["type"]
        obj = event["data"]["object"]

        # Map subscription events to user table
        if t in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted", "invoice.payment_succeeded"):
            sub = obj
            customer_id = sub.get("customer")
            status = sub.get("status")
            current_period_end = sub.get("current_period_end")
            # Get the email from the customer object
            try:
                cust = stripe.Customer.retrieve(customer_id)
                email = cust.get("email")
            except Exception:
                email = None

            # Determine plan
            price_id = None
            try:
                price_id = sub["items"]["data"][0]["price"]["id"]
            except Exception:
                pass

            plan = None
            if price_id == app.config.get("STRIPE_PRICE_ID_VIP_MONTHLY"):
                plan = "vip_monthly"
            elif price_id == app.config.get("STRIPE_PRICE_ID_VIP_YEARLY"):
                plan = "vip_yearly"
            # If canceled, keep plan label but mark status canceled
            if email:
                upsert_user(
                    email=email,
                    stripe_customer_id=customer_id,
                    plan=plan,
                    status=status,
                    current_period_end=current_period_end
                )

        elif t == "checkout.session.completed":
            # backup: handle free plan or missing sub
            email = (obj.get("customer_details") or {}).get("email") or obj.get("customer_email")
            customer = obj.get("customer")
            customer_id = customer.id if hasattr(customer, 'id') else customer
            if email:
                upsert_user(email=email, stripe_customer_id=customer_id)

        return "ok", 200

    return app

def send_email(app, to, subject, text):
    return requests.post(
        f"https://api.mailgun.net/v3/{app.config['MAILGUN_DOMAIN']}/messages",
        auth=("api", app.config["MAILGUN_API_KEY"]),
        data={
            "from": app.config["MAIL_FROM"],
            "to": [to],
            "subject": subject,
            "text": text
        },
        timeout=20
    )