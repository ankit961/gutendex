import pytest

@pytest.mark.parametrize("query, expected_keys, expect_results_min, expect_summary", [
    ("Show me English books by Mark Twain about children.", {"author", "language", "topic"}, 0, True),
    ("Books in French by Victor Hugo about love.", {"author", "language", "topic"}, 0, True),
    ("Books by an author that does not exist in my database.", {"author"}, 0, "no books matched"),
    ("", set(), 0, "no books matched"),
])
def test_chat_summary_field(client, query, expected_keys, expect_results_min, expect_summary):
    resp = client.post("/chat", json={"query": query})
    assert resp.status_code == 200
    data = resp.json()
    # summary must be present and a string
    assert "summary" in data
    assert isinstance(data["summary"], str)
    # For queries with expected results, summary should not be empty
    if expect_summary is True and data["results"]:
        assert len(data["summary"].strip()) > 10, f"Summary too short: {data['summary']}"
        # Optionally, check if it mentions some titles or authors in the summary
        for book in data["results"][:1]:  # At least mention title/author
            if "title" in book and book["title"]:
                assert book["title"][:8] in data["summary"], (
                    f"Book title '{book['title']}' not mentioned in summary: {data['summary']}"
                )
    # For queries with no results, summary should say so
    if isinstance(expect_summary, str) and data["count"] == 0:
        assert expect_summary.lower() in data["summary"].lower()

def test_chat_summary_structure(client):
    resp = client.post("/chat", json={"query": "Children's books in Spanish."})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["summary"], str)
    # Should mention either count or title/author
    if data["count"] > 0:
        assert any(key in data["summary"].lower() for key in ["found", "including", "book", "by"]), (
            f"Summary should explain result set: {data['summary']}"
        )
    else:
        assert "no books" in data["summary"].lower()

def test_chat_summary_edge_cases(client):
    # Extremely vague input
    resp = client.post("/chat", json={"query": "asdfghjkl"})
    assert resp.status_code == 200
    data = resp.json()
    # For random noise queries, summary should still be user-friendly
    assert isinstance(data["summary"], str)
    if data["count"] == 0:
        assert "no books" in data["summary"].lower()
