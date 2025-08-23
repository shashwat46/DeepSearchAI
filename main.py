from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from schemas import SearchQuery, FinalProfile
from agent import parse_user_request, synthesize_profile
from tools import get_mock_linkedin_data, get_mock_github_data

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/search", response_model=FinalProfile)
async def search(query: SearchQuery):
    if not query.free_text_context:
        raise HTTPException(status_code=400, detail="free_text_context required")

    extracted = await parse_user_request(query.free_text_context)
    if not extracted or not extracted.name:
        raise HTTPException(status_code=400, detail="Could not extract a usable name from the provided text.")

    name = extracted.name

    data_list = [
        get_mock_linkedin_data(name),
        get_mock_github_data(name),
    ]

    profile = await synthesize_profile(data_list)
    return profile

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)