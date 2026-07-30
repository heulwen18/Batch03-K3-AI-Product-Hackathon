#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from friction_pipeline.pipeline import train_and_report


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="Train and run the VLearn learner-friction pipeline")
    parser.add_argument("--chatlog", type=Path, default=ROOT / "data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv")
    parser.add_argument("--transcripts", type=Path, default=ROOT / "data/vlearn-pack/transcript")
    parser.add_argument("--output", type=Path, default=ROOT / "codebase/artifacts")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=256)
    args = parser.parse_args()
    metrics, report = train_and_report(
        args.chatlog, args.transcripts, args.output,
        epochs=args.epochs, batch_size=args.batch_size, max_length=args.max_length,
    )
    print(json.dumps({"metrics": metrics, "top_frictions": report["top_frictions"][:5]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
