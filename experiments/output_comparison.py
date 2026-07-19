from pathlib import Path
import json
from ufal.udpipe import Model, Pipeline, ProcessingError
from pymystem3 import Mystem
base_path = Path(__file__).resolve().parent.parent
model_path = base_path / "models" / "russian-syntagrus-ud-2.5-191206.udpipe"

def main():
    """
    The entire function of this script is to feed the most complicated edge cases into both of the
    engines so that we can identify if any specific type of user input can cause a missmatch
    between how the two engines tokenize that can crash the main pipeline when it tries to
    merge the two outputs into one csv file.
    :return:
    Token number for each of them so that we can check for mismatches in tokenization.
    """
    test_text = f"Из-за дождя А.С. Пушкин не пошел в МГУ... Он кто-то, кто говорит по-русски,но делает ошибки?!"
    # udpipe and mystem instantiations
    model = Model.load(str(model_path))
    udpipeline = Pipeline(model, "tokenize", Pipeline.DEFAULT, Pipeline.DEFAULT, "conllu")
    error = ProcessingError()

    mystem = Mystem()

    # processing
    mystem_result = mystem.analyze(test_text)
    # mystem_sanitized = json.dumps(mystem_result, ensure_ascii=False, indent=4)
    clean_ms_tokens = []
    for item in mystem_result:
        if "analysis" in item and len(item["analysis"]) > 0:
            clean_ms_tokens.append(item.get("text", ""))

    udpipe_result = udpipeline.process(test_text, error)
    clean_ud_tokens = []
    for line in udpipe_result.split("\n"):
        if line.strip() == '' or line.startswith('#'):
            continue
        columns = line.split("\t")
        clean_ud_tokens.append(columns[1])

    print(f"""
    UDPipe tokens: {clean_ud_tokens}
    UDPipe tokens count: {len(clean_ud_tokens)}
    Mystem tokens: {clean_ms_tokens}
    Mystem tokens count: {len(clean_ms_tokens)}
    """)

if __name__ == "__main__":
    main()