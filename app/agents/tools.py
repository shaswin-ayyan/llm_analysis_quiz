# app/agents/tools.py

import pandas as pd
import aiohttp
from io import StringIO
from urllib.parse import urlparse

from app.utils.parse_table import html_table_to_df, normalize_dataframe


# ============================================================
# LOAD CSV TOOL (CLEAN + CONSISTENT)
# ============================================================
async def load_csv_tool(args, df):
    """
    Accepted keys: file_path, url, path, dataset, file, csv_path
    """
    file_path = (
        args.get("file_path")
        or args.get("url")
        or args.get("path")
        or args.get("dataset")
        or args.get("file")
        or args.get("csv_path")
    )

    if not file_path:
        raise ValueError("load_csv requires file_path")

    parsed = urlparse(file_path)
    is_url = parsed.scheme in ("http", "https")

    if is_url:
        async with aiohttp.ClientSession() as session:
            async with session.get(file_path) as resp:
                raw = await resp.text()

        if "<html" in raw.lower():
            html_df = html_table_to_df(raw)
            html_df = normalize_dataframe(html_df)
            if not html_df.empty:
                return html_df
            raise RuntimeError(
                f"Expected CSV but got HTML. URL: {file_path}\nPreview: {raw[:200]!r}"
            )

        try:
            return pd.read_csv(StringIO(raw))
        except Exception as e:
            raise RuntimeError(
                f"Failed to parse CSV from URL: {file_path}\nReason: {e}"
            )

    # Local
    try:
        return pd.read_csv(file_path)
    except Exception as e:
        # Last-ditch attempt: treat the file as HTML and parse tables
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as handle:
                raw = handle.read()
            if "<html" in raw.lower():
                html_df = html_table_to_df(raw)
                html_df = normalize_dataframe(html_df)
                if not html_df.empty:
                    return html_df
        except Exception:
            pass
        raise RuntimeError(f"Failed to read local CSV '{file_path}': {e}")


# ============================================================
# CORRELATION TOOL — Standardized args
# ============================================================
async def correlation_tool(args, df):
    """
    args:
      - column_x: str
      - column_y: str
      - group_by: str (optional)
    """
    if df is None:
        raise ValueError("correlation_tool: df is None")

    x = args.get("column_x")
    y = args.get("column_y")
    by = args.get("group_by")

    if not x or not y:
        raise ValueError("correlation_tool requires column_x and column_y")

    if by:
        result = {}
        for group_name, gdf in df.groupby(by):
            try:
                result[group_name] = float(gdf[x].corr(gdf[y]))
            except Exception:
                result[group_name] = None
        return result

    return float(df[x].corr(df[y]))


# ============================================================
# SUMMARY STATS TOOL — Standardized
# ============================================================
async def summary_stats_tool(args, df):
    """
    args:
      - column: optional
      - group_by: optional
    """
    if df is None:
        raise ValueError("summary_stats_tool: df is None")

    col = args.get("column")
    by = args.get("group_by")

    if by:
        return df.groupby(by).describe().to_dict()

    if col:
        return df[col].describe().to_dict()

    return df.describe().to_dict()


# ============================================================
# TOP GROUP BY TOOL — Standardized args
# ============================================================
async def top_group_by_tool(args, df):
    """
    args:
      - group_by: str
      - value_col: str
      - n: int
    """
    if df is None:
        raise ValueError("top_group_by_tool: df is None")

    by = args.get("group_by")
    col = args.get("value_col")
    n = args.get("n", 5)

    if not by or not col:
        raise ValueError("top_group_by_tool requires group_by and value_col")

    if by not in df.columns:
        raise ValueError(f"Column '{by}' not in dataframe")

    if col not in df.columns:
        raise ValueError(f"Column '{col}' not in dataframe")

    grouped = (
        df.groupby(by)[col]
        .sum()
        .sort_values(ascending=False)
        .head(int(n))
        .to_dict()
    )

    return grouped


# ============================================================
# FILTER TOOL — Hardened
# ============================================================
async def filter_tool(args, df):
    """
    args:
      - column: str
      - op: one of > < >= <= == !=
      - value: number or string
    """
    if df is None:
        raise ValueError("filter_tool: df is None")

    column = args.get("column")
    op = args.get("op")
    value = args.get("value")

    if not column or op is None or value is None:
        raise ValueError("filter_tool requires column, op, value")

    if column not in df.columns:
        raise ValueError(f"Column '{column}' not in dataframe")

    operators = {
        ">": df[column] > value,
        "<": df[column] < value,
        ">=": df[column] >= value,
        "<=": df[column] <= value,
        "==": df[column] == value,
        "!=": df[column] != value,
    }

    if op not in operators:
        raise ValueError(f"Invalid operator '{op}'")

    return df[operators[op]]
