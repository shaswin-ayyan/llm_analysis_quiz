import pytest
import pandas as pd
import json
import os
from app.agents.tools import load_data_tool

@pytest.mark.asyncio
async def test_load_data_tool_json():
    # Create a dummy JSON file
    data = [{"col1": 1, "col2": "a"}, {"col1": 2, "col2": "b"}]
    filename = "test_data.json"
    with open(filename, "w") as f:
        json.dump(data, f)
    
    try:
        df = await load_data_tool({"path": filename}, None)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "col1" in df.columns
        assert df.iloc[0]["col1"] == 1
    finally:
        if os.path.exists(filename):
            os.remove(filename)

@pytest.mark.asyncio
async def test_load_data_tool_excel():
    # Create a dummy Excel file
    data = {"col1": [10, 20], "col2": ["x", "y"]}
    df_orig = pd.DataFrame(data)
    filename = "test_data.xlsx"
    df_orig.to_excel(filename, index=False)
    
    try:
        df = await load_data_tool({"path": filename}, None)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "col1" in df.columns
        assert df.iloc[0]["col1"] == 10
    finally:
        if os.path.exists(filename):
            os.remove(filename)

@pytest.mark.asyncio
async def test_load_data_tool_csv():
    # Create a dummy CSV file
    data = "col1,col2\n100,foo\n200,bar"
    filename = "test_data.csv"
    with open(filename, "w") as f:
        f.write(data)
        
    try:
        df = await load_data_tool({"path": filename}, None)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert df.iloc[0]["col1"] == 100
    finally:
        if os.path.exists(filename):
            os.remove(filename)
