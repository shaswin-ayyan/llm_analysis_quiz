import pdfplumber
import io
import logging
import pandas as pd
from ..utils.fetch_file import download_bytes

logger = logging.getLogger("uvicorn.error")


class PDFWorker:
    async def parse_pdf(self, url: str) -> str:
        logger.info(f"Downloading PDF {url}")
        data = await download_bytes(url)
        text_chunks = []
        try:
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                for page in pdf.pages:
                    text_chunks.append(page.extract_text() or "")
        except pdfplumber.PDFSyntaxError as e:
            logger.warning(f"pdfplumber failed: {e}")
            # fallback: return raw bytes placeholder
            return data.decode(errors="ignore")[:10000]
        return "\n".join(text_chunks)

    async def extract_tables(self, url: str) -> list[pd.DataFrame]:
        data = await download_bytes(url)
        dfs = []
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for tab in tables:
                    try:
                        df = pd.DataFrame(tab[1:], columns=tab[0])
                        dfs.append(df)
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Error creating DataFrame: {e}")
                        pass
        return dfs
