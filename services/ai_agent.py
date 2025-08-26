import json
from dotenv import load_dotenv
from schemas import SearchQuery, FinalProfile
from services.llm import get_gemini_model

load_dotenv()


async def parse_user_request(text: str) -> SearchQuery:
    model = get_gemini_model(model_name="gemini-2.5-flash")
    if model is None:
        return SearchQuery()
    prompt = f"""
    You are a highly intelligent data extraction API. Your sole purpose is to convert a user's free-text query into a structured JSON object.

    The JSON object must strictly adhere to the following schema.
    You MUST use the exact key names defined in the schema.
    Do not add any extra keys. If a piece of information is not found, its value must be null.
    Any deviation from this schema will result in a failure.

    Schema:
    {{
        "name": "string",
        "email": "string",
        "phone": "string",
        "username": "string",
        "location": "string",
        "free_text_context": "string"
    }}

    Example:
    User Query: "Can you find the guy named John Doe? I heard he goes by @johndoeonline and he's a senior engineer working on AI stuff, maybe based out of San Francisco."
    JSON Output:
    {{
        "name": "John Doe",
        "email": null,
        "phone": null,
        "username": "@johndoeonline",
        "location": "San Francisco",
        "free_text_context": "senior engineer working on AI stuff"
    }}

    Now, parse the following user query:

    User Query: "{text}"
    """
    
    try:
        response = await model.generate_content_async(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        print("----------- EXTRACTOR LLM RESPONSE TEXT -----------")
        print(response.text)
        print("-------------------------------------------------")
        return SearchQuery.model_validate_json(response.text)
    except Exception:
        return SearchQuery()


async def synthesize_profile(data_list: list) -> FinalProfile:
    model = get_gemini_model(model_name="gemini-2.5-flash", tools={
        "function_declarations": [
            {
                "name": "submit_final_profile",
                "description": "Submit the final synthesized profile after processing data from multiple sources.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "full_name": {"type": "STRING"},
                        "summary": {"type": "STRING"},
                        "locations": {"type": "ARRAY", "items": {"type": "STRING"}},
                        "employment_history": {"type": "ARRAY", "items": {"type": "OBJECT"}},
                    },
                    "required": ["full_name", "summary", "locations", "employment_history"]
                },
            }
        ]
    })
    if model is None:
        name = None
        locations = []
        for item in data_list:
            raw = item.get("raw_data") or {}
            if not name:
                name = raw.get("name") or raw.get("full_name") or raw.get("username")
            loc = raw.get("location") or raw.get("locations")
            if isinstance(loc, str):
                locations.append(loc)
            elif isinstance(loc, list):
                locations.extend([str(x) for x in loc])
        full_name = name or "Unknown"
        summary = "Consolidated profile from available sources."
        return FinalProfile(full_name=full_name, summary=summary, locations=list(dict.fromkeys(locations)), employment_history=[])
    prompt = f"""
    You are an expert intelligence analyst. Your job is to synthesize messy data points from multiple sources into a single, coherent profile.

    Review the following raw data about a person. **Based on all the provided data, you MUST generate a concise, 1-2 sentence summary for the 'summary' field.**

    After reasoning about the data, you MUST call the `submit_final_profile` tool to output the consolidated profile.
    
    Raw Data:
    {json.dumps(data_list, indent=2)}
    """

    try:
        response = await model.generate_content_async(prompt)
        function_call = response.candidates[0].content.parts[0].function_call
        if function_call.name == "submit_final_profile":
            args = {key: value for key, value in function_call.args.items()}
            return FinalProfile.model_validate(args)
        raise ValueError("Model did not call the expected 'submit_final_profile' tool.")
    except Exception as e:
        raise ValueError(f"Failed to synthesize profile. Error: {e}")
