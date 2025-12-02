import os
import pathlib

# Get the absolute path to the project root directory
# This will be the directory containing the src folder
ROOT_DIR = pathlib.Path(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))).resolve()

# Memory management configuration constants
MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", 25000))
MAX_MESSAGE_TOKENS = int(os.getenv("MAX_MESSAGE_TOKENS", 1000))
SLIDING_WINDOW_SIZE = int(os.getenv("SLIDING_WINDOW_SIZE", 8))
ENABLE_MEMORY_TRIMMING = os.getenv("ENABLE_MEMORY_TRIMMING", "true").lower() == "true"
ENABLE_MEMORY_SUMMARIZATION = os.getenv("ENABLE_MEMORY_SUMMARIZATION", "true").lower() == "true"
TRIM_THRESHOLD_TOKENS = int(os.getenv("TRIM_THRESHOLD_TOKENS", 20000))
SUMMARIZATION_MODEL = os.getenv("SUMMARIZATION_MODEL", "gpt-4o-mini")

# Other constants can be added here as needed
