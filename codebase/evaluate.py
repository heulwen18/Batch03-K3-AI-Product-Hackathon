#!/usr/bin/env python3
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from friction_pipeline.data import load_turns
from friction_pipeline.labels import LABELS
from friction_pipeline.phobert import PhoBERTTextClassifier
from friction_pipeline.split import grouped_split


ROOT = Path(__file__).resolve().parents[1]
HUMAN_LABEL_MAP = {
    "student_stuck": "learning_difficulty",
    "chat_cannot_help": "tutor_limitation",
    "irrelevant_question": "off_topic",
    "learning_difficulty": "learning_difficulty",
    "tutor_limitation": "tutor_limitation",
    "off_topic": "off_topic",
    "normal": "normal",
}


def aggregate_turn_labels(predictions):
    labels = [label for label, _ in predictions]
    # A tutor failure or clear difficulty anywhere makes the conversation
    # actionable. Off-topic applies only when every turn is off-topic.
    if "tutor_limitation" in labels:
        return "tutor_limitation"
    if "learning_difficulty" in labels:
        return "learning_difficulty"
    if labels and all(label == "off_topic" for label in labels):
        return "off_topic"
    return "normal"


def calculate_metrics(actual, predicted):
    confusion = {label: Counter() for label in LABELS}
    for expected, observed in zip(actual, predicted):
        confusion[expected][observed] += 1
    per_class = {}
    for label in LABELS:
        true_positive = confusion[label][label]
        false_positive = sum(confusion[other][label] for other in LABELS if other != label)
        false_negative = sum(confusion[label][other] for other in LABELS if other != label)
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": round(precision, 4), "recall": round(recall, 4),
                            "f1": round(f1, 4), "support": sum(confusion[label].values())}
    return {
        "accuracy": round(sum(a == p for a, p in zip(actual, predicted)) / len(actual), 4),
        "macro_f1": round(sum(row["f1"] for row in per_class.values()) / len(LABELS), 4),
        "per_class": per_class,
        "confusion_matrix": {label: dict(confusion[label]) for label in LABELS},
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate PhoBERT against human-labelled conversations")
    parser.add_argument("--test", type=Path, default=ROOT / "data/test.csv")
    parser.add_argument("--chatlog", type=Path, default=ROOT / "data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv")
    parser.add_argument("--model", type=Path, default=ROOT / "codebase/artifacts/phobert_model")
    parser.add_argument("--output", type=Path, default=ROOT / "codebase/artifacts/human_test_metrics.json")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--heldout-only", action="store_true",
                        help="Evaluate only conversations excluded by the pipeline's deterministic train split")
    args = parser.parse_args()

    with args.test.open(encoding="utf-8-sig", newline="") as handle:
        human_rows = list(csv.DictReader(handle))
    expected_by_conversation = {
        row["conversation_id"]: HUMAN_LABEL_MAP[row["label"]] for row in human_rows
    }
    all_turns = load_turns(args.chatlog)
    training_turns, heldout_turns = grouped_split(all_turns)
    training_ids = {turn["conversation_id"] for turn in training_turns}
    heldout_ids = {turn["conversation_id"] for turn in heldout_turns}
    overlap_count = len(set(expected_by_conversation) & training_ids)
    if args.heldout_only:
        expected_by_conversation = {
            key: value for key, value in expected_by_conversation.items() if key in heldout_ids
        }
    turns_by_conversation = defaultdict(list)
    for turn in all_turns:
        if turn["conversation_id"] in expected_by_conversation:
            turns_by_conversation[turn["conversation_id"]].append(turn)
    missing = sorted(set(expected_by_conversation) - set(turns_by_conversation))
    if missing:
        raise ValueError(f"Human-labelled conversations missing from chatlog: {missing[:5]}")

    model = PhoBERTTextClassifier.load(args.model, args.batch_size, args.max_length)
    flat_turns = [turn for conversation in expected_by_conversation for turn in turns_by_conversation[conversation]]
    turn_predictions = model.predict_many([model.format_text(turn) for turn in flat_turns])
    prediction_iter = iter(turn_predictions)
    actual, predicted, detail = [], [], []
    for conversation_id, expected in expected_by_conversation.items():
        count = len(turns_by_conversation[conversation_id])
        predictions = [next(prediction_iter) for _ in range(count)]
        observed = aggregate_turn_labels(predictions)
        actual.append(expected)
        predicted.append(observed)
        detail.append({"conversation_id": conversation_id, "expected": expected,
                       "predicted": observed, "turn_count": count})

    metrics = calculate_metrics(actual, predicted)
    metrics.update({"test_conversations": len(actual), "test_turns": len(flat_turns),
                    "human_test_conversations_seen_during_training": overlap_count,
                    "heldout_only": args.heldout_only,
                    "human_label_mapping": HUMAN_LABEL_MAP,
                    "unit": "conversation; model predictions aggregated from turns"})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
