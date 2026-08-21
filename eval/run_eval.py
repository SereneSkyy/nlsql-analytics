import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import yaml
import pandas as pd
from datetime import datetime, timezone

from backend.execution.runner import run_sql
from backend.nl2sql.generate_then_validate import question_to_sql as pipeline_a
from backend.nl2sql.constrain_then_generate import question_to_sql as pipeline_b

GOLD_PATH = os.path.join(os.path.dirname(__file__), "gold_questions.yaml")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")

def load_gold_questions():
    with open(GOLD_PATH, "r") as f:
        return yaml.safe_load(f)

def normalize_result(df: pd.DataFrame):
    """Turn a result DataFrame into an order- and column-name-independent
    representation, so we can compare a generated query's output to the gold
    query's output even when column names/order differ but the actual data
    is equivalent."""
    if df is None or df.empty:
        return []
    rows = []
    for _, row in df.iterrows():
        normalized_row = []
        for val in row:
            if isinstance(val, float):
                val = round(val, 2)
            normalized_row.append(val)
        rows.append(tuple(sorted(normalized_row, key=lambda x: str(x))))
    return sorted(rows, key=lambda r: str(r))

def run_pipeline_on_question(pipeline_fn, pipeline_name, q, gold_normalized):
    record = {
        "id": q["id"],
        "difficulty": q["difficulty"],
        "question": q["question"],
        "pipeline": pipeline_name,
    }
    try:
        result = pipeline_fn(q["question"])
    except Exception as e:
        record.update({"generation_error": str(e), "is_valid": False, "correct": False, "num_attempts": None})
        return record

    record["generated_sql"] = result["sql"]
    record["is_valid"] = result["is_valid"]
    record["num_attempts"] = len(result["attempts"])
    record["tables_used"] = result.get("tables_used")
    record["validation_errors"] = result.get("errors", [])

    if not result["is_valid"]:
        record["correct"] = False
        record["execution_error"] = None
        return record

    try:
        actual_df = run_sql(result["sql"])
        record["correct"] = normalize_result(actual_df) == gold_normalized
        record["execution_error"] = None
    except Exception as e:
        record["correct"] = False
        record["execution_error"] = str(e)

    return record

def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    questions = load_gold_questions()
    all_records = []

    import time as _time
    for q in questions:
        print(f"Running {q['id']}: {q['question']}")
        try:
            gold_df = run_sql(q["sql"])
            gold_normalized = normalize_result(gold_df)
        except Exception as e:
            print(f"  ! Could not execute gold SQL for {q['id']}: {e}")
            continue

        record_a = run_pipeline_on_question(pipeline_a, "generate_then_validate", q, gold_normalized)
        all_records.append(record_a)
        print(f"  Pipeline A: valid={record_a.get('is_valid')} correct={record_a.get('correct')} attempts={record_a.get('num_attempts')}")

        record_b = run_pipeline_on_question(pipeline_b, "constrain_then_generate", q, gold_normalized)
        all_records.append(record_b)
        print(f"  Pipeline B: valid={record_b.get('is_valid')} correct={record_b.get('correct')} attempts={record_b.get('num_attempts')}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(RESULTS_DIR, f"eval_{timestamp}.json")
    with open(out_path, "w") as f:
        json.dump(all_records, f, indent=2, default=str)

    df = pd.DataFrame(all_records)
    summary = df.groupby("pipeline").agg(
        valid_rate=("is_valid", "mean"),
        correct_rate=("correct", "mean"),
        avg_attempts=("num_attempts", "mean"),
    )
    print("\n=== SUMMARY ===")
    print(summary)

    summary_path = os.path.join(RESULTS_DIR, f"summary_{timestamp}.csv")
    summary.to_csv(summary_path)
    print(f"\nFull results: {out_path}")
    print(f"Summary: {summary_path}")

if __name__ == "__main__":
    main()
