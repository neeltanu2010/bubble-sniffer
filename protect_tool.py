import os
import requests
import streamlit as st

BACKEND_URL = st.secrets.get(
    "BACKEND_URL",
    os.getenv("BACKEND_URL", "https://financify-saas.onrender.com")
).rstrip("/")

SURECART_CHECKOUT_URL = st.secrets.get(
    "SURECART_CHECKOUT_URL",
    os.getenv("SURECART_CHECKOUT_URL", "https://financify.blog/buy/financify-tools")
)


def _post(path: str, payload: dict, timeout: int = 120):
    response = requests.post(
        f"{BACKEND_URL}{path}",
        json=payload,
        timeout=timeout
    )

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


def send_login_code(email: str):
    email = (email or "").strip().lower()
    if not email:
        raise RuntimeError("Please enter your email.")
    return _post("/auth/request-otp", {"email": email})


def verify_login_code(email: str, otp: str):
    email = (email or "").strip().lower()
    otp = (otp or "").strip()
    if not email or not otp:
        raise RuntimeError("Please enter email and OTP.")
    return _post("/auth/verify-otp", {"email": email, "otp": otp})


def get_current_access(tool_name: str) -> dict:
    email = st.session_state.get("financify_email", "")
    session_token = st.session_state.get("financify_token", "")

    if not email or not session_token:
        return {"logged_in": False}

    return _post("/usage/check", {
        "email": email,
        "session_token": session_token,
        "tool_name": tool_name
    })


def record_tool_use(tool_name: str):
    email = st.session_state.get("financify_email", "")
    session_token = st.session_state.get("financify_token", "")

    if not email or not session_token:
        return None

    return _post("/usage/record", {
        "email": email,
        "session_token": session_token,
        "tool_name": tool_name
    })


def upgrade_button():
    if SURECART_CHECKOUT_URL:
        st.link_button(
            "🚀 Upgrade to Financify Pro — ₹499/month",
            SURECART_CHECKOUT_URL,
            use_container_width=True
        )
    else:
        st.warning("SURECART_CHECKOUT_URL missing in Streamlit Secrets.")


def login_ui(tool_display_name: str):
    st.markdown(
        """
        <style>
        .fin-login-card {
            border-radius: 34px;
            padding: 34px 36px;
            background:
                radial-gradient(circle at 92% 12%, rgba(245,197,66,.22), transparent 15rem),
                radial-gradient(circle at 8% 8%, rgba(124,58,237,.10), transparent 14rem),
                linear-gradient(135deg, rgba(255,255,255,.98), rgba(255,249,232,.97));
            border: 1px solid rgba(230,164,0,.22);
            box-shadow: 0 24px 70px rgba(23,26,31,.10);
            color: #171A1F;
            margin-bottom: 24px;
        }
        .fin-login-kicker {
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
        .fin-login-title {
            font-size: 2.25rem;
            font-weight: 950;
            letter-spacing: -.045em;
            margin: 0 0 .55rem 0;
            color: #111827;
        }
        .fin-login-text {
            color:#4B5563;
            line-height:1.7;
            font-size:1.02rem;
            max-width: 820px;
        }
        .fin-login-pill {
            display:inline-flex;
            padding: 9px 13px;
            border-radius: 999px;
            background: rgba(255,255,255,.92);
            border: 1px solid rgba(23,26,31,.09);
            color:#374151;
            font-weight:850;
            font-size:.86rem;
            margin: 14px 8px 0 0;
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
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        f"""
        <div class="fin-login-card">
          <div class="fin-login-kicker">Financify Pro Access</div>
          <div class="fin-login-title">Unlock {tool_display_name}</div>
          <div class="fin-login-text">
            Login with your email OTP to use free trials or your Pro subscription.
            Blog pages stay public and free. Tools are protected separately.
          </div>
          <span class="fin-login-pill">5 free uses per tool</span>
          <span class="fin-login-pill">100 Pro uses per tool</span>
          <span class="fin-login-pill">₹499/month</span>
          <span class="fin-login-pill">Email OTP login</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    email = st.text_input(
        "Email address",
        value=st.session_state.get("financify_email", ""),
        key="financify_login_email"
    )

    otp = st.text_input(
        "6-digit login code",
        key="financify_login_otp"
    )

    c1, c2 = st.columns(2)

    with c1:
        if st.button("Send login code", use_container_width=True):
            try:
                send_login_code(email)
                st.session_state["financify_email"] = email.strip().lower()
                st.success("OTP sent. Check your email.")
            except Exception as e:
                st.error(str(e))

    with c2:
        if st.button("Verify login", use_container_width=True, type="primary"):
            try:
                data = verify_login_code(email, otp)

                token = (
                    data.get("session_token")
                    or data.get("token")
                    or data.get("access_token")
                )

                if not token:
                    st.error("Login succeeded, but backend did not return a session token.")
                    st.stop()

                st.session_state["financify_email"] = email.strip().lower()
                st.session_state["financify_token"] = token
                st.session_state["financify_logged_in"] = True

                st.success("Login successful.")
                st.rerun()

            except Exception as e:
                st.error(str(e))

    st.markdown(
        """
        <div class="fin-upgrade-box">
          <div class="fin-upgrade-title">Want more runs?</div>
          <div class="fin-upgrade-text">Upgrade once and unlock 100 uses per tool across Financify tools.</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    upgrade_button()


def require_tool_access(tool_name: str, display_name: str = None):
    display_name = display_name or tool_name

    if not st.session_state.get("financify_logged_in"):
        login_ui(display_name)
        st.stop()

    try:
        access = get_current_access(tool_name)
    except Exception as e:
        for key in ["financify_email", "financify_token", "financify_logged_in"]:
            st.session_state.pop(key, None)

        st.error("Your login session expired. Please login again.")
        st.caption(str(e))
        login_ui(display_name)
        st.stop()

    plan = access.get("plan", "free")
    used = int(access.get("usage_count", access.get("used", 0)) or 0)
    limit = int(access.get("limit", 5 if plan == "free" else 100) or 5)
    remaining = int(access.get("remaining", max(0, limit - used)) or 0)
    allowed = bool(access.get("allowed", remaining > 0))

    st.info(
        f"🔐 Logged in as {st.session_state.get('financify_email')} | "
        f"Plan: {plan.upper()} | Used this month: {used}/{limit} | Remaining: {remaining}"
    )

    c1, c2 = st.columns(2)

    with c1:
        if st.button("Logout", use_container_width=True):
            for key in ["financify_email", "financify_token", "financify_logged_in"]:
                st.session_state.pop(key, None)
            st.rerun()

    with c2:
        if plan != "pro":
            upgrade_button()

    if not allowed:
        st.error("Your free limit is finished for this tool.")
        st.write("Upgrade to Financify Pro for 100 uses per tool.")
        upgrade_button()
        st.stop()

    return access
