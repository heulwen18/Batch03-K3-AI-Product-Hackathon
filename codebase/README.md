# VLearn Learner-Friction Pipeline

An offline, reproducible pipeline that fine-tunes PhoBERT on anonymized VLearn prompt logs and produces a class-level friction report. No API key or hosted inference service is required, so private chat data stays local. The first run downloads public pretrained weights from Hugging Face.

## What it does

1. Pairs student and tutor messages by `turn_id` (independent of CSV row order).
2. Creates exactly one auditable output label per turn:
   - `learning_difficulty`: observable confusion or repeated difficulty with material
   - `tutor_limitation`: the tutor response cannot resolve the learner's question
   - `off_topic`: the prompt is unrelated to learning
   - `normal`: an ordinary learning interaction without a difficulty signal
3. Splits by conversation to prevent the same conversation leaking into train and test.
4. Fine-tunes `vinai/phobert-base-v2` with a three-class classification head using the complete prompt-log turn (typed prompt, selected passage, and tutor response).
5. Adds conversation-level repeated-question detection.
6. Searches the six supplied transcripts with TF-IDF to distinguish likely tutor retrieval failures from content not found in the supplied teaching material.
7. Writes aggregate reports without `user_id`.

## Run

From the repository root:

```bash
python3 -m pip install -r codebase/requirements.txt
python3 codebase/train.py --epochs 3 --batch-size 8
python3 -m pytest codebase/tests -q
```

On Apple Silicon, training automatically uses MPS when available; otherwise it uses CUDA or CPU.

Artifacts are written to `codebase/artifacts/`:

- `phobert_model/`: fine-tuned model, tokenizer, and label mapping
- `metrics.json`: held-out weak-label agreement and confusion matrix
- `predictions.csv`: anonymized turn-level diagnoses with traceable turn IDs
- `report.json`: ranked class-level topics for a dashboard

## Interpretation

The classes are mutually exclusive. Off-topic prompts take precedence, followed by tutor-failure evidence, learning-difficulty signals, and finally `normal`. Class-weighted cross-entropy reduces the effect of class imbalance. The reported accuracy measures agreement with programmatic seed labels, not human truth. It verifies that the training pipeline works, but the deployable quality bar must be measured on independently human-labelled cases in `eval/`. A transcript miss means only “not found in the six supplied transcripts,” never “was never taught.”

The transcript similarity threshold (`0.18`) and repetition threshold (`0.48`) are explicit prototype defaults. Tune them against the golden set rather than silently treating them as facts.
