import os
import requests
import streamlit as st

BACKEND_URL = st.secrets.get(
    "BACKEND_URL",
    os.getenv("BACKEND_URL", "https://financify-saas.onrender.com")
).rstrip("/")

SURECART_CHECKOUT_URL = st.secrets.get(
    "SURECART_CHECKOUT_URL",
    os.getenv("SURECART_CHECKOUT_URL", "")
)


def _post(path: str, payload: dict, timeout: int = 120):
    response = requests.post(
        f"{BACKEND_URL}{path}",
        json=payload,
        timeout=timeout
    )

    if response.status_code >= 400:
        try:
            raise RuntimeError(response.json().get("detail", response.text))
        except Exception:
            raise RuntimeError(response.text)

    return response.json()


def send_login_code(email: str):
    return _post("/auth/request-otp", {"email": email})


def verify_login_code(email: str, otp: str):
    return _post("/auth/verify-otp", {"email": email, "otp": otp})


def get_current_access(tool_name: str) -> dict:
    email = st.session_state.get("financify_email", "")

    if not email:
        return {"logged_in": False}

    return _post("/usage/check", {
        "email": email,
        "tool_name": tool_name
    })


def record_tool_use(tool_name: str):
    email = st.session_state.get("financify_email", "")

    if not email:
        return None

    return _post("/usage/record", {
        "email": email,
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


def login_ui(tool_name: str):
    st.markdown("## 🔐 Login required")
    st.write("Login with email OTP to use your free trials or Pro subscription.")

    email = st.text_input("Email address", key="financify_login_email")
    otp = st.text_input("6-digit login code", key="financify_login_otp")

    c1, c2 = st.columns(2)

    with c1:
        if st.button("Send login code", use_container_width=True):
            try:
                send_login_code(email)
                st.session_state["financify_email"] = email
                st.success("OTP sent. Check your email.")
            except Exception as e:
                st.error(str(e))

    with c2:
        if st.button("Verify login", use_container_width=True):
            try:
                verify_login_code(email, otp)
                st.session_state["financify_email"] = email
                st.session_state["financify_logged_in"] = True
                st.success("Login successful.")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    st.markdown("---")
    st.write("Want more runs? Upgrade to Pro for 100 uses per tool.")
    upgrade_button()


def require_tool_access(tool_name: str, display_name: str = None):
    display_name = display_name or tool_name

    if not st.session_state.get("financify_logged_in"):
        login_ui(display_name)
        st.stop()

    access = get_current_access(tool_name)

    plan = access.get("plan", "free")
    used = access.get("used", access.get("usage_count", 0))
    limit = access.get("limit", 5 if plan == "free" else 100)
    remaining = access.get("remaining", max(0, limit - used))
    allowed = access.get("allowed", remaining > 0)

    st.info(
        f"🔐 Logged in as {st.session_state.get('financify_email')} | "
        f"Plan: {plan.upper()} | Used this month: {used}/{limit} | Remaining: {remaining}"
    )

    c1, c2 = st.columns(2)

    with c1:
        if st.button("Logout", use_container_width=True):
            st.session_state.clear()
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
