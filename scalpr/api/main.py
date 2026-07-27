"""SCALPR API entry point.

All logic moved to bootstrap.py and routers/. This file exists only for
backward compatibility with the `uvicorn scalpr.api.main:app` command.
"""
from scalpr.api.bootstrap import create_app

app = create_app()
