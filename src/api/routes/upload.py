"""Upload API route — handles WhatsApp chat file uploads."""

from fastapi import APIRouter, UploadFile, File
from src.api.services.ranking_service import upload_chat_data

router = APIRouter(tags=["upload"])


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(..., description="WhatsApp chat .txt file"),
):
    """Upload a WhatsApp chat file to parse and store new game data."""
    if not file.filename or not file.filename.endswith(".txt"):
        return {"error": "Please upload a .txt file"}

    content = await file.read()
    result = upload_chat_data(content)
    return result
