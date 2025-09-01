from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def get_ocr():
    return {"message": "you've reached the ocr router"}


@router.get("/categorise")
async def get_hex():
    # TODO: handled the get endpoint to get the tags from the ai and assign hex accordingly
    return {"message": "hex_code"}


@router.post("/categorise")
async def categorise_data():
    # TODO: handle the post endpoint to post the pdf to the ai
    return {"message": "i have posted"}
