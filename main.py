from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from schemas import SearchQuery, FinalProfile
from agent import parse_user_request, synthesize_profile
from tools import get_real_github_data, get_phone_number_info

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.post("/search", response_model=FinalProfile)
async def search(query: SearchQuery):
    # Start with user-provided structured data
    params = query.model_dump(exclude_none=True)

    # Run extractor only if free_text_context present
    if query.free_text_context:
        extracted = await parse_user_request(query.free_text_context)
        # Merge while preserving existing user values
        for k, v in extracted.model_dump(exclude_none=True).items():
            params.setdefault(k, v)

    data_list: list = []

    if params.get("username") or params.get("name"):
        target = params.get("username") or params.get("name")
        data_list.append(get_real_github_data(target))

    if params.get("phone"):
        data_list.append(get_phone_number_info(params["phone"]))

    if params.get("location"):
        data_list.append({"source": "user_input", "raw_data": {"location": params["location"]}})

    if not data_list:
        raise HTTPException(status_code=400, detail="Not enough information to run any searches.")

    profile = await synthesize_profile(data_list)
    return profile

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)