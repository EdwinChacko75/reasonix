# utils.py
import os
import json
import yaml
import datetime
import torch.distributed as dist
from typing import Optional, Dict, Any


def is_main_process() -> bool:
    """
    Determines if the current process is the main process in a distributed training setup.

    Returns:
        bool: True if it's the main process, or if not in a distributed setup.
    """
    return not dist.is_available() or not dist.is_initialized() or dist.get_rank() == 0


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Loads and parses a YAML configuration file with type-safe casting.

    Args:
        config_path (str): Path to the YAML config file.

    Returns:
        dict: Configuration dictionary with appropriate value types.
    """
    with open(config_path, "r") as f:
        config: Dict[str, Any] = yaml.safe_load(f)

    # Ensure numeric config values are correctly cast
    config["learning_rate"] = float(config["learning_rate"])
    config["weight_decay"] = float(config.get("weight_decay", 0.0))
    config["warmup_steps"] = int(config.get("warmup_steps", 0))
    config["epochs"] = int(config["epochs"])
    config["batch_size"] = int(config["batch_size"])
    config["eval_batch_size"] = int(config.get("eval_batch_size", config["batch_size"]))
    config["gradient_accumulation_steps"] = int(
        config.get("gradient_accumulation_steps", 1)
    )
    config["logging_steps"] = int(config.get("logging_steps", 50))
    config["eval_steps"] = int(config.get("eval_steps", 100))
    config["save_steps"] = int(config.get("save_steps", 200))
    config["save_total_limit"] = int(config.get("save_total_limit", 2))
    return config


def create_run_directory(
    base_dir: str = "checkpoints",
    model_name: str = "run",
    config: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Creates a unique directory for saving model checkpoints and logs.

    Directory name is based on the current timestamp.
    Saves the config as config.json in the run directory if provided.

    Args:
        base_dir (str): Root directory for saving runs.
        model_name (str): Identifier for the run.
        config (dict, optional): Configuration to save alongside the run.

    Returns:
        str: Path to the created run directory.
    """
    os.makedirs(base_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%d_%H-%M")
    run_name = f"{model_name}_{timestamp}"
    run_dir = os.path.join(base_dir, run_name)
    os.makedirs(run_dir, exist_ok=True)

    if config:
        config_path = os.path.join(run_dir, "config.json")
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)

    return run_dir
