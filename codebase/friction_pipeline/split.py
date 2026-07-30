import random


def grouped_split(records, test_ratio=0.2, seed=42):
    """Split whole conversations to prevent train/test leakage."""
    groups = sorted({record["conversation_id"] for record in records})
    random.Random(seed).shuffle(groups)
    test_groups = set(groups[:max(1, round(len(groups) * test_ratio))])
    return (
        [record for record in records if record["conversation_id"] not in test_groups],
        [record for record in records if record["conversation_id"] in test_groups],
    )

