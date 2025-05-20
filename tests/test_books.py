
def test_known_title(client):
    response = client.get("/books?title=kennedy")
    assert response.status_code == 200
    assert any("kennedy" in (b["title"] or "").lower() for b in response.json()["results"])

def test_download_count_field(client):
    response = client.get("/books")
    for b in response.json()["results"]:
        assert isinstance(b["download_count"], int)  

def test_subject_partial(client):
    response = client.get("/books?topic=politics")
    assert response.status_code == 200
    # Should match on bookshelf or subject with "politics"
    for book in response.json()["results"]:
        names = [s["name"].lower() for s in book["subjects"] + book["bookshelves"]]
        assert any("politics" in n for n in names)

def test_language_code(client):
    # Assuming 'en' exists from your dump
    response = client.get("/books?language=en")
    assert response.status_code == 200
    for book in response.json()["results"]:
        codes = [lang["code"] for lang in book["languages"]]
        assert "en" in codes

def test_mime_type_real(client):
    # Should return books with at least one format containing 'text/plain'
    response = client.get("/books?mime_type=text/plain")
    assert response.status_code == 200
    for book in response.json()["results"]:
        mime_types = [f["mime_type"] for f in book["formats"]]
        assert any("text/plain" in mt for mt in mime_types)


def test_author_multi(client):
    # Should work for any known substring of an author from your DB, e.g. "lincoln"
    response = client.get("/books?author=lincoln")
    assert response.status_code == 200
    for b in response.json()["results"]:
        names = [a["name"].lower() for a in b["authors"]]
        assert any("lincoln" in name for name in names)

def test_pagination_skip(client):
    # Get two pages and compare, should not repeat
    page1 = client.get("/books?limit=2&skip=0").json()["results"]
    page2 = client.get("/books?limit=2&skip=2").json()["results"]
    if page1 and page2:
        assert page1[0]["id"] != page2[0]["id"]

def test_multiple_filters_strong(client):
    # Find 'constitution' by author "United States" in English, with "Politics" subject
    response = client.get("/books?title=constitution&author=united&language=en&topic=politics")
    assert response.status_code == 200
    for book in response.json()["results"]:
        assert any("united" in a["name"].lower() for a in book["authors"])
        assert any(l["code"] == "en" for l in book["languages"])
        found = False
        for s in book["subjects"] + book["bookshelves"]:
            if "politics" in s["name"].lower():
                found = True
        assert found

def test_empty_result(client):
    response = client.get("/books?author=zzzxnonexistentxxx")
    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert response.json()["results"] == []

def test_sorting_by_downloads(client):
    response = client.get("/books")
    downloads = [b["download_count"] for b in response.json()["results"]]  
    assert downloads == sorted(downloads, reverse=True)

def test_case_insensitive_title(client):
    response = client.get("/books?title=CONSTITUTION")
    assert response.status_code == 200
    for book in response.json()["results"]:
        assert "constitution" in (book["title"] or "").lower()

def test_combined_languages(client):
    # Assume your DB has books in 'en' and 'fr'
    response = client.get("/books?language=en&language=fr")
    assert response.status_code == 200
    for book in response.json()["results"]:
        codes = [lang["code"] for lang in book["languages"]]
        assert "en" in codes or "fr" in codes

def test_invalid_limit_param(client):
    response = client.get("/books?limit=notanumber")
    assert response.status_code == 422  # Unprocessable Entity

def test_missing_param_values(client):
    response = client.get("/books?author=&title=")
    assert response.status_code == 200  # Should not crash or error


def test_subject_case_insensitive(client):
    response = client.get("/books?topic=POLITICS")
    assert response.status_code == 200
    for book in response.json()["results"]:
        found = False
        for s in book["subjects"] + book["bookshelves"]:
            if "politics" in s["name"].lower():
                found = True
        assert found

def test_download_links_exist(client):
    response = client.get("/books")
    for book in response.json()["results"]:
        assert isinstance(book["formats"], list)
        for f in book["formats"]:
            assert "url" in f and isinstance(f["url"], str)

