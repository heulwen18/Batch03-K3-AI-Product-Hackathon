import csv
import re
from collections import defaultdict
from pathlib import Path

from .text import split_prompt


SEGMENT_RE = re.compile(r"\*\*\[(T\d{2}-\d{3})\]\*\*\s*(.*?)(?=\n\s*\*\*\[T|\Z)", re.S)


def load_turns(csv_path):
    grouped = defaultdict(dict)
    metadata = {}
    with Path(csv_path).open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            turn_id = row["turn_id"]
            grouped[turn_id][row["role"]] = row
            metadata[turn_id] = row
    turns = []
    for turn_id, messages in grouped.items():
        if "student" not in messages or "tutor" not in messages:
            continue
        student, tutor = messages["student"], messages["tutor"]
        question, selected = split_prompt(student["content"])
        turns.append({
            "turn_id": turn_id,
            "conversation_id": student["conversation_id"],
            "day_code": student["day_code"],
            "created_at": student["message_created_at"],
            "student_text": question,
            "selected_text": selected,
            "analysis_text": " ".join(part for part in (question, selected, tutor["content"]) if part),
            "student_raw": student["content"],
            "tutor_text": tutor["content"],
            "move_used": tutor["move_used"],
            "rating": tutor["rating"] or student["rating"],
        })
    return sorted(turns, key=lambda x: (x["conversation_id"], x["created_at"], x["turn_id"]))


def load_transcripts(directory):
    segments = []
    for path in sorted(Path(directory).glob("transcript-*-clean.md")):
        text = path.read_text(encoding="utf-8")
        for segment_id, content in SEGMENT_RE.findall(text):
            segments.append({"segment_id": segment_id, "text": " ".join(content.split()), "source": path.name})
    return segments
