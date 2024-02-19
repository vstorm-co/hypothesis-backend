class ErrorCode:
    ROOM_ALREADY_EXISTS = "Room with this name already exists!"
    ROOM_DOES_NOT_EXIST = "Room with this id does not exist!"
    ROOM_IS_NOT_SHARED = "Room is not shared for you"
    NOT_SAME_ORGANIZATIONS = "You are from different organization"
    ROOM_CANNOT_BE_CREATED = "Room cannot be created"


MODEL_NAME = "gpt-4-1106-preview"
MAIN_SYSTEM_PROMPT = """I am very helpful AI assistant.
I am open to handle conversations with people.
I remember everything you say to me during the conversation.
"""
TITLE_PROMPT = """To craft a distinctive chat name from a given prompt,
I will distill it into a short and memorable phrase.
This phrase should be a condensed set of words that convey the essence of the text,
and it should sound sensible when spoken.
The choice of words can be influenced by the prompt's structure,
and there is no requirement
to prioritize the initial words.
If the provided text doesn't offer sufficient material for a chat name,
I'll indicate it by not generating a name.
Rules:
- I won't give a name that is longer than 10 words.
- I won't give name that starts with "New Chat".
- I won't result in a name that is longer than 50 characters.
- If the given prompt is up to 2 words I will return the same prompt and
random name to avoid duplicates.
"""
OPTIMIZE_CONTENT_PROMPT = f"""Basic on given input text,
I will return optimised text, easy to read for {MODEL_NAME},
Don't duplicate information.
If not possible, I will return key words from the input text.
"""
TITLE_FROM_URL_PROMPT = (
    """Return only file the human readable name from url and nothing more."""
)
FILE_PATTERN = "&lt;&lt;file:"
