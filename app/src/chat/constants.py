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
I am also able to get information from given files content.
"""
TITLE_PROMPT = """Crafting Distinctive Chat Names:
Transforming Text into Memorable Phrases
Create short, sensible, and memorable chat names
based on the essence of the text provided.
Never return the same name for the same input.
Never return merged words.
Guidelines:
- Keep names under 10 words.
- Avoid starting with "New Chat."
- Limit names to 50 characters.
- For prompts up to 2 words, return a random name
to prevent duplicates.
- Do not merge words into one.
Examples:
#1
Input: "Test"
Output: "Test Chat Alpha"
#2
Input: "Test Chat"
Output: "Test Chat Foxtrot"
#3
Input: "Hi"
Output: "Greetings"
"""
OPTIMIZE_CONTENT_PROMPT = f"""Basic on given input text,
I will return optimised text, easy to read for {MODEL_NAME},
Don't duplicate information.
If not possible, I will return key words from the input text.
"""
TITLE_FROM_URL_PROMPT = """Create file name from given url.
    No dashes, no underscores, no dots, no file extensions.
    Examples:
    #1
    Input: "https://www.example.com/this-is-a-test"
    Output: "This Is A Test"
    #2
    Input: "https://www.example.com/wall-street-journal"
    Output: "Wall Street Journal"
    Return the name and nothing more."""
VALUABLE_PAGE_CONTENT_PROMPT = """You will get scraped page content.
The content has whole page content. Get only valuable information.
Focus on content that is strictly connected to given url
and title of the page.
Do not include website features like ads, links, navigation, etc.
Examples:
#1
Input page is about "How to make a cake" but it also contains
information about "How to make a pie",
"Best cake recipes", "How to make a cake without eggs" and has
a lot of ads and links to other pages,
downloadable files, etc.
Output: Only information strictly connected to "How to make a cake" and nothing more.
**Input:**
"""
FILE_PATTERN = "<<file:"
MAX_TOKENS = 15900
