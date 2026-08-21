NAIVE_SQL_PROMPT = '''You are a SQL expert. Given a database schema and a question, write a single PostgreSQL SELECT query that answers the question.

Schema:
{schema}

Question: {question}

Rules:
- Return ONLY the SQL query, no explanation, no markdown code fences.
- Only use SELECT statements.
- Only use tables and columns that appear in the schema above.

SQL:'''
