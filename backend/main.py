from fastapi import FastAPI

from routes import text_ocr, user

app = FastAPI()

app.include_router(text_ocr.router, prefix="/api/ocr", tags=["ocr"])
app.include_router(user.router, prefix="/api/user", tags=["user"])


@app.get("/")
async def hello():
    return {"message": "hello world"}
