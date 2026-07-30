#!/usr/bin/env python3
import argparse
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from evaluate import HUMAN_LABEL_MAP, calculate_metrics
from friction_pipeline.data import load_turns
from friction_pipeline.phobert import PhoBERTTextClassifier


ROOT = Path(__file__).resolve().parents[1]


def stratified_conversation_split(records, test_ratio=0.2, seed=42):
    by_label = defaultdict(list)
    for record in records:
        by_label[record["label"]].append(record)
    train, test = [], []
    randomizer = random.Random(seed)
    for label, items in sorted(by_label.items()):
        items = list(items)
        randomizer.shuffle(items)
        test_size = max(1, round(len(items) * test_ratio))
        if len(items) > 1:
            test_size = min(test_size, len(items) - 1)
        test.extend(items[:test_size])
        train.extend(items[test_size:])
    randomizer.shuffle(train)
    randomizer.shuffle(test)
    return train, test


def load_human_records(labels_path, chatlog_path):
    with Path(labels_path).open(encoding="utf-8-sig", newline="") as handle:
        human_rows = list(csv.DictReader(handle))
    labels = {row["conversation_id"]: HUMAN_LABEL_MAP[row["label"]] for row in human_rows}
    turns_by_conversation = defaultdict(list)
    for turn in load_turns(chatlog_path):
        if turn["conversation_id"] in labels:
            turns_by_conversation[turn["conversation_id"]].append(turn)
    missing = sorted(set(labels) - set(turns_by_conversation))
    if missing:
        raise ValueError(f"Labelled conversations missing from chatlog: {missing[:5]}")
    return [{"conversation_id": conversation_id, "label": label,
             "text": PhoBERTTextClassifier.format_conversation(turns_by_conversation[conversation_id])}
            for conversation_id, label in labels.items()]


def main():
    parser = argparse.ArgumentParser(description="Fine-tune PhoBERT on human-labelled conversations")
    parser.add_argument("--labels", type=Path, default=ROOT / "data/test.csv")
    parser.add_argument("--chatlog", type=Path, default=ROOT / "data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "codebase/artifacts/phobert_human_model")
    parser.add_argument("--metrics", type=Path, default=ROOT / "codebase/artifacts/human_trained_metrics.json")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--test-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    records = load_human_records(args.labels, args.chatlog)
    train, test = stratified_conversation_split(records, args.test_ratio, args.seed)
    model = PhoBERTTextClassifier(epochs=args.epochs, batch_size=args.batch_size,
                                  max_length=args.max_length, seed=args.seed)
    model.fit([row["text"] for row in train], [row["label"] for row in train])
    predictions = model.predict_many([row["text"] for row in test])
    metrics = calculate_metrics([row["label"] for row in test], [label for label, _ in predictions])
    metrics.update({
        "unit": "conversation", "split": "stratified by label and conversation_id",
        "seed": args.seed, "train_conversations": len(train), "test_conversations": len(test),
        "train_distribution": dict(Counter(row["label"] for row in train)),
        "test_distribution": dict(Counter(row["label"] for row in test)),
        "train_conversation_ids": [row["conversation_id"] for row in train],
        "test_conversation_ids": [row["conversation_id"] for row in test],
    })
    model.save(args.output)
    args.metrics.parent.mkdir(parents=True, exist_ok=True)
    args.metrics.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
