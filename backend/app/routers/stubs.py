"""
All benchmark endpoints previously stubbed here are now fully implemented:
  - POST /smes/{sme_id}/materials  → app/routers/materials.py
  - POST /smes/{sme_id}/knowledge/synthesize → app/routers/knowledge.py
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")
