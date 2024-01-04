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
TITLE_PROMPT = """Today, we’re going to create a prompt that will take a longish
text, usually a prompt, and condense it to a very short “gist” of the text
that the author will recognize when he or she sees it in a history
that can only show about 25-30 characters of text.
The gist should be a compact short sequence of words
that make sense when said aloud, almost as a phrase or something.
The gist may favor the first words in the prompt, or it may not,
depending on how the prompt is structured.
If the given text is not sufficient to generate a title,
return 'New Chat' and nothing else.
Be aware of input messages that looks like a continuation of
this prompt message- if it happen,
return 'New Chat' and nothing else more."""
