import json
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
from app.config import settings
import torch

llm_pipeline = None

def get_llm_pipeline():
    global llm_pipeline
    if llm_pipeline is None:
        print(f"Loading LLM model: {settings.LLM_MODEL_PATH}")
        tokenizer = AutoTokenizer.from_pretrained(settings.LLM_MODEL_PATH, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            settings.LLM_MODEL_PATH,
            trust_remote_code=True,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
        )
        llm_pipeline = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            device=0 if torch.cuda.is_available() else -1,
            max_new_tokens=128,
            do_sample=True,
            temperature=0.2,
            repetition_penalty=1.1
        )
    return llm_pipeline

def query_to_filter(query: str) -> dict:
    prompt = (
        "You are generating a JSON filter for a books database. "
        "IMPORTANT: Only use the following exact database field names in your output: "
        "'author', 'title', 'language', 'topic', 'mime_type', 'ids', 'sort', 'limit'.\n\n"
        "Field definitions:\n"
        "  - author: string (e.g., 'Austen, Jane')\n"
        "  - title: string (e.g., 'Pride and Prejudice')\n"
        "  - language: list of language codes (e.g., ['en'])\n"
        "  - topic: string (e.g., 'Love stories')\n"
        "  - mime_type: string (e.g., 'text/plain; charset=utf-8')\n"
        "  - ids: list of integers (e.g., [1342])\n"
        "  - sort: string for sorting results (e.g., 'download_count:desc')\n"
        "  - limit: integer to restrict the number of results (e.g., 1)\n\n"
        "Allowed keys in your JSON: author, title, language, topic, mime_type, ids, sort, limit.\n"
        "ONLY include a key if the user query directly mentions that field. Do not infer, guess, or add values from context. "
        "Output must be exactly valid JSON with no extra text and no additional keys. "
        "For example, if the user only mentions a title, the JSON filter should only contain the 'title' key. "
        "If the user asks for 'most downloaded', 'latest', or similar, include the 'sort' key using the exact field name 'download_count' (e.g., 'sort': 'download_count:desc') and 'limit' if specified. "
        "DO NOT invent or add any values that are not explicitly mentioned in the query. "
        "Use language codes (e.g., 'en') not full language names. "
        "If the query is general or ambiguous, return an empty JSON object {}.\n\n"
        "Example: For the query 'how many books titled Pride and Prejudice', the output should be:\n"
        "{\"title\": \"Pride and Prejudice\"}\n\n"
        f"Question: {query}\n"
        "JSON:"
    )
    pipe = get_llm_pipeline()
    response = pipe(prompt, max_new_tokens=100)[0]['generated_text']
    try:
        json_start = response.index("{")
        json_str = response[json_start:]
        # Try to trim to the last closing bracket
        last_brace = max(json_str.rfind("}"), json_str.rfind("]"))
        if last_brace != -1:
            json_str = json_str[:last_brace+1]
        filter_dict = json.loads(json_str)
        return filter_dict
    except Exception as e:
        print(f"Failed to parse filter JSON: {e}\nRaw LLM output: {response}")
        return {}

def summarize_results(query: str, filters: dict, books: list) -> str:
    if not books:
        return "No books matched your criteria."
    book_samples = []
    for b in books[:3]:
        title = getattr(b, "title", "")
        authors = ", ".join(getattr(a, "name", "Unknown author") for a in getattr(b, "authors", [])) or "Unknown author"
        book_samples.append(f"'{title}' by {authors}")
    prompt = (
        f"Given the user query: '{query}' and the following books from the database: "
        f"{'; '.join(book_samples)}. "
        "Write a short summary for the user describing what was found."
    )
    pipe = get_llm_pipeline()
    summary = pipe(prompt, max_new_tokens=60)[0]["generated_text"].strip()
    # Fallback if LLM output is empty or too short
    if not summary or len(summary) < 10:
        summary = f"Found {len(books)} books including {book_samples[0]}." if books else "No books matched your criteria."
    return summary
