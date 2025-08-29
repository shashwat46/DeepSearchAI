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
    import os
    model_name = os.getenv("GEMINI_SYNTHESIS_MODEL", "gemini-2.5-pro")
    model = get_gemini_model(model_name=model_name, tools={
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
You are an intelligence analyst. Produce a single coherent person profile from structured tool outputs.

Rules:
- Use only stated facts from the inputs. Do not hallucinate or infer missing data.
- Prefer higher-confidence sources in case of conflicts: LinkedIn-Verify > GitHub > ESPY > others.
- Derive full_name from verified fields when available (e.g., LinkedIn-Verify.name), else best available name/username.
- Summary must be 1–2 sentences, factual, and source-neutral (no mentions of tools).
- Locations should be unique, human-readable strings from inputs only.
- Employment history should be an array; include only fields explicitly present in inputs.
- If a field is unknown, leave it out of employment entries.
- After reasoning, you MUST call submit_final_profile with fields: full_name, summary, locations, employment_history.

Inputs (JSON):
{json.dumps(data_list, indent=2)}
"""

    # Try up to 2 attempts, then fallback to heuristic synthesis
    last_err = None
    for _ in range(2):
        try:
            response = await model.generate_content_async(prompt)
            # Defensive parse: prefer function_call, else parse JSON in text
            try:
                function_call = response.candidates[0].content.parts[0].function_call
                if function_call and getattr(function_call, 'name', '') == "submit_final_profile":
                    args = {key: value for key, value in function_call.args.items()}
                    return FinalProfile.model_validate(args)
            except Exception:
                pass
            # Fallback: attempt JSON parse of response.text
            try:
                text_obj = json.loads(getattr(response, 'text', '') or '{}')
                if isinstance(text_obj, dict):
                    return FinalProfile.model_validate({
                        "full_name": text_obj.get("full_name") or text_obj.get("name") or "Unknown",
                        "summary": text_obj.get("summary") or "Consolidated profile from available sources.",
                        "locations": text_obj.get("locations") or [],
                        "employment_history": text_obj.get("employment_history") or [],
                    })
            except Exception:
                pass
            raise ValueError("Model did not return expected tool call or JSON.")
        except Exception as e:
            last_err = e
            continue

    # Heuristic fallback: derive minimal profile without failing the endpoint
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


async def generate_search_hint(context: str) -> str:
    model = get_gemini_model(model_name="gemini-2.5-flash")
    if model is None or not context:
        return ""
    prompt = f"""
You extract one short hint (<=50 chars) from the text that can uniquely help find a person's public profiles. Prefer proper nouns like employer, university, project, or certification. Avoid generic roles or buzzwords. Return only the hint string, no quotes, no extra text.

Text:\n{context}
"""
    try:
        resp = await model.generate_content_async(prompt)
        hint = (resp.text or "").strip().strip("\"'")
        if len(hint) > 50:
            hint = hint[:50]
        return hint
    except Exception:
        return ""
