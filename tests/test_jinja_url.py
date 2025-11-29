import pytest
import os
from jinja2 import Environment, FileSystemLoader
from app.utils.url_utils import extract_urls

# ============================================================
# Test Jinja2 Prompts
# ============================================================

def test_jinja2_prompts_rendering():
    prompt_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "prompts")
    jinja_env = Environment(loader=FileSystemLoader(prompt_dir))
    
    # Test base_prompt.j2
    base_template = jinja_env.get_template("base_prompt.j2")
    rendered = base_template.render(
        user_payload='{"question": "test"}',
        allowed_columns="col1, col2",
        data_profile='{"columns": ["col1", "col2"]}'
    )
    assert "SYSTEM: You are a SENIOR DATA SCIENTIST" in rendered
    assert "col1, col2" in rendered
    assert '{"columns": ["col1", "col2"]}' in rendered

    # Test repair_json.j2
    repair_template = jinja_env.get_template("repair_json.j2")
    rendered_repair = repair_template.render(
        bad_output="bad json",
        allowed_columns="col1"
    )
    assert "bad json" in rendered_repair
    assert "col1" in rendered_repair

# ============================================================
# Test URL Utils
# ============================================================

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
