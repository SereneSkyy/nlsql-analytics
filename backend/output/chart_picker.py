import pandas as pd

def _looks_like_date(series) -> bool:
    try:
        pd.to_datetime(series, errors="raise")
        return True
    except Exception:
        return False

def pick_chart(df: pd.DataFrame) -> dict:
    """Look at the shape of a result set and decide what chart (if any) makes
    sense. Returns a description of chart type + columns to use; actual
    rendering happens in the frontend. Deliberately rule-based rather than
    LLM-based -- chart choice from result shape doesn't need a model call,
    and staying rule-based means this never costs quota or can hallucinate."""
    if df is None or df.empty:
        return {"chart_type": "none"}

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    datetime_cols = df.select_dtypes(include="datetime").columns.tolist()
    if not datetime_cols:
        for col in df.columns:
            if col not in numeric_cols and _looks_like_date(df[col]):
                datetime_cols.append(col)

    categorical_cols = [c for c in df.columns if c not in numeric_cols and c not in datetime_cols]

    # Single row, single numeric value -> big number metric
    if len(df) == 1 and len(numeric_cols) == 1 and len(df.columns) <= 2:
        return {
            "chart_type": "metric",
            "value_col": numeric_cols[0],
            "label_col": categorical_cols[0] if categorical_cols else None,
        }

    # A real date/time column plus a number -> line chart (trend over time)
    if datetime_cols and numeric_cols:
        return {"chart_type": "line", "x_col": datetime_cols[0], "y_col": numeric_cols[0]}

    # Two numeric columns (e.g. year, revenue) -> treat first as the axis
    if len(numeric_cols) >= 2 and len(df) > 1:
        return {"chart_type": "bar", "x_col": numeric_cols[0], "y_col": numeric_cols[1]}

    # One category + one number, multiple rows -> bar chart
    if categorical_cols and numeric_cols and len(df) > 1:
        return {"chart_type": "bar", "x_col": categorical_cols[0], "y_col": numeric_cols[0]}

    return {"chart_type": "none"}
