"""ASGI entry point for local development and serverless deployment."""

import logging
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

logging.basicConfig(level=logging.INFO)
logging.getLogger("invoicechaser").setLevel(logging.INFO)

from web.bootstrap import runtime  # noqa: E402  (environment must load first)

globals().update(runtime.exports)
app = runtime.app
