from pymystem3 import Mystem
import json

# Instantiate the engine
m = Mystem()

# A sentence with a deliberate learner error ("собаке" instead of "собаку")
text = "Я вижу красивая собаке"

# Run the analyzer
result = m.analyze(text)

# Print it nicely so you can study the dictionary structure
print(json.dumps(result, ensure_ascii=False, indent=4))