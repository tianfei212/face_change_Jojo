from fastapi import APIRouter, Request


router = APIRouter()


@router.get("/status")
def get_status(request: Request):
    return request.app.state.status