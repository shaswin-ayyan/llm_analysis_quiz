import pandas as pd

async def load_html_tables(args):
    """
    Extracts tables from an HTML file.
    args:
      - path: str
    """
    path = args.get("path")
    if not path:
        return {"error": "No path provided"}
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
            
        dfs = pd.read_html(html)
        tables = []
        for i, df in enumerate(dfs):
            tables.append({
                "table_index": i,
                "columns": list(df.columns),
                "data": df.head(5).to_dict(orient="records"),
                "full_data_summary": f"{len(df)} rows"
            })
            
        return {"tables": tables}
    except Exception as e:
        return {"error": str(e)}
