from pymystem3 import Mystem
import json

# Instantiate the engine
m = Mystem()
text = "Я вижу красивая собаке."

# Run the analyzer
result = m.analyze(text)

# Mystem.analyze() output structure check
print(json.dumps(result, ensure_ascii=False, indent=4))