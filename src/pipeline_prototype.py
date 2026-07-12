import sys
import time
import tracemalloc
import logging
from pathlib import Path
import pandas as pd
from ufal.udpipe import Model, Pipeline, ProcessingError
from pymystem3 import Mystem
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

    # Input regex cleaning
    logger.info("Sanitizing the raw input text...")
    df["raw_text"] = (
        df["raw_text"]
        .str.replace(r'[\xa0\t\n\r]', " ", regex=True)
        .str.repalce(r'\.{2,}', "...", regex=True)
        .str.replace(r' +', ' ', regex=True)
        .str.strip())
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

    # Update the original metadata dataframe
    df["token_count"] = token_counts

    # Build the brand new token-level dataframe
    token_columns = ["participant_id", "ID", "FORM", "LEMMA", "UPOS", "XPOS", "FEATS", "HEAD", "DEPREL", "DEPS", "MISC"]
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