# Financify tools — premium login UI update

This package updates:
- Bubble Sniffer
- Macro Dance Floor
- Portfolio Hive Check

Changes:
- Premium Honey Scanner-style login page
- Visible "Upgrade to Financify Pro" button
- Free limit block screen with upgrade button
- Usage tracking on real run buttons

## Required Streamlit Secrets

Add these to each Streamlit app:

```toml
BACKEND_URL = "https://financify-saas.onrender.com"
SURECART_CHECKOUT_URL = "PASTE_YOUR_SURECART_CHECKOUT_URL_HERE"
```

## GitHub placement

For each tool repo:
1. Rename the matching `*-app.py` to `app.py`, or copy its contents into your current `app.py`.
2. Upload `protect_tool.py` to the same root folder as `app.py`.
3. Keep your existing `requirements.txt`, but make sure it includes `requests`.

Example:
```
app.py
protect_tool.py
requirements.txt
```

Then commit and reboot Streamlit.
