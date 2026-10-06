import uvicorn

if __name__ == "__main__":
    print("🚀 Starting AI Microservice at http://127.0.0.1:8000 (0.0.0.0:8000)")
    print("📖 Swagger UI → http://127.0.0.1:8000/docs or http://localhost:8000/docs")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
