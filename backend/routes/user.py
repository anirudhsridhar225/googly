from fastapi import APIRouter

router = APIRouter()

@router.get("")
async def user_endpoint():
    return {"message": "hello user"}
