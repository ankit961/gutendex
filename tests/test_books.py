def test_no_filters_returns_25(client):
    response = client.get("/books")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= len(data["results"])
    assert len(data["results"]) <= 25
    for book in data["results"]:
        assert "id" in book
        assert "title" in book
        assert "downloads" in book

def test_language_filter(client):
    response = client.get("/books?language=en")
    assert response.status_code == 200
    for book in response.json()["results"]:
        codes = [lang["code"] for lang in book["languages"]]
        assert "en" in codes

def test_multiple_languages(client):
    response = client.get("/books?language=en&language=fr")
    assert response.status_code == 200
    for book in response.json()["results"]:
        codes = [lang["code"] for lang in book["languages"]]
        assert "en" in codes or "fr" in codes

def test_author_partial_match(client):
    response = client.get("/books?author=lincoln")
    assert response.status_code == 200
    for book in response.json()["results"]:
        authors = [a["name"].lower() for a in book["authors"]]
        assert any("lincoln" in name for name in authors)

def test_title_partial_match(client):
    response = client.get("/books?title=address")
    assert response.status_code == 200
    for book in response.json()["results"]:
        assert "address" in (book["title"] or "").lower()

def test_topic_subject_partial_match(client):
    response = client.get("/books?topic=education")
    assert response.status_code == 200
    if response.json()["results"]:
        found = False
        for book in response.json()["results"]:
            subjects = [s["name"].lower() for s in book["subjects"]]
            bookshelves = [s["name"].lower() for s in book["bookshelves"]]
            if any("education" in s for s in subjects + bookshelves):
                found = True
        assert found, "No books found with 'education' in subject or bookshelf"

def test_bookshelf_partial_match(client):
    response = client.get("/books?topic=children")
    assert response.status_code == 200
    if response.json()["results"]:
        found = False
        for book in response.json()["results"]:
            bookshelves = [s["name"].lower() for s in book["bookshelves"]]
            if any("children" in shelf for shelf in bookshelves):
                found = True
        assert found, "No books found with 'children' in bookshelf"


def test_mime_type_filter(client):
    response = client.get("/books?mime_type=text/plain")
    assert response.status_code == 200
    for book in response.json()["results"]:
        mime_types = [f["mime_type"] for f in book["formats"]]
        assert any("text/plain" in mt for mt in mime_types)

def test_id_filter(client):
    # Use a real book id from your DB; here, we just pick 1 for example.
    response = client.get("/books?ids=1")
    assert response.status_code == 200
    if response.json()["results"]:  # Book may not exist in dump!
        assert response.json()["results"][0]["id"] == 1

def test_pagination(client):
    r1 = client.get("/books?limit=1&skip=0")
    r2 = client.get("/books?limit=1&skip=1")
    assert r1.status_code == 200 and r2.status_code == 200
    # Only compare if both have at least 1 result
    if r1.json()["results"] and r2.json()["results"]:
        assert r1.json()["results"][0]["id"] != r2.json()["results"][0]["id"]

def test_multiple_filters(client):
    response = client.get("/books?author=lincoln&language=en&topic=address")
    assert response.status_code == 200
    for book in response.json()["results"]:
        assert any("lincoln" in a["name"].lower() for a in book["authors"])
        assert any(l["code"] == "en" for l in book["languages"])
        found = False
        for s in book["subjects"] + book["bookshelves"]:
            if "address" in s["name"].lower():
                found = True
        assert found

def test_not_found(client):
    response = client.get("/books?author=zzzxnonexistentxxx")
    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert response.json()["results"] == []

def test_downloads_sorted(client):
    # Checks that results are sorted by downloads descending
    response = client.get("/books")
    assert response.status_code == 200
    results = response.json()["results"]
    downloads = [b["downloads"] or 0 for b in results]
    assert downloads == sorted(downloads, reverse=True)

def test_invalid_params_handling(client):
    response = client.get("/books?limit=abc")
    assert response.status_code == 422  # Unprocessable Entity for invalid param type

def test_title_case_insensitive(client):
    # Should match titles regardless of case
    response = client.get("/books?title=CONSTITUTION")
    assert response.status_code == 200
    for book in response.json()["results"]:
        assert "constitution" in (book["title"] or "").lower()
