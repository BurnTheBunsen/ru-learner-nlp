import sys
from pathlib import Path
from ufal.udpipe import Model, Pipeline, ProcessingError

def processing_test_txt():
    base_path = Path(__file__).resolve().parent.parent
    model_path = base_path / "models" / "russian-syntagrus-ud-2.5-191206.udpipe"

    if not model_path.exists():
        print("Error: Model not found.")
        sys.exit(1)

    print("Model's being loaded into memory.")
    model = Model.load(str(model_path))
    if not model:
        print("Error: Model couldn't be loaded.")
        sys.exit(1)

    pipeline = Pipeline(model, "tokenize", Pipeline.DEFAULT, Pipeline.DEFAULT,"conllu")
    error = ProcessingError()

    sample_text = "Студент написал хороший текст, но сделал ошибку."
    print(f"\nProcessing Sample Text: {sample_text}\n")
    processed_text = pipeline.process(sample_text, error)

    if error.occurred():
        print(f"An error occurred: {error.message}")
    else:
        print(processed_text)


if __name__ == "__main__":
    processing_test_txt()