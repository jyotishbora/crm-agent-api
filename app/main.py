from fastapi import FastAPI

app = FastAPI(title="CRM Agent API")


@app.get("/")
async def root():
    return {"message": "CRM Agent API is running"}


@app.get("/health")
async def health():
    return {"status": "ok"}
