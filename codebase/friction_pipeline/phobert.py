from pathlib import Path

from .labels import LABELS


LABEL_TO_ID = {label: index for index, label in enumerate(LABELS)}
ID_TO_LABEL = {index: label for label, index in LABEL_TO_ID.items()}


class PhoBERTTextClassifier:
    """Three-class PhoBERT classifier with a small, dependency-light trainer."""

    def __init__(self, model_name="vinai/phobert-base-v2", max_length=256,
                 batch_size=8, epochs=3, learning_rate=2e-5, seed=42):
        self.model_name = model_name
        self.max_length = max_length
        self.batch_size = batch_size
        self.epochs = epochs
        self.learning_rate = learning_rate
        self.seed = seed
        self.labels = list(LABELS)
        self.tokenizer = None
        self.model = None
        self.device = None

    @staticmethod
    def _dependencies():
        try:
            import torch
            from pyvi import ViTokenizer
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "PhoBERT dependencies are missing. Run: "
                "python3 -m pip install -r codebase/requirements.txt"
            ) from exc
        return torch, ViTokenizer, AutoModelForSequenceClassification, AutoTokenizer

    @staticmethod
    def format_text(turn):
        parts = [f"Câu hỏi học viên: {turn['student_text']}"]
        if turn.get("selected_text"):
            parts.append(f"Đoạn được chọn: {turn['selected_text']}")
        parts.append(f"Câu trả lời gia sư: {turn['tutor_text']}")
        return " ".join(parts)

    def _prepare(self):
        torch, _, model_class, tokenizer_class = self._dependencies()
        from huggingface_hub import hf_hub_download

        torch.manual_seed(self.seed)
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else
            "mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available() else
            "cpu"
        )
        self.tokenizer = tokenizer_class.from_pretrained(self.model_name)
        # Fetch the published PyTorch checkpoint explicitly. Loading locally
        # afterwards prevents Transformers from starting its background
        # safetensors auto-conversion/download thread.
        hf_hub_download(repo_id=self.model_name, filename="pytorch_model.bin")
        self.model = model_class.from_pretrained(
            self.model_name,
            num_labels=len(LABELS),
            id2label=ID_TO_LABEL,
            label2id=LABEL_TO_ID,
            # PhoBERT publishes a PyTorch .bin checkpoint. Prefer it explicitly
            # so Hugging Face does not attempt a second 540 MB safetensors fetch.
            use_safetensors=False,
            local_files_only=True,
        ).to(self.device)
        print(f"PhoBERT loaded on {self.device}", flush=True)
        return torch

    def _encode(self, texts):
        _, segmenter, _, _ = self._dependencies()
        segmented = [segmenter.tokenize(text) for text in texts]
        return self.tokenizer(
            segmented, padding=True, truncation=True,
            max_length=self.max_length, return_tensors="pt",
        )

    def fit(self, texts, labels):
        torch = self._prepare()
        encoded = self._encode(texts)
        targets = torch.tensor([LABEL_TO_ID[label] for label in labels], dtype=torch.long)
        dataset = torch.utils.data.TensorDataset(
            encoded["input_ids"], encoded["attention_mask"], targets
        )
        generator = torch.Generator().manual_seed(self.seed)
        loader = torch.utils.data.DataLoader(
            dataset, batch_size=self.batch_size, shuffle=True, generator=generator
        )
        counts = torch.bincount(targets, minlength=len(LABELS)).float()
        class_weights = (len(targets) / (len(LABELS) * counts.clamp_min(1))).to(self.device)
        loss_function = torch.nn.CrossEntropyLoss(weight=class_weights)
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=self.learning_rate)

        self.model.train()
        total_batches = len(loader)
        for epoch in range(self.epochs):
            total_loss = 0.0
            for batch_index, (input_ids, attention_mask, batch_targets) in enumerate(loader, start=1):
                optimizer.zero_grad()
                logits = self.model(
                    input_ids=input_ids.to(self.device),
                    attention_mask=attention_mask.to(self.device),
                ).logits
                loss = loss_function(logits, batch_targets.to(self.device))
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()
                total_loss += loss.item()
                if batch_index == 1 or batch_index % 10 == 0 or batch_index == total_batches:
                    print(
                        f"epoch {epoch + 1}/{self.epochs} "
                        f"batch {batch_index}/{total_batches} loss={loss.item():.4f}",
                        flush=True,
                    )
            print(
                f"epoch {epoch + 1} complete average_loss={total_loss / total_batches:.4f}",
                flush=True,
            )
        return self

    def predict_many(self, texts):
        torch, _, _, _ = self._dependencies()
        self.model.eval()
        results = []
        for start in range(0, len(texts), self.batch_size):
            encoded = self._encode(texts[start:start + self.batch_size])
            with torch.no_grad():
                logits = self.model(**{key: value.to(self.device) for key, value in encoded.items()}).logits
                probabilities = torch.softmax(logits, dim=-1).cpu()
            for row in probabilities:
                confidence, label_id = row.max(dim=-1)
                results.append((ID_TO_LABEL[label_id.item()], confidence.item()))
        return results

    def predict(self, text):
        return self.predict_many([text])[0]

    def save(self, path):
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        self.model.save_pretrained(path)
        self.tokenizer.save_pretrained(path)
