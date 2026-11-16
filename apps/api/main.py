"""ASGI entrypoint: uvicorn apps.api.main:app"""
from memory_mesh.api import create_app

app = create_app()
