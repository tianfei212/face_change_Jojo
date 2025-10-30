from fastapi import APIRouter, UploadFile, File
import os
import pathlib


router = APIRouter()

ASSETS_DIR = "/opt/fusion_assets/user"
ASSETS_FACE = os.path.join(ASSETS_DIR, "face")
ASSETS_BG = os.path.join(ASSETS_DIR, "background")

pathlib.Path(ASSETS_FACE).mkdir(parents=True, exist_ok=True)
pathlib.Path(ASSETS_BG).mkdir(parents=True, exist_ok=True)


@router.post("/upload/face")
async def upload_face(file: UploadFile = File(...)):
    dst = os.path.join(ASSETS_FACE, file.filename)
    contents = await file.read()
    with open(dst, "wb") as f:
        f.write(contents)
    return {"ok": True, "path": dst}


@router.post("/upload/background")
async def upload_background(file: UploadFile = File(...)):
    dst = os.path.join(ASSETS_BG, file.filename)
    contents = await file.read()
    with open(dst, "wb") as f:
        f.write(contents)
    return {"ok": True, "path": dst}