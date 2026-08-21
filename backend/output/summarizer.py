from backend.nl2sql.llm_client import generate_text

SUMMARY_PROMPT = '''You are summarizing the result of a database query for a business user.

Question: {question}

Query result rows (already computed -- do not recalculate anything):
{rows}

Write ONE short sentence (max 30 words) that directly answers the question using ONLY the numbers and values shown above. Do not add commentary or caveats. Do not invent any number that is not present in the data above.'''

def summarize_result(question: str, rows: list, max_rows_shown: int = 10) -> str:
    """Ask the LLM to write a single sentence describing the result, grounded
    explicitly in the real returned rows. This reduces -- but does not fully
    eliminate -- the risk of a hallucinated summary; worth noting as a known
    limitation rather than a guarantee."""
    if not rows:
        return "The query returned no results."
    preview = rows[:max_rows_shown]
    prompt = SUMMARY_PROMPT.format(question=question, rows=preview)
    return generate_text(prompt)
