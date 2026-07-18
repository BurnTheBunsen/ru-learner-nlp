from pathlib import Path
from ufal.udpipe import Model, Pipeline, ProcessingError
from pymystem3 import Mystem
from src.pipeline_prototype import BASE_DIR
MODEL_PATH = BASE_DIR / "models" / "russian-syntagrus-ud-2.5-191206.udpipe"

def main():
    """
    The entire function of this script is to feed the most complicated edge cases into both of the
    engines so that we can identify if any specific type of user input can cause a missmatch
    between how the two engines tokenize that can crash the main pipeline when it tries to
    merge the two outputs into one csv file.
    :return:
    Two outputs one after another to visually check for mismatches.
    """
    test_text = f"Из-за дождя А.С. Пушкин не пошел в МГУ... Он кто-то, кто говорит по-русски,но делает ошибки?!"
    # udpipe and mystem instantiations
    model = Model.load(MODEL_PATH)
    udpipeline = Pipeline(model, "tokenize", Pipeline.DEFAULT, Pipeline.DEFAULT, "conllu")
    error = ProcessingError()

