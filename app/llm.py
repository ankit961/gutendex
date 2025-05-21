import json
import logging
from typing import Dict, Any, List
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
from app.config import settings
import torch
from threading import Lock

# Thread-safe singleton for LLM pipeline
_llm_pipeline = None
_llm_lock = Lock()

def get_llm_pipeline():
    """
    Loads and returns the LLM pipeline for text generation.
    Uses global caching and locking to avoid reloading the model on every call.
    """
    global _llm_pipeline
    with _llm_lock:
        if _llm_pipeline is None:
            tokenizer = AutoTokenizer.from_pretrained(settings.LLM_MODEL_PATH, trust_remote_code=True)
            model = AutoModelForCausalLM.from_pretrained(
                settings.LLM_MODEL_PATH,
                trust_remote_code=True,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
            )
            _llm_pipeline = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                device=0 if torch.cuda.is_available() else -1,
                max_new_tokens=128,
                do_sample=True,
                temperature=0.2,
                repetition_penalty=1.1
            )
    return _llm_pipeline

def extract_explicit_keys(query: str, allowed: List[str]) -> List[str]:
    """
    Returns a list of allowed keys that are explicitly mentioned in the query.
    """
    query_lower = query.lower()
    return [k for k in allowed if k in query_lower]

def query_to_filter(query: str) -> Dict[str, Any]:
    """
    Converts a user query string into a JSON filter for the books database using the LLM.
    The prompt is designed to minimize hallucination and ensure only explicitly mentioned fields are included.
    Returns a dictionary suitable for filtering the database.
    """
    allowed_keys = ['author', 'title', 'language', 'topic', 'mime_type', 'ids', 'sort', 'limit']
    prompt = (
        "You are an expert assistant for generating JSON filters for a books database API.\n\n"
        "Your task is to convert a user's natural language question into a JSON object that can be used to filter a books database. "
        "The JSON must use only the allowed keys and must not include any extra keys or inferred values.\n"
        "--------------------\n"
        "ALLOWED KEYS & FORMATS:\n"
        "- author: string (e.g., \"Austen, Jane\")\n"
        "- title: string (e.g., \"Pride and Prejudice\")\n"
        "- language: list of ISO 639-1 codes (e.g., [\"en\"], [\"fr\"])\n"
        "- topic: string (e.g., \"adventure\", \"Love stories\")\n"
        "- mime_type: string (e.g., \"text/plain; charset=utf-8\", \"application/pdf\")\n"
        "- ids: list of integers (e.g., [1342])\n"
        "- sort: string for sorting results (e.g., \"download_count:desc\", \"latest\")\n"
        "- limit: integer (e.g., 1, 5, 10)\n"
        "--------------------\n"
        "STRICT RULES:\n"
        "- Only include a key if the user query **explicitly mentions** it.\n"
        "- Do NOT infer, guess, or add values from context, prior knowledge, or the title.\n"
        "- Do NOT include any key or value unless it is directly stated in the query.\n"
        "- Use language codes (e.g., \"en\"), not full language names.\n"
        "- If the user asks for \"most downloaded\", \"top\", or \"latest\", use the 'sort' key (e.g., \"sort\": \"download_count:desc\" or \"sort\": \"latest\") and 'limit' if a number is specified.\n"
        "- If the user asks for a specific number of results, use the 'limit' key.\n"
        "- If the user asks for a specific book by id, use the 'ids' key with a list of integers.\n"
        "- If the query is general or ambiguous, return an empty JSON object {}.\n"
        "- Output **must be valid JSON only** with no extra text, comments, or explanations.\n"
        "--------------------\n"
        "POSITIVE EXAMPLES:\n"
        "Q: how many books titled Pride and Prejudice\n"
        "A: {\"title\": \"Pride and Prejudice\"}\n\n"
        "Q: Most Downloaded book\n"
        "A: {\"sort\": \"download_count:desc\", \"limit\": 1}\n\n"
        "Q: List top 3 most downloaded French books\n"
        "A: {\"language\": [\"fr\"], \"sort\": \"download_count:desc\", \"limit\": 3}\n\n"
        "Q: Books by Mark Twain about adventure\n"
        "A: {\"author\": \"Mark Twain\", \"topic\": \"adventure\"}\n\n"
        "Q: Give me books in Spanish\n"
        "A: {\"language\": [\"es\"]}\n\n"
        "Q: Show me books with mime type text/html\n"
        "A: {\"mime_type\": \"text/html\"}\n\n"
        "Q: Find book with id 1342\n"
        "A: {\"ids\": [1342]}\n\n"
        "Q: List 10 latest books\n"
        "A: {\"sort\": \"latest\", \"limit\": 10}\n\n"
        "Q: Give me all books\n"
        "A: {}\n\n"
        "Q: Show me 5 books by Agatha Christie in English, sorted by most downloaded\n"
        "A: {\"author\": \"Agatha Christie\", \"language\": [\"en\"], \"sort\": \"download_count:desc\", \"limit\": 5}\n\n"
        "Q: Show me books about science fiction in French\n"
        "A: {\"topic\": \"science fiction\", \"language\": [\"fr\"]}\n"
        "--------------------\n"
        "NEGATIVE EXAMPLES (DO NOT DO THIS):\n"
        "Incorrect: (query only mentions title, but LLM adds extra fields)\n"
        "{\n"
        "  \"author\": \"Austen, Jane\",\n"
        "  \"title\": \"Pride and Prejudice\",\n"
        "  \"language\": [\"en\"],\n"
        "  \"topic\": [\"Love stories\"],\n"
        "  \"mime_type\": \"text/plain; charset=utf-8\",\n"
        "  \"ids\": [1342],\n"
        "  \"sort\": \"download_count:desc\",\n"
        "  \"limit\": 5\n"
        "}\n\n"
        "Incorrect: (query is ambiguous, but LLM guesses fields)\n"
        "{\n"
        "  \"author\": \"Unknown\",\n"
        "  \"language\": [\"en\"]\n"
        "}\n\n"
        "Incorrect: (query is general, but LLM adds keys)\n"
        "{\n"
        "  \"sort\": \"download_count:desc\"\n"
        "}\n"
        "--------------------\n"
        "EDGE CASES:\n"
        "- If the user says \"any book\", \"all books\", or is vague, return {}.\n"
        "- If the user says \"top 5\", use \"limit\": 5 and \"sort\": \"download_count:desc\".\n"
        "- If the user says \"latest\", use \"sort\": \"latest\" and \"limit\" if a number is given.\n"
        "- If the user says \"books by id 123, 456\", use \"ids\": [123, 456].\n"
        "- If the user says \"books in English and French\", use \"language\": [\"en\", \"fr\"].\n"
        "--------------------\n"
        "If you are unsure, return {}.\n"
        "--------------------\n"
        f"Question: {query}\n"
        "JSON:"
    )
    pipe = get_llm_pipeline()
    response = pipe(prompt, max_new_tokens=180)[0]['generated_text']
    try:
        # Extract the JSON object from the LLM output
        json_start = response.index("{")
        json_str = response[json_start:]
        last_brace = max(json_str.rfind("}"), json_str.rfind("]"))
        if last_brace != -1:
            json_str = json_str[:last_brace+1]
        filter_dict = json.loads(json_str)
        # Post-process: remove keys not explicitly mentioned in the query (except sort/limit)
        explicit_keys = extract_explicit_keys(query, allowed_keys)
        filter_dict = {k: v for k, v in filter_dict.items() if k in explicit_keys or k in ['sort', 'limit']}
        return filter_dict
    except Exception as e:
        logging.error(f"Failed to parse filter JSON: {e}\nRaw LLM output: {response}")
        return {}

def summarize_results(query: str, filters: dict, books: list) -> str:
    """
    Generates a short summary of the search results using the LLM.
    If no books are found, returns a default message.
    """
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
    if not summary or len(summary) < 10:
        summary = f"Found {len(books)} books including {book_samples[0]}." if books else "No books matched your criteria."
    return summary
