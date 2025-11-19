from bs4 import BeautifulSoup
import pandas as pd
import re
from dateutil import parser as date_parser

def _expand_rowspan_colspan(table_soup):
    # Very small best-effort implementation: handle simple colspan/rowspan
    rows = []
    span_map = {}
    trs = table_soup.find_all('tr')
    for r_i, tr in enumerate(trs):
        cols = []
        c_i = 0
        for cell in tr.find_all(['td', 'th']):
            # skip occupied positions
            while span_map.get((r_i, c_i)):
                cols.append(span_map.pop((r_i, c_i)))
                c_i += 1
            text = cell.get_text(strip=True)
            rowspan = int(cell.get('rowspan', 1))
            colspan = int(cell.get('colspan', 1))
            # place text in current and record spans
            cols.append(text)
            for rs in range(rowspan):
                for cs in range(colspan):
                    rr = r_i + rs
                    cc = c_i + cs
                    if rr == r_i and cc == c_i:
                        continue
                    span_map[(rr, cc)] = text
            c_i += colspan
        rows.append(cols)
    return rows

def html_table_to_df(table_html: str) -> pd.DataFrame:
    soup = BeautifulSoup(table_html, 'html.parser')
    table = soup.find('table') or soup
    rows = _expand_rowspan_colspan(table)
    if not rows:
        return pd.DataFrame()
    # treat first row as header if it has ths
    header_candidates = [th.get_text(strip=True) for th in table.find_all('tr')[0].find_all('th')]
    if header_candidates:
        header = header_candidates
        data_rows = rows[1:]
    else:
        header = rows[0]
        data_rows = rows[1:]
    df = pd.DataFrame(data_rows, columns=header)
    return df

def _infer_type(val: str):
    if val is None:
        return None
    v = val.strip()
    if v == '':
        return None
    # numeric
    num = re.sub(r'[,\s]', '', v)
    if re.match(r'^-?\d+(\.\d+)?$', num):
        try:
            if '.' in num:
                return float(num)
            else:
                return int(num)
        except:
            pass
    # date
    try:
        dt = date_parser.parse(v, fuzzy=False)
        return dt
    except:
        pass
    return v

def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df2 = df.copy()
    for col in df2.columns:
        df2[col] = df2[col].astype(str).map(lambda x: x.strip() if x is not None else x)
        # infer types
        df2[col] = df2[col].map(lambda v: _infer_type(v))
    return df2
