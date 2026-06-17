import os
import requests
import streamlit as st

BACKEND_URL = st.secrets.get("BACKEND_URL", os.getenv("BACKEND_URL", "http://localhost:8000")).rstrip("/")
SURECART_CHECKOUT_URL = st.secrets.get("SURECART_CHECKOUT_URL", os.getenv("SURECART_CHECKOUT_URL", ""))


def _post(path: str, payload: dict):
    try:
        response = requests.post(f"{BACKEND_URL}{path}", json=payload, timeout=20)
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            raise RuntimeError(detail)
        return response.json()
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not connect to Financify backend: {exc}")


def login_box():
    st.sidebar.subheader("Financify Login")

    if st.session_state.get("financify_email") and st.session_state.get("financify_session_token"):
        st.sidebar.success(f"Logged in: {st.session_state['financify_email']}")
        if st.sidebar.button("Logout"):
            for key in ["financify_email", "financify_session_token", "otp_email_sent"]:
                st.session_state.pop(key, None)
            st.rerun()
        return st.session_state["financify_email"], st.session_state["financify_session_token"]

    st.info("Login is required to use this Financify tool. Your blog stays free.")
    email = st.text_input("Email", key="login_email").strip().lower()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Send login code"):
            if not email:
                st.error("Enter your email first.")
            else:
                try:
                    _post("/auth/request-otp", {"email": email})
                    st.session_state["otp_email_sent"] = email
                    st.success("Login code sent. Check your email.")
                except RuntimeError as exc:
                    st.error(str(exc))

    otp = st.text_input("6-digit login code", max_chars=6, key="login_otp")
    with col2:
        if st.button("Verify login"):
            verify_email = st.session_state.get("otp_email_sent") or email
            if not verify_email or not otp:
                st.error("Enter email and login code.")
            else:
                try:
                    data = _post("/auth/verify-otp", {"email": verify_email, "otp": otp})
                    st.session_state["financify_email"] = data["email"]
                    st.session_state["financify_session_token"] = data["session_token"]
                    st.success("Login successful.")
                    st.rerun()
                except RuntimeError as exc:
                    st.error(str(exc))

    st.stop()


def require_tool_access(tool_name: str):
    email, session_token = login_box()

    data = _post("/usage/check", {
        "email": email,
        "tool_name": tool_name,
        "session_token": session_token,
    })

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Usage")
    st.sidebar.write(f"Plan: **{data['plan'].upper()}**")
    st.sidebar.write(f"Used: **{data['usage_count']}/{data['limit']}**")

    if SURECART_CHECKOUT_URL:
        st.sidebar.link_button("🚀 Upgrade to Pro - ₹499/month", SURECART_CHECKOUT_URL)

    if not data.get("allowed"):
        st.error("Your free limit is finished for this tool.")
        st.write("Upgrade to Financify Pro for 100 uses per tool.")
        if SURECART_CHECKOUT_URL:
            st.link_button("🚀 Upgrade to Pro - ₹499/month", SURECART_CHECKOUT_URL)
        st.stop()

    return {"email": email, "session_token": session_token, "usage": data}


def record_tool_use(tool_name: str):
    email = st.session_state.get("financify_email")
    session_token = st.session_state.get("financify_session_token")
    if not email or not session_token:
        st.error("Login session missing. Please login again.")
        st.stop()

    data = _post("/usage/record", {
        "email": email,
        "tool_name": tool_name,
        "session_token": session_token,
    })

    if data.get("remaining", 0) == 0:
        st.warning("This was your last allowed use for this tool this month.")

    return data
