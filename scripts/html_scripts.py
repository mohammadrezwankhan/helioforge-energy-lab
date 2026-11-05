"""Extract script bodies for publication verification."""

from dataclasses import dataclass
from html.parser import HTMLParser


@dataclass(frozen=True)
class ScriptBlock:
    """One script element's attributes and exact body text."""

    attributes: dict[str, str | None]
    body: str


class ScriptParser(HTMLParser):
    """Use HTML tokenization for attributes, comments and script raw text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.blocks: list[ScriptBlock] = []
        self.attributes: dict[str, str | None] | None = None
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script":
            self.attributes = {}
            for name, value in attrs:
                self.attributes.setdefault(name, value)
            self.parts = []

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # A slash does not make an HTML script element void.
        if tag == "script":
            self.handle_starttag(tag, attrs)
            self.set_cdata_mode("script")

    def handle_data(self, data: str) -> None:
        if self.attributes is not None:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self.attributes is not None:
            self.blocks.append(ScriptBlock(self.attributes, "".join(self.parts)))
            self.attributes = None
            self.parts = []


def script_blocks(html: str) -> list[ScriptBlock]:
    """Parse generated-page scripts without dropping malformed or quoted tags."""
    parser = ScriptParser()
    parser.feed(html.replace("\r\n", "\n").replace("\r", "\n"))
    parser.close()
    if parser.attributes is not None:
        raise ValueError("Publication evidence contains an unterminated script element")
    return parser.blocks
