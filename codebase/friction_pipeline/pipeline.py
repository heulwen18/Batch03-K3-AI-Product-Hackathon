import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from .data import load_transcripts, load_turns
from .labels import add_repetition_signals, seed_label, topic_for, tutor_failed
from .phobert import PhoBERTTextClassifier
from .retrieval import TranscriptIndex
from .split import grouped_split


def evaluate(model, records):
    labels = model.labels
    matrix = {actual: Counter() for actual in labels}
    predicted_rows = model.predict_many([row["model_text"] for row in records])
    for row, (predicted, _) in zip(records, predicted_rows):
        matrix[row["seed_label"]][predicted] += 1
    correct = sum(matrix[label][label] for label in labels)
    total = len(records)
    return {"accuracy": round(correct / total, 4) if total else 0, "size": total,
            "confusion_matrix": {k: dict(v) for k, v in matrix.items()}}


def train_and_report(csv_path, transcript_dir, output_dir, min_sample=20,
                     epochs=3, batch_size=8, max_length=256):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    turns = add_repetition_signals(load_turns(csv_path))
    for turn in turns:
        turn["seed_label"] = seed_label(turn)
    train, test = grouped_split(turns)
    model = PhoBERTTextClassifier(
        epochs=epochs, batch_size=batch_size, max_length=max_length
    )
    texts = [model.format_text(row) for row in train]
    model.fit(texts, [r["seed_label"] for r in train])
    model.save(output / "phobert_model")
    for row in turns:
        row["model_text"] = model.format_text(row)
    metrics = evaluate(model, test)
    metrics.update({"backend": "phobert", "train_size": len(train), "labels": dict(Counter(r["seed_label"] for r in turns)),
                    "note": "Agreement with weak labels; validate quality against a human-labelled golden set."})
    (output / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    index = TranscriptIndex(load_transcripts(transcript_dir))
    predictions = []
    model_predictions = model.predict_many([turn["model_text"] for turn in turns])
    for turn, (label, confidence) in zip(turns, model_predictions):
        grounding_query = " ".join(part for part in (turn["student_text"], turn["selected_text"]) if part)
        matches = index.search(grounding_query, limit=1)
        match = matches[0] if matches else {"score": 0, "segment_id": None}
        retrieval_failure = tutor_failed(turn["tutor_text"])
        cause = "tutor_retrieval_failure" if retrieval_failure and match["score"] >= 0.18 else (
            "not_found_in_provided_transcripts" if retrieval_failure else "learner_concept_difficulty")
        if label == "irrelevant_question": cause = "irrelevant_or_non_learning_prompt"
        predictions.append({
            "turn_id": turn["turn_id"], "conversation_id": turn["conversation_id"],
            "date": turn["created_at"][:10], "topic": topic_for(grounding_query),
            "label": label, "confidence": round(confidence, 4),
            "repeated_question": turn["repeated_question"], "cause": cause,
            "transcript_segment": match["segment_id"], "transcript_score": match["score"],
            "example": turn["student_text"][:180],
        })
    fields = list(predictions[0])
    with (output / "predictions.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fields); writer.writeheader(); writer.writerows(predictions)

    grouped = defaultdict(list)
    for row in predictions:
        if row["label"] != "irrelevant_question": grouped[row["topic"]].append(row)
    summary = []
    for topic, rows in grouped.items():
        summary.append({"topic": topic, "turns": len(rows),
                        "conversations": len({r["conversation_id"] for r in rows}),
                        "repeated": sum(r["repeated_question"] for r in rows),
                        "retrieval_failures": sum(r["cause"] == "tutor_retrieval_failure" for r in rows),
                        "not_found": sum(r["cause"] == "not_found_in_provided_transcripts" for r in rows),
                        "confidence": round(sum(r["confidence"] for r in rows) / len(rows), 3),
                        "examples": [{"turn_id": r["turn_id"], "text": r["example"]} for r in rows[:2]]})
    summary.sort(key=lambda x: (x["repeated"] + x["retrieval_failures"], x["turns"]), reverse=True)
    report = {"sample_size": len(turns), "low_sample_confidence": len(turns) < min_sample,
              "privacy": "Class-level aggregate; user_id is neither loaded into outputs nor persisted.",
              "limitations": ["Labels are weakly supervised and require human golden-set validation.",
                              "Transcript absence means absent only from the six supplied files."],
              "top_frictions": summary[:10]}
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return metrics, report
