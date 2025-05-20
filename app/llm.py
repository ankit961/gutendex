import json
from transformers import pipeline
from app.config import settings

llm_pipeline = None

def get_llm_pipeline():
    global llm_pipeline
    if llm_pipeline is None:
        print(f"Loading LLM model: {settings.LLM_MODEL_PATH}")
        llm_pipeline = pipeline(
            "text-generation",
            model=settings.LLM_MODEL_PATH,    
            device=-1,                       # -1 = CPU, 0 = GPU (if you have CUDA)
            max_new_tokens=128,
            do_sample=True,
            temperature=0.2,                
            repetition_penalty=1.1,
            trust_remote_code=True           # Required for some new models
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
    # Try to extract the JSON block from the generated text
    try:
        json_start = response.index("{")
        json_str = response[json_start:]
        filter_dict = json.loads(json_str)
        return filter_dict
    except Exception as e:
        print(f"Failed to parse filter JSON: {e}\nRaw LLM output: {response}")
        return {}

def summarize_results(query: str, filters: dict, books: list) -> str:
    # Compose a text prompt that gives context to the LLM.
    if not books:
        return "No books matched your criteria."
    book_samples = []
    for b in books[:3]:  # Show up to 3 examples for context.
        title = b.get("title", "")
        authors = ", ".join(a["name"] for a in b.get("authors", [])) or "Unknown author"
        book_samples.append(f"'{title}' by {authors}")
    prompt = (
        f"Given the user query: '{query}' and the following books from the database: "
        f"{'; '.join(book_samples)}. "
        "Write a short summary for the user describing what was found."
    )
    pipe = get_llm_pipeline()
    response = pipe(prompt, max_new_tokens=60)[0]["generated_text"]
    # Postprocess to remove prompt, if needed
    if response.startswith(prompt):
        response = response[len(prompt):]
    return response.strip()

