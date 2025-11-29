from app.utils.url_utils import extract_urls

def test_extract_urls_absolute():
    text = 'Check this <a href="https://example.com">link</a> and https://google.com'
    urls = extract_urls(text)
    assert "https://example.com" in urls
    assert "https://google.com" in urls

def test_extract_urls_relative():
    text = '<a href="/path/to/resource">link</a>'
    base_url = "https://example.com"
    urls = extract_urls(text, base_url=base_url)
    assert "https://example.com/path/to/resource" in urls

def test_extract_urls_relative_no_base():
    text = '<a href="/path/to/resource">link</a>'
    urls = extract_urls(text)
    # Should return relative URL as is if no base_url
    assert "/path/to/resource" in urls
