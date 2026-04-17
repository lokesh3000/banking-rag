from fastapi import FastAPI
from src.api.v1.routes.query import router as query_router
from src.api.v1.routes.admin import router as admin_router

# Create a FastAPI instance
app = FastAPI(title="RAG API")

# we will enable rest api endpoint at localhost:8000/
@app.get("/")
def read_root():
    return {
        "message": "Hello World!"
    }

# health check endpoint
@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }

app.include_router(query_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1/admin")