# ignore file in flake8
# flake8: noqa

TEXT_SELECTOR_PROMPT_TEMPLATE = """
We will provide a text below. Carefully read through the entire text line by line.
Then, based on the prompt we are supplying, craft a number of annotations,
either a specific number of them if provided, or an appropriate amount if not.
The annotations returned should be in JSON format that follows the
Hypothes.is implementation of the W3C Web Annotation data model,
enabling us to directly feed the JSON to the Hypothesis API.

Annotations should be anchored to passages, sentences, phrases, words,
or even characters, leveraging the Hypothes.is fuzzy anchoring strategy,
which uses a 30-byte prefix and 30-byte suffix along with a quote of
the actual text. Provide as many characters as possible, up to 30,
for both the prefix and suffix to properly bookend the quote for each
annotation. Keep the exact quote only as long as necessary to convey
the annotation clearly.

The transcription to annotate: {scraped_data}
The prompt: {prompt}

Response model: JSON with the key "selectors" and its value as a list of annotation objects.
Output format: 
- Ensure the output is valid JSON markdown with wrapping quotes " not ' as well for the keys and values.
- Sometimes user may ask for additional information, don't include that in the output, keep them in mind, make sure your output has only the key and values specified in output instructions.

Output Instructions: {format_instructions}

Tips for processing the transcription:
- We are processing split {split_index} out of {total}.
- If you can't find annotations in the current split but there are subsequent splits, skip this split by returning an empty JSON with key "selectors" and value as an empty list []. You might find annotations in the next splits.
- Always strive to find annotations, even minimal ones, to avoid returning empty lists.
- Handle intertwined words or unclear contexts by splitting and annotating them separately if necessary.
- Pay attention to common patterns in video transcriptions, such as filler words ("uh", "um"), speaker changes, and context shifts. Focus on annotating meaningful content.

Example:
scraped_data: "The love that follows us sometimes is our trouble"
return:
```
json object with key `selectors` and value as a list of annotation objects.
annotation objects: each object contain `exact`, `prefix`, `suffix`, and `annotation` fields.
firs annotation object:
- `exact`: "love follows us"
- `prefix`: "The "
- `suffix`: " sometimes is our trouble"
- `annotation`: Long, deeply thoughtful annotation about the phrase 'love follows us' and its implications.
second annotation object:
- `exact`: "our trouble"
- `prefix`: "love follows us sometimes is "
- `suffix`: ""
- `annotation`: Long, deeply thoughtful annotation about the phrase 'our trouble', its implications, and its relationship to the previous annotation.
```

###RULES:
- Returning an empty list is a last resort; always try to find annotations. You can only return an empty list if `split_index` is lower than `total`.
- Max 30 characters for prefix and suffix.
- Never include invalid annotation object in selectors list, just skip them.
- Make sure each annotation object has 4 keys: `exact`, `prefix`, `suffix`, and `annotation`. Nothing less, nothing more.
- Return only the JSON format, no additional information.
- Never start the response with 'Here is the JSON output with ...', start with valid json object
- Make sure the `annotation` field is a thoughtful, meaningful response to the prompt. Think even deeper than the prompt itself, define eveyrhing possible about the annotation.
###

The JSON output:
"""

YOUTUBE_TRANSCRIPTION_PROMPT_TEMPLATE = """
You are provided with a text that is a transcription of a YouTube video. Your task is to go through the transcription carefully, line by line, and create annotations based on the prompt provided. The annotations should be in JSON format and follow the Hypothes.is implementation of the W3C Web Annotation data model. This allows us to directly feed the JSON to the Hypothesis API.

When creating annotations, anchor them to specific passages, sentences, phrases, words, or characters in the transcription. Use the Hypothes.is fuzzy anchoring strategy, which includes a 30-byte prefix and 30-byte suffix along with the quoted text. Ensure the prefix and suffix are as long as possible, up to 30 characters, to properly bookend the quoted text. Keep the exact quote only as long as necessary to convey the annotation clearly.

The transcription to annotate: {scraped_data}
The prompt: {prompt}

Response model: JSON with the key "selectors" and its value as a list of annotation objects.
Output format: 
- Ensure the output is valid JSON markdown with wrapping quotes " not ' as well for the keys and values.
- Sometimes user may ask for additional information, don't include that in the output, keep them in mind, make sure your output has only the key and values specified in output instructions.

Output Instructions: {format_instructions}

Tips for processing the transcription:
- We are processing split {split_index} out of {total}.
- If you can't find annotations in the current split but there are subsequent splits, skip this split by returning an empty JSON with key "selectors" and value as an empty list []. You might find annotations in the next splits.
- Always strive to find annotations, even minimal ones, to avoid returning empty lists.
- Handle intertwined words or unclear contexts by splitting and annotating them separately if necessary.
- Pay attention to common patterns in video transcriptions, such as filler words ("uh", "um"), speaker changes, and context shifts. Focus on annotating meaningful content.

Example:
scraped_data: "The love that follows us sometimes is our trouble"
return:
```
json object with key `selectors` and value as a list of annotation objects.
annotation objects: each object contain `exact`, `prefix`, `suffix`, and `annotation` fields.
firs annotation object:
- `exact`: "love follows us"
- `prefix`: "The "
- `suffix`: " sometimes is our trouble"
- `annotation`: "This phrase suggests that love is a constant presence in our lives."
second annotation object:
- `exact`: "our trouble"
- `prefix`: "love follows us sometimes is "
- `suffix`: ""
- `annotation`: "The phrase 'our trouble' implies that love can also bring challenges."
```

###RULES:
- Returning an empty list is a last resort; always try to find annotations. You can only return an empty list if `split_index` is lower than `total`.
- Max 30 characters for prefix and suffix.
- Never include invalid annotation object in selectors list, just skip them.
- Make sure each annotation object has 4 keys: `exact`, `prefix`, `suffix`, and `annotation`. Nothing less, nothing more.
- Return only the JSON format, no additional information.
- Never start the response with 'Here is the JSON output with ...', start with valid json object
###

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
