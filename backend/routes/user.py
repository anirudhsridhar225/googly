from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

import models
import db

router = APIRouter()


@router.get("/health")
async def user_endpoint():
    return {"message": "hello user"}


@router.post("/add")
async def add_user(user_data: models.User):
    new_user = user_data.dict()
    new_user["id"] = str(new_user["id"])
    # when we are creating a new user, their history will always be empty right
    new_user["history"] = []

    db.db.collection("users").document(new_user["id"]).set(new_user)

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": f"new user {new_user} has been saved",
        },
    )


@router.delete("/delete/{id}")
async def delete_user(id: str):
    docRef = db.db.collection("users").document(id)
    doc = docRef.get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="User not found")

    docRef.delete()
    return JSONResponse(
        status_code=200,
        content={"status": "success", "message": f"user {id} has been deleted"},
    )


@router.put("/update/{id}")
async def update_user(id: str, updates: models.UserUpdate):
    doc_ref = db.db.collection("users").document(id)
    doc = doc_ref.get()

    if not doc.exists:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = {k: v for k, v in updates.dict().items() if v is not None}

    if not update_data:
        raise HTTPException(status_code=400, detail="User update details not found")

    if update_data.get("wants_history") is False:
        update_data["history"] = []

    doc_ref.update(update_data)

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": f"user {id}'s details have been updated",
        },
    )
