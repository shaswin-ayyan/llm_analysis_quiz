from app.agents.tools.definitions import (
    load_csv_metadata,
    load_excel_metadata,
    load_json_metadata,
    load_pdf,
    load_html_tables,
    python_execute,
    plot_to_base64,
    extract_urls_tool,
    scrape_url_tool
)

VALID_TOOLS = {
    "load_csv_metadata": load_csv_metadata,
    "load_excel_metadata": load_excel_metadata,
    "load_json_metadata": load_json_metadata,
    "load_pdf": load_pdf,
    "load_html_tables": load_html_tables,
    "python_execute": python_execute,
    "plot_to_base64": plot_to_base64,
    "extract_urls": extract_urls_tool,
    "scrape_url": scrape_url_tool,
}
