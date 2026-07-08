import sys
import logging
from pathlib import Path
import pandas as pd
from ufal.udpipe import Model, Pipeline, ProcessingError
import pymystem3 as mystem
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
MODEL_PATH = DATA_DIR / "models" / "russian-Syntagrus-ud-2.5-191206.udpipe"

def main():
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
    df = pd.read_csv(active_path)
    logger.info(f"Data loaded from {active_path}")
    # Ufal.udpipe engine initialization
    if not MODEL_PATH.exists():
        logger.critical(f"Model does not exist in {MODEL_PATH}.")
        raise FileNotFoundError(f"UDPipe model file not found: {MODEL_PATH}")

    model = Model.load(str(MODEL_PATH))
    logger.info(f"{MODEL_PATH} Loaded.")

    if not model:
        logger.critical(f"UDPipe failed to instantiate model {MODEL_PATH}.")

    pipeline = Pipeline(model, "tokenize",Pipeline.DEFAULT, Pipeline.DEFAULT, "conllu")
    error = ProcessingError()

    # Pipeline loop
    conllu_outputs = []
    token_count = []
    for idx, row in df.iterrows():
        text = str(row['raw_text'])
        pid = row['participant_id']

        processed_text = pipeline.process(text, error)
        # In case C++ engine crashes on an essay
        if error.occurred():
            logger.error(f"Processing failed for essay {pid}: {error.message}")
        conllu_outputs.append(None)
        token_count.append(0)
        continue

        conllu_output.append(processed_text)

        # token count extraction
        tokens = [line for line in processed_text.split("\n") if line and not line.startswith("#")]
        token_count.append(len(tokens))