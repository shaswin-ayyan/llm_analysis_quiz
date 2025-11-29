import pdfplumber

async def load_pdf(args):
    """
    Extracts text and tables from a PDF.
    args:
      - path: str
    """
    path = args.get("path")
    if not path:
        return {"error": "No path provided"}
    
    try:
        text_content = []
        tables = []
        
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    text_content.append(f"--- Page {i+1} ---\n{text}")
                
                page_tables = page.extract_tables()
                for tbl in page_tables:
                    tables.append(tbl)
                    
        return {
            "text": "\n".join(text_content),
            "tables": tables
        }
    except Exception as e:
        return {"error": str(e)}
