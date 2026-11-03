"""Entry point:  uvicorn parking.main:app --reload"""
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv is optional
    pass

from parking.bootstrap import create_app_from_env  # noqa: E402

app = create_app_from_env()
