# Financify tools with login + paid usage integrated

This folder contains your uploaded Streamlit tools patched with Financify login and usage tracking.

## Files
- `common/protect_tool.py` — shared login/OTP/usage helper.
- `bubble-sniffer/bubble_sniffer.py` — protected as `bubble-sniffer`.
- `honey-scanner/app.py` — protected as `honey-scanner`.
- `macro-dance-floor/macro_dance_floor.py` — protected as `macro-dance-floor`.
- `portfolio-hive-check/app.py` — protected as `portfolio-hive-check`.

## Streamlit secrets required for every app

```toml
BACKEND_URL = "https://financify-saas.onrender.com"
SURECART_CHECKOUT_URL = "YOUR_SURECART_CHECKOUT_URL"
```

## What was added
At the top of each tool, this was added:

```python
from common.protect_tool import require_tool_access, record_tool_use
TOOL_NAME = "..."
user = require_tool_access(TOOL_NAME)
```

And `record_tool_use(TOOL_NAME)` was added inside the main Run/Analyze button flow.

Free users get 5 uses per tool per month. Pro users get 100 uses per tool per month.
