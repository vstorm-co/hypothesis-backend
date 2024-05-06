from html.parser import HTMLParser
from io import StringIO


class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()

    def handle_data(self, d):
        self.text.write(d)

    def get_data(self):
        return self.text.getvalue()


def clean_html_input(input_text: str):
    # change &lt, &gt, &amp to <, >, &
    input_text = (
        input_text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    )
    s = MLStripper()
    s.feed(input_text)
    return s.get_data()
