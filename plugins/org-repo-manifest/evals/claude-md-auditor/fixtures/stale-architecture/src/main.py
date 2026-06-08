from fastapi import FastAPI
from sqlalchemy.orm import Session

app = FastAPI()

@app.post("/orders")
def create_order(): ...
