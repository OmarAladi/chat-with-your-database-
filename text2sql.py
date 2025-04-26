# pip install -qU transformers json-repair==0.29.1
# pip install torch torchvision torchaudio
# pip install huggingface_hub
# huggingface-cli login --token {}

import json
from pydantic import BaseModel, Field
import json_repair
from transformers import AutoModelForCausalLM, AutoTokenizer


class generate_query(BaseModel):
    query: str = Field(..., min_length=5, description="The SQL statement that retrieves.")

def parse_json(text):
    try:
        return json_repair.loads(text)
    except:
        return None

def generate(question, schema):
    sql_guery_generation = [
        {
            "role": "system",
            "content": "\n".join([
                "You are a helpful assistant specialized in converting natural language questions into SQL queries.",
                "You will be provided with an task description containing an SQL table schema and a query question.",
                "Generate the output strictly in JSON, following the provided Pydantic schema.",
                "Extract exactly the fields defined in the schema; do not add, remove, or rename any fields.",
                "Do not include any additional introduction, explanation, or conclusion."
            ])
        },
        {
            "role": "user",
            "content": "\n".join([
                "## Question:",
                question.strip(),
                "",

                "## Schema:",
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
        }
    ]

    base_model_id = "google/gemma-3-1b-it" 
    device = "cuda"
    torch_dtype = None

    model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        device_map="cuda",
        torch_dtype = torch_dtype
    )

    tokenizer = AutoTokenizer.from_pretrained(base_model_id)

    model.load_adapter("OmarAladdin/gemma-3-1b-text2sql")

    text = tokenizer.apply_chat_template(
        sql_guery_generation,
        tokenize=False,
        add_generation_prompt=True
    )

    model_inputs = tokenizer([text], return_tensors="pt").to(device)

    generated_ids = model.generate(
        model_inputs.input_ids,
        max_new_tokens=1024,
        do_sample=False, top_k=None, temperature=None, top_p=None,
    )

    generated_ids = [
        output_ids[len(input_ids):]
        for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]

    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

    return parse_json(response)



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