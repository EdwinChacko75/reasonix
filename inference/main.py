# main.py
import os
import torch
import shutil
from tqdm import tqdm

from model import load_model
from dataset import load_dataset, extract_final_number, compute_accuracy
from utils import save_outputs_to_file, create_run_directory, load_config, get_final_dir

# Load config
config = load_config()

# Optional: Set CUDA devices from config
if config.get("cuda_visible_devices"):
    os.environ["CUDA_VISIBLE_DEVICES"] = config["cuda_visible_devices"]

MODEL_NAME = config["model_name"]
LoRA_MODEL = config["use_lora"]
LOAD_MODEL_PTH = config["weights_path"]
BATCH_SIZE = config["batch_size"]
PRESCISION = getattr(torch, config["precision"])  # float16 -> torch.float16

RUN_DIR = create_run_directory(config["checkpoint_dir"], MODEL_NAME[:4])
OUTPUT_FILE = os.path.join(RUN_DIR, config["output_file_name"])
FINAL_DIR = get_final_dir(LOAD_MODEL_PTH, RUN_DIR, config["checkpoint_dir"])
WEIGHTS_PATH = LOAD_MODEL_PTH if LOAD_MODEL_PTH is not None else MODEL_NAME


def main():
    # Load dataset
    print("Loading Dataset...")
    _, dataloader = load_dataset(
        dataset_name=config["dataset_name"], batch_size=BATCH_SIZE
    )

    # Load model
    print("Loading Model...")
    model, tokenizer = load_model(WEIGHTS_PATH, PRESCISION)
    model.eval()
    print("Running Inference...")

    accuracies = []
    accuracy = 0

    for batch_idx, batch in enumerate(tqdm(dataloader, desc="Processing Batches")):
        prompts = batch["prompts"]
        batch_ground_truth_values = batch["ground_truth_values"]

        inputs = tokenizer(
            prompts, return_tensors="pt", padding=True, truncation=True
        ).to("cuda")

        with torch.no_grad():
            with torch.autocast("cuda", dtype=PRESCISION):
                outputs = model.generate(
                    input_ids=inputs["input_ids"],
                    attention_mask=inputs.get("attention_mask", None),
                    max_new_tokens=config["max_new_tokens"],
                    temperature=config["temperature"],
                    top_p=config["top_p"],
                    do_sample=config["do_sample"],
                    eos_token_id=tokenizer.eos_token_id,
                    pad_token_id=tokenizer.pad_token_id,
                    early_stopping=config.get("early_stopping", False),
                    repetition_penalty=config.get("repetition_penalty", 1.0),
                    num_beams=config.get("num_beams", 1.0),
                )

        generated_texts = [
            tokenizer.decode(output, skip_special_tokens=True) for output in outputs
        ]
        batch_predictions = [extract_final_number(text) for text in generated_texts]
        batch_acc = compute_accuracy(batch_predictions, batch_ground_truth_values)
        accuracies.append(batch_acc)
        accuracy = (accuracy * batch_idx + batch_acc) / (batch_idx + 1)

        print(f"Cumulative Accuracy: {accuracy * 100:.2f}%")

        save_outputs_to_file(
            OUTPUT_FILE,
            batch_idx,
            prompts,
            generated_texts,
            batch_ground_truth_values,
            batch_acc,
            accuracy,
        )

    print(f"Model Accuracy: {accuracy * 100:.2f}%")
    print(f"Model Accuracy: {sum(accuracies) / len(accuracies) * 100:.2f}%")

    print(f"Inference complete. Outputs saved to: {FINAL_DIR}")
    if os.path.exists(FINAL_DIR):
        shutil.rmtree(FINAL_DIR)
    shutil.move(RUN_DIR, FINAL_DIR)


if __name__ == "__main__":
    main()
