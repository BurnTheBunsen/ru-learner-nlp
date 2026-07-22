import sys
import time
import tracemalloc
import logging
from pathlib import Path
import pandas as pd
from ufal.udpipe import Model, Pipeline, ProcessingError
from pymystem3 import Mystem
import re

# Setting up logging so all the processes, errors and crashes are logged and accounted for
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s',
                    level=logging.INFO,
                    handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

# Setting up Path resolution
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MOCK_DIR = DATA_DIR / "mock"
MODEL_PATH = BASE_DIR / "models" / "russian-syntagrus-ud-2.5-191206.udpipe"

def preprocess_text(raw_text):
    """The master text sanitizer: Cleans structural noise and eliminates digital syntax mismatches.
    Takes a raw_text string as input.
    """
    text = str(raw_text)
    cleaning_rules = [
        (r'[\xa0\t\n\r]', ' '),              # 1. Flatten hidden line breaks and tabs
        (r'\.{2,}', '...'),                  # 2. Normalize multiple dots
        (r'\S+@\S+\.\S+', 'EMAIL'),          # 3. Neutralize emails
        (r'http[s]?://\S+|www\.\S+', 'URL'), # 4. Neutralize web links
        (r' +', ' ')                         # 5. Collapse multiple spaces
    ]
    # Now we iterate over each text and apply the rules one by one
    for pattern, replacement in cleaning_rules:
        text = re.sub(pattern, replacement, text)

    return text.strip()

def normalize_for_match(text):
    """
    Normalize a string purely for the two-pointer check.
    This data is NOT saved to the final csv.
    """
    return str(text).replace(",", "").replace(".", "").lower()

def extract_scrub_tokens(udpipe_result, mystem_result):
    pass

def _get_mystem_match_indices(ud_norm, clean_ms_tokens,start_idx):
    pass

def align_tokens(clean_ms_tokens, clean_ud_tokens):
    pass

def fuse_aligned(alignment_map, ud_lines, ms_json, participant_id):
    pass


def main():
    # Profiler start to check for processing time and memory usage
    start_time = time.perf_counter()
    tracemalloc.start()

    # Make sure the subsequent directories actually exist
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    MOCK_DIR.mkdir(parents=True, exist_ok=True)
    logger.debug("Ensuring directories exist...")

    # Data Ingestion (And if there isn't any, mock data creation)
    raw_path = RAW_DIR / "corpus_dataset.csv"
    if raw_path.exists():
        active_path = raw_path
        logger.info(f"Raw dataset file already exists at {active_path}")
    else:
        mock_path = MOCK_DIR / "mock_dataset.csv"
        if mock_path.exists():
            active_path = mock_path
            logger.info("Using mock dataset that already exists...")
        else:
            mock_data = {
                "participant_id": ["P001", "P002", "P003"],
                "trki_level": ["A2", "B1", "B2"],
                "task_type": ["narrative", "argumentative", "narrative"],
                "raw_text": [
                    "Студент написал хороший текст, но сделал ошибку.",
                    "Я изучаю русский язык в университете уже два года.",
                    "Если бы я знал все правила грамматики, я бы написал тест без ошибок."
                ]
            }
            pd.DataFrame(mock_data).to_csv(mock_path, index=False, encoding='utf-8')
            active_path = mock_path
            logger.info(f"Wrote {active_path}")

    logger.info("Loading mock data into memory...")
    df = pd.read_csv(active_path, encoding="utf-8")
    logger.info(f"Data loaded from {active_path}")

    # Text preprocessing
    logger.info("Sanitizing the raw input text...")
    df["raw_text"] = df["raw_text"].apply(preprocess_text)
    logger.info("Text sanitization complete!")

    # Ufal.udpipe engine initialization
    if not MODEL_PATH.exists():
        logger.critical(f"Model does not exist in {MODEL_PATH}.")
        raise FileNotFoundError(f"UDPipe model file not found: {MODEL_PATH}")

    model = Model.load(str(MODEL_PATH))
    logger.info(f"{MODEL_PATH} Loaded.")

    if not model:
        logger.critical(f"UDPipe failed to instantiate model {MODEL_PATH}.")
        raise RuntimeError(f"UDPipe failed to instantiate model. Halting pipeline.")

    pipeline = Pipeline(model, "tokenize",Pipeline.DEFAULT, Pipeline.DEFAULT, "conllu")
    error = ProcessingError()

    # Mystem engine instantiation before the loop, same as UDPipe
    ms_engine = Mystem()

    # Pipeline loop
    token_counts = []
    parsed_tokens_list = []  # This will hold every single word from every single essay

    for idx, row in df.iterrows():
        text = str(row["raw_text"])
        pid = row["participant_id"]

        processed_text = pipeline.process(text, error)

        if error.occurred():
            logger.error(f"UDPipe failed to parse essay {pid}: {error.message}")
            token_counts.append(0)
            continue

        # Split the CoNLL-U output into individual lines
        lines = processed_text.split("\n")

        # Filter out empty lines and metadata comments
        valid_token_lines = [line for line in lines if line and not line.startswith("#")]
        token_counts.append(len(valid_token_lines))

        # The nested loop: Process each word and attach the student's ID
        for line in valid_token_lines:
            fields = line.split("\t")  # CoNLL-U format is always tab-separated
            row_data = [pid] + fields  # Combine the participant ID with the 10 UDPipe columns
            parsed_tokens_list.append(row_data)

        # Passing the raw text list which was extracted from our dataset into mystem
        ms_result = ms_engine.analyze(text)

        # now we need to write a loop for mystem too to extract all the info and tags that it provides
        clean_ms_tokens = []
        for item in ms_result:
            if "analysis" in item and len(item["analysis"]) > 0:
                clean_tokens = {
                    "ms_text": item.get("text", ""),
                    "ms_lex": item["analysis"][0].get("lex", ""),
                    "ms_wt": item["analysis"][0].get("wt", ""),
                    "ms_gr": item ["analysis"][0].get("gr", ""),
                }
                clean_ms_tokens.append(clean_tokens)

    # Update the original metadata dataframe
    df["token_count"] = token_counts

    # Build the brand new token-level dataframe
    token_columns = ["participant_id", "UD_ID", "UD_FORM", "UD_LEMMA", "UD_UPOS", "UD_XPOS", "UD_FEATS", "UD_HEAD", "UD_DEPREL", "UD_DEPS", "UD_MISC"]
    df_tokens = pd.DataFrame(parsed_tokens_list, columns=token_columns)

    # SAVE OUTPUT (RELATIONAL ARCHITECTURE)

    metadata_path = PROCESSED_DIR / "corpus_metadata.csv"
    tokens_path = PROCESSED_DIR / "corpus_tokens.csv"

    df.to_csv(metadata_path, index=False, encoding="utf-8")
    df_tokens.to_csv(tokens_path, index=False, encoding="utf-8")

    logger.info(f"Pipeline complete. Saved {len(df)} essays to {metadata_path}")
    logger.info(f"Exploded {len(df_tokens)} total tokens to {tokens_path}")

    # Profiler stop and log the metrics
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    end_time = time.perf_counter()

    elapsed_time = end_time - start_time
    peak_mb = peak_mem / (1024*1024)
    avg_time_per_essay = elapsed_time / len(df) if len(df) > 0 else 0
    logger.info(f"""
    =====================================
            PERFORMANCE PROFILER         
    =====================================
    Total Execution Time  : {elapsed_time:.2f} seconds
    Avg Time per Essay    : {avg_time_per_essay:.3f} seconds
    Peak Memory Usage     : {peak_mb:.2f} MB
    =====================================""")

if __name__ == "__main__":
    main()