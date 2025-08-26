from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from schemas import SearchQuery, FinalProfile, Candidate, ShallowResponse, DeepResponse, PlanResponse
from tools.espy.client import EspyClient
from services.orchestrator import SearchOrchestrator
from services.planner import generate_plan
from services.executor import execute_plan_scrape_only

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

@app.post("/plan/search", response_model=PlanResponse)
async def plan_search(query: SearchQuery):
    params = query.model_dump(exclude_none=True)
    return await generate_plan(stage="shallow", params=params)

@app.post("/plan/enrich", response_model=PlanResponse)
async def plan_enrich(candidate: Candidate):
    params = candidate.model_dump(exclude_none=True)
    return await generate_plan(stage="deep", params=params)

@app.post("/execute/plan")
async def execute_plan(plan: PlanResponse):
    return await execute_plan_scrape_only(plan)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

@app.get("/espy/poll/{request_id}")
async def poll_espy(request_id: int):
    client = EspyClient()
    return await client.poll_request(request_id)