from fastapi import APIRouter


router = APIRouter()


@router.post("/sdp")
async def sdp_exchange():
    # Placeholder for aiortc signaling
    return {"ok": True, "message": "SDP endpoint placeholder"}