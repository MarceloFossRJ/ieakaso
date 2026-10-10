# CV parsing is deterministic code, not the agent

Every other Ieakaso feature runs through the agent, but the Parsed CV (`input/cv.md`) is produced by plain Python code (`ieakaso.cv_parser`). The same Source CV with the same parser version always gives byte-identical output, with the same words in the same order. Only declared structure (headings, lists, links, tables, footnotes) and documented character cleanups are added. The one exception to "same order" is footnote text: it follows the paragraph or table that references it, or the whole list, so an LLM reading a claim also reads its qualifier a line or two later (inline notes interrupt the sentence; notes at the end sit too far from their claim). The Parsed CV is generated, never edited by hand; to change it, the candidate changes the Source CV. We chose this because downstream modes judge the candidate against job ads based on this file, and an agent-written transcription can silently reword, drop or add content, which breaks the "never fabricate CV content" guardrail and makes scores impossible to reproduce.

## Considered Options

- **The agent reads the Source CV and writes the markdown.** Rejected: it reads layouts better, but it isn't repeatable and can't be tested against a stored expected output.
- **Guessing PDF structure from layout (font size gives headings, columns get reordered).** Rejected: deterministic, but it guesses at structure the file doesn't declare. PDFs come out as text blocks in the order the file stores them. Sorting blocks top-to-bottom was tried first and dropped: on two-column CVs it splits main-column sentences with sidebar text.
- **Pandoc for DOCX and TeX.** Rejected: every candidate would need a system install outside `uv`. TeX support stays limited to common commands, and an unknown command is a hard error.
- **OCR for scanned PDFs.** Rejected: recognition mistakes, and not reliably deterministic. The candidate is asked for a text-based file instead.
- **pdfplumber / pdfminer.six or pypdf for PDF.** Rejected in favour of PyMuPDF, which gives text blocks in stored order, link annotations and control over ligature expansion. Its AGPL licence matches this project's. DOCX uses `python-docx` (plus `lxml` for footnotes and text boxes), and TeX uses `pylatexenc`'s `LatexWalker` for parsing only.
- **Guessing the encoding of TXT files.** Rejected: TXT and Markdown Source CVs must be UTF-8 and not empty. A Markdown Source CV that meets this is copied byte for byte; one that doesn't is refused like any other unparseable CV, since an unreadable or empty Parsed CV would only fail later.

## Consequences

- Any change to the parser's output must raise `PARSER_VERSION` (in `ieakaso.cv_parser`) and update the stored expected test outputs in the same commit; `tests/fixtures/update_expected.py` refuses to change an output otherwise; the setup check then parses again.
- Odd layouts (two-column PDFs, custom TeX macros) produce awkward or failed output. The parser never "fixes" it; the candidate supplies a cleaner Source CV.
