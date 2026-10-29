"""Export only the immutable selected screenplay, without model or project context."""
from functools import lru_cache
from io import BytesIO
from pathlib import Path
import re
import textwrap
import unicodedata

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, SimpleDocTemplate, CondPageBreak


@lru_cache(maxsize=1)
def fonts():
    directory = Path(__file__).resolve().parents[1] / "assets/fonts"
    for suffix, file in (("", "LiberationMono-Regular.ttf"), ("Bold", "LiberationMono-Bold.ttf")):
        pdfmetrics.registerFont(TTFont("Screenplay" + suffix, str(directory / file)))
    return pdfmetrics.getFont("Screenplay").face.charToGlyph


def printable(text):
    # Compose Vietnamese accents for reliable glyph placement; never mutate the snapshot.
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n").expandtabs(4)
    if any(ord(c) not in fonts() for c in text if c != "\n"):
        raise ValueError("Bản đã chọn có ký tự font PDF chưa hỗ trợ. Hãy giữ bản sao và chỉnh ký tự đó trước khi chọn bản mới.")
    return text


class ScriptText(Flowable):
    def __init__(self, text, *, speaker="", bold=False, size=12, heading=False, lines=None):
        super().__init__()
        self.text, self.speaker, self.lines = text, speaker, lines
        self.font = "ScreenplayBold" if bold else "Screenplay"
        self.size, self.leading = size, size * 1.3
        self.keepWithNext = False
        self.spaceBefore = 16 if heading else 0
        self.spaceAfter = 10

    def wrap(self, width, height):
        self.width = width
        self.indent = 60 if self.speaker else 0
        self.text_width = width - self.indent * 2
        columns = max(1, int(self.text_width / pdfmetrics.stringWidth("M", self.font, self.size)))
        wrapper = textwrap.TextWrapper(width=columns, replace_whitespace=False, drop_whitespace=False,
            break_long_words=True, break_on_hyphens=False)
        if self.lines is None:
            self.lines = [line for paragraph in self.text.split("\n") for line in (wrapper.wrap(paragraph) or [""])]
        self.labels = wrapper.wrap(self.speaker) if self.speaker else []
        self.height = (len(self.labels) + len(self.lines)) * self.leading
        return width, self.height

    def split(self, width, height):
        count = int(height / self.leading) - len(self.labels)
        if count < min(2, len(self.lines)):
            return []
        # Repeat the exact speaker on each page of long dialogue, never orphan the name.
        args = dict(speaker=self.speaker, bold=self.font.endswith("Bold"), size=self.size)
        return [ScriptText("", lines=self.lines[:count], **args), ScriptText("", lines=self.lines[count:], **args)]

    def draw(self):
        canvas = self.canv
        y = self.height - self.size
        canvas.setFont(self.font, self.size)
        for label in self.labels:
            canvas.drawCentredString(self.width / 2, y, label)
            y -= self.leading
        for line in self.lines:
            canvas.drawString(self.indent, y, line)
            y -= self.leading


def selection_title(selection):
    return selection.screenplay.source_outline.source.draft.title


def filename(selection):
    title = unicodedata.normalize("NFKD", selection_title(selection).replace("đ", "d").replace("Đ", "D"))
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.encode("ascii", "ignore").decode()).strip("-")[:70]
    return f"{slug or 'screenplay'}-{selection.id}.pdf"


def render_pdf(selection):
    fonts()
    buffer = BytesIO()
    title = printable(selection_title(selection))
    document = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=72, rightMargin=60,
        topMargin=54, bottomMargin=54, title=title, author="", creator="", subject="",
        invariant=1, pageCompression=1)
    story = []
    if title.strip():
        story.append(ScriptText(title, bold=True, size=16, heading=True))
    for scene in selection.screenplay.scenes:
        heading = ScriptText(printable(scene.heading), bold=True, heading=True)
        blocks = [ScriptText(printable(b.text), speaker=printable(b.speaker) if b.kind == "dialogue" else "") for b in scene.blocks]
        heading.wrap(document.width - 12, 0)
        needed = heading.height + heading.spaceBefore + heading.spaceAfter
        if blocks:
            first = blocks[0]
            first.wrap(document.width - 12, 0)
            needed += (len(first.labels) + min(2, len(first.lines))) * first.leading
        # Reserve only the beginning of a scene, not its entire potentially long first block.
        story.extend([CondPageBreak(needed), heading, *blocks])

    def page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont("Screenplay", 10)
        canvas.drawRightString(A4[0] - 60, A4[1] - 30, str(doc.page))
        canvas.restoreState()

    document.build(story, onFirstPage=page_number, onLaterPages=page_number)
    return buffer.getvalue()
