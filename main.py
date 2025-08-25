from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from schemas import SearchQuery, FinalProfile, Candidate, ShallowResponse, DeepResponse
from tools.espy.client import EspyClient
from services import SearchOrchestrator

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

orchestrator = SearchOrchestrator()

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/search", response_model=ShallowResponse)
async def search(query: SearchQuery):
    return await orchestrator.perform_shallow_search(query)

@app.post("/profile/enrich", response_model=DeepResponse)
async def enrich(candidate: Candidate):
    return await orchestrator.perform_deep_search(candidate)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

@app.get("/espy/poll/{request_id}")
async def poll_espy(request_id: int):
    client = EspyClient()
    return await client.poll_request(request_id)