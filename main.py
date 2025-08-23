from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from schemas import SearchQuery, FinalProfile
from services import SearchOrchestrator

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

orchestrator = SearchOrchestrator()

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/search", response_model=FinalProfile)
async def search(query: SearchQuery):
    return await orchestrator.search(query)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)