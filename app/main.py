from fastapi import FastAPI
from app.api.endpoints import contacts

app = FastAPI(title="Contact Manager API")

from fastapi.middleware.cors import CORSMiddleware

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(contacts.router, prefix="/contacts", tags=["contacts"])

@app.get("/")
async def root():
    return {"message": "Welcome to Contact Manager API"}
