import os
import torch

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
