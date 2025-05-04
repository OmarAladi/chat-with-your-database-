# pip install google-genai
# pip install -qU json-repair
import json
import json_repair
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

class generate_query(BaseModel):
    query: str = Field(..., min_length=5, description="The SQL statement that retrieves.")

def parse_json(text):
    try:
        return json_repair.loads(text)
    except:
        return None

def generate(question, schema):
    client = genai.Client(
        api_key=" "
    )

    model = "gemini-2.5-flash-preview-04-17"

    user_prompt = "\n".join([
        "## Human Question:",
        question.strip(),
        "",

        "## Database Schema:",
        schema.strip(),
        "",

        "## Pydantic Details:",
        json.dumps(
            generate_query.model_json_schema(), ensure_ascii=False
        ),
        "",

        "## Story Details:",
        "```json"

    ])

    system_message = "\n".join([
        "You are a helpful assistant specialized in converting natural language questions into SQL queries.",
        "The user will provide a `Human Question` and a `Database Schema`.",
        "Your task is to generate the corresponding `SQL Query` that correctly answers the question based on the provided schema.",
        "Your output must be a JSON object in the following format:",
        '{"sql": "<GENERATED_SQL_QUERY>"}',
        "Do not include any explanations, comments, or additional text. Only return the JSON object."
    ])

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=user_prompt),
            ],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        response_mime_type="text/plain",
        system_instruction=[
            types.Part.from_text(text=system_message),
        ],
    )

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )
    return parse_json(response.text)

# if __name__ == "__main__":
#     question_2 = "Get a list of all unique cities in the United States, sorted by city name."
#     schema_2 = """
#     CREATE TABLE addresses (
#         address_id INTEGER,
#         line_1 TEXT,
#         line_2 TEXT,
#         line_3 TEXT,
#         city TEXT,
#         zip_postcode TEXT,
#         state_province_county TEXT,
#         country TEXT,
#         other_address_details TEXT
#     )
#     """
#     # query_2 = "SELECT DISTINCT city FROM addresses WHERE country = 'United States' ORDER BY city;"
        
#     query = generate(question_2, schema_2)

#     print(type(query))
#     print("----------------------------------")
#     print(query)
