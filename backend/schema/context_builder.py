import re
from backend.schema.introspect import get_schema_map

_SYNONYMS = {
    "revenue": {"payment"}, "spent": {"payment"}, "spend": {"payment"},
    "earn": {"payment"}, "earned": {"payment"}, "money": {"payment"}, "paid": {"payment"},
    "rent": {"rental"}, "rented": {"rental"}, "rentals": {"rental"},
    "borrow": {"rental"}, "borrowed": {"rental"}, "returned": {"rental"},
    "genre": {"category"}, "genres": {"category"},
    "actor": {"actor", "film_actor"}, "actors": {"actor", "film_actor"},
    "movie": {"film"}, "movies": {"film"}, "film": {"film"}, "films": {"film"},
    "customer": {"customer"}, "customers": {"customer"},
    "staff": {"staff"}, "employee": {"staff"}, "employees": {"staff"},
    "store": {"store"}, "stores": {"store"},
    "city": {"city", "address"}, "country": {"country", "address"},
    "language": {"language"},
}

_JOIN_BRIDGES = {
    frozenset({"film", "category"}): {"film_category"},
    frozenset({"film", "actor"}): {"film_actor"},
    frozenset({"film", "rental"}): {"inventory"},
    frozenset({"customer", "address"}): {"address"},
    frozenset({"address", "city"}): {"city"},
    frozenset({"city", "country"}): {"country"},
}

# Common short words that are substrings of unrelated column names by
# accident (e.g. 'in' matches inventory_id, original_language_id) and add
# no real signal about the question's intent. Filtered out before scoring
# after we caught this producing false-positive table matches in testing.
_STOPWORDS = {
    "how", "much", "many", "what", "who", "when", "where", "which", "why",
    "the", "a", "an", "is", "are", "was", "were", "did", "do", "does",
    "in", "on", "at", "of", "to", "for", "and", "or", "we", "us", "our",
    "make", "made", "has", "have", "had", "all", "each", "per", "by",
}
_MIN_TOKEN_LENGTH = 3

def _tokenize(question: str) -> set[str]:
    words = re.findall(r"[a-z]+", question.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) >= _MIN_TOKEN_LENGTH}

def select_relevant_tables(question: str, top_k: int = 6) -> set[str]:
    """Score each table by keyword/synonym overlap with the question, return
    the top_k highest scorers plus any join-bridge tables needed to connect
    them. Falls back to the full schema if nothing scores above zero, so an
    oddly-phrased question still gets an answer rather than an empty prompt."""
    schema = get_schema_map()
    tokens = _tokenize(question)

    scores = {t: 0 for t in schema}
    for token in tokens:
        for table_name, columns in schema.items():
            if token in table_name:
                scores[table_name] += 2
            if any(token in col for col in columns):
                scores[table_name] += 1
        for syn_word, syn_tables in _SYNONYMS.items():
            if token == syn_word:
                for t in syn_tables:
                    if t in scores:
                        scores[t] += 2

    ranked = sorted(schema.keys(), key=lambda t: scores[t], reverse=True)
    top_scoring = [t for t in ranked if scores[t] > 0][:top_k]

    if not top_scoring:
        return set(schema.keys())

    selected = set(top_scoring)
    for pair, bridges in _JOIN_BRIDGES.items():
        if pair.issubset(selected):
            selected |= bridges

    return selected
