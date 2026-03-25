import os

# Ensure env vars required at import time are set before test collection
os.environ.setdefault("SEC_USER_AGENT", "Test Agent test@example.com")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake")
