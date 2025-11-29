from app.tools.csv_loader import load_csv_metadata
from app.tools.pdf_loader import load_pdf
from app.tools.html_table_loader import load_html_tables
from app.tools.scraper import scrape_url
from app.tools.chart_plotter import plot_to_base64

TOOLS = {
    "load_csv_metadata": load_csv_metadata,
    "load_pdf": load_pdf,
    "load_html_tables": load_html_tables,
    "scrape_url": scrape_url,
    "plot_to_base64": plot_to_base64
}

async def execute_tool(tool_name: str, args: dict):
    if tool_name in TOOLS:
        return await TOOLS[tool_name](args)
    return {"error": f"Tool {tool_name} not found."}
