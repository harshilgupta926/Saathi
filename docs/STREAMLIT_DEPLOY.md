# Saathi Streamlit demo

The Streamlit app is a visual/demo shell around the existing Saathi orchestrator. It imports the backend directly, so routing and factual-tool policy are not duplicated.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r streamlit_app/requirements.txt
streamlit run streamlit_app/app.py
```

## Streamlit Community Cloud

Create an app with:
- Repository: `kaustubhdua/Saathi`
- Branch: `main`
- Main file: `streamlit_app/app.py`

Dependencies are declared in `streamlit_app/requirements.txt`.

The demo is useful without provider credentials because the backend defaults to demo-safe mode. For live providers, configure secrets/environment values in Community Cloud and never commit keys.

Recommended first live secrets:
```toml
DEMO_MODE = false
GEMINI_API_KEY = "..."
SARVAM_API_KEY = "..."
MANDI_API_KEY = "..."
MANDI_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
```

Optional telephony secrets, only after the public HTTPS/WSS endpoint has been verified:
```toml
EXOTEL_API_KEY = "..."
EXOTEL_API_TOKEN = "..."
EXOTEL_ACCOUNT_SID = "..."
EXOTEL_VIRTUAL_NUMBER = "..."
EXOTEL_STREAM_URL = "wss://..."
TELEPHONY_WEBHOOK_SECRET = "..."
CALL_API_TOKEN = "..."
```

Do not paste credentials into the repository. Add them through Streamlit Community Cloud's Secrets UI.

The Streamlit entrypoint mirrors supported Community Cloud secrets into the process environment before the backend `Settings` object is created, so use the same uppercase names. The demo never prints secret values.

Do not enable live mode until the corresponding provider path has actually been exercised and verified.
