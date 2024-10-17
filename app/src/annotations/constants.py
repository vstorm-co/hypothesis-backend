# ignore file in flake8
# flake8: noqa

TEXT_SELECTOR_PROMPT_TEMPLATE = """We will provide a text below. Your task is to meticulously read the entire text, line by line. Using the supplied prompt, create annotations. The number of annotations should match a specified amount if given, or otherwise, be a reasonable number. Each annotation must be formatted in JSON according to the Hypothes.is implementation of the W3C Web Annotation Data Model, allowing direct submission to the Hypothesis API.

Annotations should precisely anchor to the text, whether it's a passage, sentence, phrase, word, or character, using the Hypothes.is fuzzy anchoring strategy. This involves a 30-byte prefix and 30-byte suffix along with quoting the actual text. Use up to 30 characters for both prefix and suffix to frame the quote effectively. Keep the quote itself concise yet clear to convey the annotation.

Text to annotate: {scraped_data}
Prompt: {prompt}

Response model: Provide a JSON with the key "selectors" whose value is a list of annotation objects. The JSON format should use wrapping double quotes for keys and values to ensure validity.

Output Instructions: {format_instructions}

Processing Tips:
- This is split {split_index} of {total}.
- If no annotations are found in the current split but subsequent splits exist, return an empty JSON with "selectors": []. Ensure an empty list is only a last resort.
- Endeavor to create detailed annotations to avoid empty lists.
- Handle intertwined or unclear contexts by breaking them down and annotating individually.
- Prioritize meaningful content over fillers or context shifts.

Annotation Field Focus:
- The 'annotation' field must provide a comprehensive and precise explanation detailing why each annotation was chosen. Strive for depth and clarity to ensure complete understanding.

Example format:
scraped_data: "The love that follows us sometimes is our trouble"
Expected return:
  "selectors": 
    #1
      "exact": "love follows us",
      "prefix": "The ",
      "suffix": " sometimes is our trouble",
      "annotation": "A thorough analysis on how love persistently influences us, exploring emotional connections and psychological impacts, reflecting on the human experience."
    #2
      "exact": "our trouble",
      "prefix": "love follows us sometimes is ",
      "suffix": "",
      "annotation": "An in-depth examination of 'our trouble', addressing its role, significance, and its interrelation with the previous context of love, exploring thematic struggles."

Rules:
- Returning an empty list is only permissible if `split_index` is less than `total`.
- Prefix and suffix must not exceed 30 characters.
- Each annotation object must contain only four keys: `exact`, `prefix`, `suffix`, and `annotation`.
- Begin the response directly with a valid JSON object.

The JSON output:
"""

YOUTUBE_TRANSCRIPTION_PROMPT_TEMPLATE = """
You are provided with a text that is a transcription of a YouTube video. Your task is to go through the transcription carefully, line by line, and create annotations based on the prompt provided. The annotations should be in JSON format and follow the Hypothes.is implementation of the W3C Web Annotation data model. This allows us to directly feed the JSON to the Hypothesis API.

Annotations should precisely anchor to the text, whether it's a passage, sentence, phrase, word, or character, using the Hypothes.is fuzzy anchoring strategy. This involves a 30-byte prefix and 30-byte suffix along with quoting the actual text. Use up to 30 characters for both prefix and suffix to frame the quote effectively. Keep the quote itself concise yet clear to convey the annotation.

Text to annotate: {scraped_data}
Prompt: {prompt}

Response model: Provide a JSON with the key "selectors" whose value is a list of annotation objects. The JSON format should use wrapping double quotes for keys and values to ensure validity.

Output Instructions: {format_instructions}

Processing Tips:
- This is split {split_index} of {total}.
- If no annotations are found in the current split but subsequent splits exist, return an empty JSON with "selectors": []. Ensure an empty list is only a last resort.
- Endeavor to create detailed annotations to avoid empty lists.
- Handle intertwined or unclear contexts by breaking them down and annotating individually.
- Prioritize meaningful content over fillers or context shifts.

Annotation Field Focus:
- The 'annotation' field must provide a comprehensive and precise explanation detailing why each annotation was chosen. Strive for depth and clarity to ensure complete understanding.

Example format:
scraped_data: "The love that follows us sometimes is our trouble"
Expected return:
  "selectors": 
    #1
      "exact": "love follows us",
      "prefix": "The ",
      "suffix": " sometimes is our trouble",
      "annotation": "A thorough analysis on how love persistently influences us, exploring emotional connections and psychological impacts, reflecting on the human experience."
    #2
      "exact": "our trouble",
      "prefix": "love follows us sometimes is ",
      "suffix": "",
      "annotation": "An in-depth examination of 'our trouble', addressing its role, significance, and its interrelation with the previous context of love, exploring thematic struggles."

Rules:
- Returning an empty list is only permissible if `split_index` is less than `total`.
- Prefix and suffix must not exceed 30 characters.
- Each annotation object must contain only four keys: `exact`, `prefix`, `suffix`, and `annotation`.
- Begin the response directly with a valid JSON object.

The JSON output:
"""

DOCUMENT_TITLE_PROMPT_TEMPLATE = """Get the title of the document
from the input.
RULES:
- Return only the title and nothing else.
- Title can't be longer than 50 characters.
Input: {input}",
"""
UNIQUE_TEXT_SELECTOR_PROMPT_TEMPLATE = """Create a unique text that will be
representative of the given selector.
Have in mind, the question on the basis of which it was created: {question}.
Rules:
- Return only the unique text.
- Max 5 words.
Examples:
```
#1
question: "Make 2 annotations that can help a student
think critically about this text"
selector: "The love that follows us sometimes is our trouble"
return: "love follows us"
```
Selector: {selector}
"""
NUM_OF_SELECTORS_PROMPT_TEMPLATE = """How many things does the user ask for?
Return only the number and nothing more.
If there is no specific number return None.
Number must be in decimal system.
Example 1:
question: Annotate 10 passages where...
response: 10
Example 2:
question: Annotate the text...
response: None
Example 3:
question: Mark three facts about...
response: 3
User question: {question}
"""
