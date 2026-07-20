# Tokenizer Stress Testing & Alignment

## Overview
This directory contains the experimental testing environment for the L2 Russian NLP pipeline. Before processing the full learner corpus, we must ensure absolute token alignment between our morphological dictionary (Mystem3) and our syntactic dependency parser (UDPipe). 

Because these engines possess fundamentally different architectural philosophies, unhandled edge cases will cause fatal index mismatches during the Two-Pointer matching phase. This module isolates those edge cases and implements sanitization layers to neutralize them.

## Methodology
We built an interactive command-line testing script (`output_comparison.py`) that feeds specific linguistic traps into both engines. 

Run the tests via terminal:
`python output_comparison.py --test <1|2|3>`

---

## Edge Cases & Engineered Solutions

### Test 1: Punctuation & L2 Spacing Errors
**The Trap:** `Из-за дождя А.С. Пушкин... говорит по-русски,но делает ошибки?!`  
**The Problem:** UDPipe is a syntactic parser that preserves punctuation as structural tokens. Mystem also outputs punctuation as raw text tokens (e.g., `{'text': '.'}`). Furthermore, L2 spacing errors (e.g., `по-русски,но`) cause UDPipe to attach punctuation directly to alphabetic words, creating a severe alignment mismatch between the two engines.  
**The Solution:** A custom string-stripping Scrubber. It dynamically clears leading/trailing punctuation from both UDPipe and Mystem strings while preserving necessary internal hyphens (e.g., `кто-то`, `по-русски`). For Mystem, isolated punctuation tokens are stripped down to empty strings and automatically dropped from the final array.

### Test 2: Numerical Governance
**The Trap:** `В 2025-м году 99,9% студентов сдали экзамен на 5+-!`  
**The Problem:** Russian numerals dictate the grammatical case of trailing nouns. Historically, our extraction loop filtered out any token lacking a morphological `analysis` dictionary. Because numbers lack morphology, they vanished entirely, destroying the model's ability to track L1 interference in numeral governance.  
**The Solution:** We restructured the extraction loop to preserve all alphabetic and numeric strings regardless of dictionary presence, ensuring structural anchors remain intact for UDPipe's dependency trees.

### Test 3: Digital Syntax
**The Trap:** `Студент/ка отправил(а) файл на e-mail: ivan_99@mail.ru!`  
**The Problem:** Mystem aggressively fragments email addresses and URLs at every symbol (`@`, `_`, `.`), causing a massive token bloat that breaks mathematical alignment with UDPipe.  
**The Solution:** We implemented a Regex pre-processing layer that sanitizes the raw text before it reaches the tokenizers, replacing volatile digital strings with stable, alphabetical placeholders (e.g., `EMAIL`, `URL`).