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
        "Given a user's question about books, output a JSON filter object with keys: author, title, language, topic, mime_type, ids. "
        "Only use relevant keys, leave others out. "
        f"Question: {query}\n"
        "JSON:"
    )
    pipe = get_llm_pipeline()
    response = pipe(prompt, max_new_tokens=80)[0]['generated_text']
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
