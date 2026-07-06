from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
import json
import os

router = APIRouter()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@router.get("/", response_class=HTMLResponse)
async def get_dashboard():
    with open(os.path.join(BASE_DIR, "static/index.html"), "r", encoding="utf-8") as f:
        return f.read()

@router.get("/api/status")
async def get_status():
    from main import system_status
    return system_status
