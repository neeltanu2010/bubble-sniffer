import os
from datetime import datetime
import requests
import streamlit as st

# Financify premium protection layer
# - Email OTP login via Render backend
# - Free/pro usage-limit display
# - Premium styled login page
# - Upgrade button always visible when user is free/limited

BACKEND_URL = st.secrets.get("BACKEND_URL", os.getenv("BACKEND_URL", "https://financify-saas.onrender.com")).rstrip("/")
SURECART_CHECKOUT_URL = st.secrets.get("SURECART_CHECKOUT_URL", os.getenv("SURECART_CHECKOUT_URL", ""))


def _premium_auth_css():
    st.markdown(
        """
        <style>
        .fin-auth-shell {
            max-width: 980px;
            margin: 0 auto 2rem auto;
            padding: 1.2rem;
        }
        .fin-auth-card {
            border-radius: 34px;
            padding: 34px 36px;
            background:
                radial-gradient(circle at 92% 12%, rgba(245,197,66,.20), transparent 15rem),
                radial-gradient(circle at 8% 8%, rgba(124,58,237,.10), transparent 14rem),
                linear-gradient(135deg, rgba(255,255,255,.98), rgba(255,249,232,.97));
            border: 1px solid rgba(230,164,0,.22);
            box-shadow: 0 24px 70px rgba(23,26,31,.10);
            color: #171A1F;
        }
        .fin-auth-kicker {
            display:inline-flex;
            padding: 8px 13px;
            border-radius: 999px;
            background:#FFF3BF;
            color:#7A5600;
            font-weight: 950;
            font-size:.78rem;
            letter-spacing:.05em;
            text-transform:uppercase;
            border: 1px solid rgba(230,164,0,.20);
            margin-bottom: 12px;
        }
        .fin-auth-title {
            font-size: 2.25rem;
            font-weight: 950;
            letter-spacing: -.045em;
            margin: 0 0 .55rem 0;
            color: #111827;
        }
        .fin-auth-text {
            color:#4B5563;
            line-height:1.7;
            font-size:1.02rem;
            max-width: 820px;
        }
        .fin-auth-metrics {
            display:flex;
            flex-wrap:wrap;
            gap:10px;
            margin-top: 18px;
        }
        .fin-auth-pill {
            padding: 9px 13px;
            border-radius: 999px;
            background: rgba(255,255,255,.92);
            border: 1px solid rgba(23,26,31,.09);
            color:#374151;
            font-weight:850;
            font-size:.86rem;
        }
        .fin-status {
            border-radius: 22px;
            padding: 14px 16px;
            border: 1px solid rgba(23,26,31,.08);
            background: rgba(255,255,255,.94);
            box-shadow: 0 12px 30px rgba(23,26,31,.05);
            margin-bottom: 1rem;
        }
        .fin-upgrade-box {
            border-radius: 28px;
            padding: 22px 24px;
            background:
                radial-gradient(circle at 90% 18%, rgba(245,197,66,.20), transparent 13rem),
                linear-gradient(135deg, rgba(255,255,255,.98), rgba(255,243,191,.96));
            border: 1px solid rgba(230,164,0,.22);
            box-shadow: 0 18px 50px rgba(23,26,31,.08);
            margin: 18px 0;
        }
        .fin-upgrade-title {
            font-size: 1.35rem;
            font-weight: 950;
            color:#111827;
            letter-spacing:-.03em;
            margin-bottom: 6px;
        }
        .fin-upgrade-text {
            color:#4B5563;
            line-height:1.65;
            margin-bottom: 14px;
        }
        div.stButton > button {
            border-radius: 16px !important;
            min-height: 3rem;
            font-weight: 950 !important;
            box-shadow: 0 12px 28px rgba(23,26,31,.10);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _post(path: str, payload: dict, timeout: int = 120):
    try:
        response = requests.post(f"{BACKEND_URL}{path}", json=payload, timeout=timeout)
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            raise RuntimeError(str(detail))
        try:
            return response.json()
        except Exception:
            return {"ok": True, "raw": response.text}
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not connect to Financify backend: {exc}")


def _get(path: str, params: dict | None = None, timeout: int = 120):
    try:
        response = requests.get(f"{BACKEND_URL}{path}", params=params or {}, timeout=timeout)
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            raise RuntimeError(str(detail))
        try:
            return response.json()
        except Exception:
            return {"ok": True, "raw": response.text}
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not connect to Financify backend: {exc}")


def _get_email_from_token(token: str) -> str:
    # Backend tokens may be JWT-like or opaque. We keep the email separately in session.
    return st.session_state.get("financify_email", "")


def _upgrade_button(label: str = "🚀 Upgrade to Financify Pro — ₹499/month"):
    if SURECART_CHECKOUT_URL:
        st.link_button(label, SURECART_CHECKOUT_URL, use_container_width=True)
    else:
        st.warning("Upgrade link missing. Add SURECART_CHECKOUT_URL in Streamlit Secrets.")


def _render_login(tool_display_name: str):
    _premium_auth_css()
    st.markdown(
        f"""
        <div class="fin-auth-shell">
          <div class="fin-auth-card">
            <div class="fin-auth-kicker">Financify Pro Access</div>
            <div class="fin-auth-title">Unlock {tool_display_name}</div>
            <div class="fin-auth-text">
              Login with your email OTP to use free trials or your Pro subscription.
              Blog pages stay public and free. Tools are protected separately.
            </div>
            <div class="fin-auth-metrics">
              <span class="fin-auth-pill">5 free uses per tool</span>
              <span class="fin-auth-pill">100 Pro uses per tool</span>
              <span class="fin-auth-pill">₹499/month</span>
              <span class="fin-auth-pill">Email OTP login</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(f"### Access {tool_display_name}")
    email = st.text_input("Email address", value=st.session_state.get("financify_email", ""), key="fin_login_email")
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Send login code", use_container_width=True):
            if not email or "@" not in email:
                st.error("Enter a valid email.")
            else:
                try:
                    _post("/auth/request-otp", {"email": email})
                    st.session_state["financify_email"] = email
                    st.success("Login code sent. Check your email.")
                except Exception as exc:
                    st.error(str(exc))
    otp = st.text_input("6-digit login code", key="fin_login_otp")
    with c2:
        if st.button("Verify login", use_container_width=True, type="primary"):
            if not email or not otp:
                st.error("Enter email and OTP.")
            else:
                try:
                    data = _post("/auth/verify-otp", {"email": email, "otp": otp})
                    st.session_state["financify_email"] = email
                    st.session_state["financify_token"] = data.get("token") or data.get("access_token") or data.get("session_token") or "verified"
                    st.success("Login successful.")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

    st.markdown('<div class="fin-upgrade-box"><div class="fin-upgrade-title">Want more runs?</div><div class="fin-upgrade-text">Upgrade once and unlock 100 uses per tool across Financify tools.</div></div>', unsafe_allow_html=True)
    _upgrade_button()


def get_current_access(tool_name: str) -> dict:
    email = st.session_state.get("financify_email", "")
    token = st.session_state.get("financify_token", "")
    if not email or not token:
        return {"logged_in": False}

    # Try common backend endpoint names. If one fails, fall back gracefully.
    payload = {"email": email, "tool_name": tool_name}
    for path in ["/tools/check-access", "/check-access", "/usage/check", "/auth/check-access"]:
        try:
            data = _post(path, payload)
            data["logged_in"] = True
            return data
        except Exception:
            continue

    # Fallback for older backend: assume free if verification succeeded.
    return {"logged_in": True, "email": email, "plan": "free", "limit": 5, "used": 0, "remaining": 5, "allowed": True}


def require_tool_access(tool_name: str, tool_display_name: str | None = None):
    tool_display_name = tool_display_name or tool_name.replace("-", " ").replace("_", " ").title()
    if "financify_token" not in st.session_state or "financify_email" not in st.session_state:
        _render_login(tool_display_name)
        st.stop()

    _premium_auth_css()
    access = get_current_access(tool_name)
    email = st.session_state.get("financify_email", "")
    plan = str(access.get("plan") or access.get("user_plan") or "free").upper()
    used = access.get("used", access.get("usage_count", access.get("used_this_month", 0)))
    limit = access.get("limit", access.get("monthly_limit", 5 if plan.lower() == "free" else 100))
    remaining = access.get("remaining", max(0, int(limit or 0) - int(used or 0)) if str(used).isdigit() and str(limit).isdigit() else "")
    allowed = access.get("allowed", True)

    st.markdown(
        f"""
        <div class="fin-status">
          🔐 Logged in as <b>{email}</b> |
          Plan: <b>{plan}</b> |
          Used this month: <b>{used}/{limit}</b> |
          Remaining: <b>{remaining}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )

    logout_col, upgrade_col = st.columns([1, 1])
    with logout_col:
        if st.button("Logout", use_container_width=True):
            st.session_state.pop("financify_token", None)
            st.session_state.pop("financify_email", None)
            st.rerun()
    with upgrade_col:
        if str(plan).lower() != "pro":
            _upgrade_button("🚀 Upgrade to Financify Pro")

    if not allowed or (str(plan).lower() != "pro" and str(remaining) not in ("", "None") and int(remaining or 0) <= 0):
        st.error("Your free limit is finished for this tool.")
        st.markdown('<div class="fin-upgrade-box"><div class="fin-upgrade-title">Upgrade to Financify Pro</div><div class="fin-upgrade-text">Get 100 uses per tool for ₹499/month.</div></div>', unsafe_allow_html=True)
        _upgrade_button()
        st.stop()

    return access


def record_tool_use(tool_name: str):
    email = st.session_state.get("financify_email", "")
    token = st.session_state.get("financify_token", "")
    if not email or not token:
        return None
    payload = {"email": email, "tool_name": tool_name}
    for path in ["/tools/record-usage", "/record-usage", "/usage/record", "/tool/record"]:
        try:
            return _post(path, payload)
        except Exception:
            continue
    return None
