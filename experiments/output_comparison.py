from pathlib import Path
import json
from string import punctuation
from ufal.udpipe import Model, Pipeline, ProcessingError
from pymystem3 import Mystem
import argparse
import string
import re
base_path = Path(__file__).resolve().parent.parent
model_path = base_path / "models" / "russian-syntagrus-ud-2.5-191206.udpipe"

def get_test_string():
    """Getting the test string via argparse."""
    parser = argparse.ArgumentParser(
        description="Stress test UDPipe vs Mystem tokenization on edgecases."
    )
    parser.add_argument(
        "--test",
        type=int,
        choices=[1, 2, 3],
        default=1,
        help=f"""The test string to use.
        1. Standard Traps (Initials, Spacing, Clusters)
        2. Numerical Data (Decimals, Suffixes)
        3. Digital Syntax (Emails, Slashes)""",
    )
    args = parser.parse_args()
    if args.test == 1:
        print("Running Test 1: Standard Traps...")
        return f"Из-за дождя А.С. Пушкин не пошел в МГУ... Он кто-то, кто говорит по-русски,но делает ошибки?!"
    elif args.test == 2:
        print("Running Test 2: Numerical Data...")
        return f"В 2025-м году 99,9% студентов сдали экзамен на 5+-!"
    elif args.test == 3:
        print("Running Test 3: Digital Syntax...")
        return f"Студент/ка отправил(а) файл на e-mail: ivan_99@mail.ru!"

def pre_process_text(raw_text):
    """Sanitizes text by replacing emails and URLs with safe placeholder words."""
    # Replace emails with the word "EMAIL"
    clean_text = re.sub(r'\S+@\S+\.\S+', 'EMAIL', raw_text)

    # Replace web links with the word "URL"
    clean_text = re.sub(r'http[s]?://\S+|www\.\S+', 'URL', clean_text)

    return clean_text

def main():
    """
    The entire function of this script is to feed the most complicated edge cases into both of the
    engines so that we can identify if any specific type of user input can cause a missmatch
    between how the two engines tokenize that can crash the main pipeline when it tries to
    merge the two outputs into one csv file.
    :return:
    Token number for each of them so that we can check for mismatches in tokenization.
    """
    test_text = get_test_string()
    test_text = pre_process_text(test_text)

    # udpipe and mystem instantiations
    model = Model.load(str(model_path))
    udpipeline = Pipeline(model, "tokenize", Pipeline.DEFAULT, Pipeline.DEFAULT, "conllu")
    error = ProcessingError()

    # Strip all punctuations EXCEPT hyphens
    punctuation_to_strip = string.punctuation.replace("-", "")

    mystem = Mystem()
    # processing
    mystem_result = mystem.analyze(test_text)
    # mystem_sanitized = json.dumps(mystem_result, ensure_ascii=False, indent=4)
    clean_ms_tokens = []
    for item in mystem_result:
        ms_raw_words = item.get("text", '').strip()
        ms_cleaned_words = ms_raw_words.strip(punctuation_to_strip)

        if ms_cleaned_words:
            clean_ms_tokens.append(ms_cleaned_words)

    udpipe_result = udpipeline.process(test_text, error)
    clean_ud_tokens = []
    for line in udpipe_result.split("\n"):
        if line.strip() == '' or line.startswith('#'):
            continue
        columns = line.split("\t")
        ud_raw_words = columns[1]

        # Strip leading/trailing punctuation (keeps internal punctuations like 99,9)
        cleaned_words = ud_raw_words.strip(punctuation_to_strip)

        if cleaned_words:
            clean_ud_tokens.append(cleaned_words)

    print(f"""
    UDPipe tokens: {clean_ud_tokens}
    UDPipe tokens count: {len(clean_ud_tokens)}
    Mystem tokens: {clean_ms_tokens}
    Mystem tokens count: {len(clean_ms_tokens)}
    """)

if __name__ == "__main__":
    main()