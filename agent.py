import os
import json
from dotenv import load_dotenv
import google.generativeai as genai
from schemas import SearchQuery, FinalProfile

# --- Configuration (Done once at the module level) ---
# Load environment variables from .env file
load_dotenv()

# Configure the Gemini API key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY not set in environment. Please check your .env file.")
genai.configure(api_key=api_key)


# --- Agent Functions ---

async def parse_user_request(text: str) -> SearchQuery:
    """
    Uses Gemini to parse a user's free-text request into a structured SearchQuery object.
    This is the "Extractor" agent.
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    # This is the "hardened" prompt specifically for extracting entities from user text.
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
        
        # Print for debugging, then parse the validated JSON
        print("----------- EXTRACTOR LLM RESPONSE TEXT -----------")
        print(response.text)
        print("-------------------------------------------------")
        
        return SearchQuery.model_validate_json(response.text)
        
    except Exception as e:
        print(f"An error occurred during the Extractor API call: {e}")
        return SearchQuery()  # Return an empty object on failure


async def synthesize_profile(data_list: list) -> FinalProfile:
    """
    Uses Gemini Tool Calling to synthesize data from multiple sources into a final profile.
    This is the "Synthesizer" agent.
    """
    
    # This defines the 'submit_final_profile' tool that the LLM can call.
    tools = {
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
    }

    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        tools=tools,
    )

    # This is the CORRECT prompt for the Synthesizer's job.
    prompt = f"""
    You are an expert intelligence analyst. Your job is to synthesize messy data points from multiple sources into a single, coherent profile.

    Review the following raw data about a person. **Based on all the provided data, you MUST generate a concise, 1-2 sentence summary for the 'summary' field.**

    After reasoning about the data, you MUST call the `submit_final_profile` tool to output the consolidated profile.
    
    Raw Data:
    {json.dumps(data_list, indent=2)}
    """

    try:
        response = await model.generate_content_async(prompt)

        # A direct and safe way to access the function call from the response
        function_call = response.candidates[0].content.parts[0].function_call
        
        if function_call.name == "submit_final_profile":
            # The model has called our tool, now we get the arguments it provided
            args = {key: value for key, value in function_call.args.items()}
            # Validate the arguments against our Pydantic schema and return
            return FinalProfile.model_validate(args)
        else:
            # The model responded but didn't call the right tool
            raise ValueError("Model did not call the expected 'submit_final_profile' tool.")

    except (AttributeError, IndexError, Exception) as e:
        print("----------- RAW SYNTHESIZER RESPONSE (ERROR) -----------")
        print(response) # Print the response to see why it failed
        print("------------------------------------------------------")
        # Handle cases where no function call is present or another error occurs
        raise ValueError(f"Failed to synthesize profile. Error: {e}")