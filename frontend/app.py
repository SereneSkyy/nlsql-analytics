import streamlit as st
import requests
import pandas as pd
import plotly.express as px

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="NL-to-SQL Analytics", layout="wide")
st.title("NL-to-SQL Analytics Tool")
st.caption("Ask a business question about the Pagila (DVD rental) database in plain English.")

question = st.text_input("Your question", placeholder="e.g. Who are the top 5 customers by total amount spent?")

if st.button("Ask", type="primary") and question:
    with st.spinner("Generating SQL and running query..."):
        try:
            response = requests.post(f"{API_URL}/ask", json={"question": question}, timeout=60)
            response.raise_for_status()
            result = response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Could not reach the backend: {e}")
            st.stop()

    if not result.get("is_valid"):
        st.error("The generated SQL did not pass validation.")
        st.code(result.get("sql", ""), language="sql")
        for err in result.get("errors", []):
            st.write(f"- {err}")
        if len(result.get("attempts", [])) > 1:
            with st.expander(f"Show all {len(result['attempts'])} attempts"):
                for i, attempt in enumerate(result["attempts"], 1):
                    st.text(f"Attempt {i}:")
                    st.code(attempt, language="sql")
    else:
        if result.get("summary"):
            st.subheader("Answer")
            st.write(result["summary"])

        df = pd.DataFrame(result["rows"], columns=result["columns"])
        chart = result.get("chart", {"chart_type": "none"})

        if chart["chart_type"] == "metric":
            st.metric(label=chart.get("label_col") or "Result", value=df[chart["value_col"]].iloc[0])
        elif chart["chart_type"] == "bar":
            fig = px.bar(df, x=chart["x_col"], y=chart["y_col"])
            st.plotly_chart(fig, use_container_width=True)
        elif chart["chart_type"] == "line":
            fig = px.line(df, x=chart["x_col"], y=chart["y_col"])
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Generated SQL")
        st.code(result["sql"], language="sql")
        if len(result.get("attempts", [])) > 1:
            st.caption(f"(Took {len(result['attempts'])} attempts to pass validation)")

        st.subheader("Results")
        st.dataframe(df, use_container_width=True)
