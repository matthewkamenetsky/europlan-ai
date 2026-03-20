from fastapi import FastAPI
from api.routes import router

app = FastAPI(title="Europlan AI")
app.include_router(router)

@app.get("/")
def root():
    return {"message": "Europlan AI is running"}