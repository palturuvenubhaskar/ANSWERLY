import io
import re
from dataclasses import dataclass, field
import fitz  # PyMuPDF
from docx import Document as DocxDocument


@dataclass
class ExtractedQuestion:
    unit_name: str | None
    section: str | None
    question_number: str | None
    question_text: str
    original_text: str
    marks: int | None
    bl: str | None
    co: str | None
    source_page_start: int
    source_page_end: int
    source_excerpt: str
    confidence: float


@dataclass
class ExtractionResult:
    questions: list[ExtractedQuestion] = field(default_factory=list)
    units: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


UNIT_PATTERN = re.compile(
    r"^(?:UNIT|MODULE|CHAPTER)\s*[-:]?\s*([0-9IVXLCDM]+)[\s:.-]*(.*)$",
    re.IGNORECASE,
)
SECTION_PATTERN = re.compile(
    r"^(?:PART|SECTION)\s*[-:]?\s*([A-D])[\s:.-]*(.*)$",
    re.IGNORECASE,
)
QUESTION_START_PATTERN = re.compile(
    r"^(?:(?:Q|Question)\s*[\.:#]?\s*(\d+[a-z]?|\([a-z0-9]+\)|\b[0-9]+\b)|(\d{1,3})\s*[\.\)\]]\s+)",
    re.IGNORECASE,
)
MARKS_PATTERN = re.compile(
    r"(?:\[|\(|\b)(\d{1,3})\s*(?:M(?:arks?)?|marks?)\b(?:\s*\]|\)|\b)?",
    re.IGNORECASE,
)
BL_PATTERN = re.compile(
    r"\b(?:BL|Bloom['\s]?s(?:\s*Level)?)\s*[:=-]?\s*(L[1-6]|\d)\b",
    re.IGNORECASE,
)
CO_PATTERN = re.compile(
    r"\b(?:CO)\s*[:=-]?\s*(\d|CO\d)\b",
    re.IGNORECASE,
)


def validate_file_content(content: bytes, filename: str) -> tuple[str, str]:
    """Validates file magic bytes and returns (extension, mime_type)."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        if not content.startswith(b"%PDF-"):
            raise ValueError("File extension is .pdf but content is not a valid PDF")
        return ".pdf", "application/pdf"
    elif lower.endswith(".docx"):
        if not content.startswith(b"PK\x03\x04"):
            raise ValueError("File extension is .docx but content is not a valid zip archive")
        # Ensure it contains word/document.xml
        import zipfile

        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                namelist = zf.namelist()
                if not any("word/document.xml" in name for name in namelist):
                    raise ValueError("DOCX archive is missing word/document.xml")
        except zipfile.BadZipFile as e:
            raise ValueError("Corrupt DOCX file") from e
        return ".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        raise ValueError("Unsupported file type. Only PDF and DOCX files are allowed.")


def _parse_metadata_and_clean_text(raw_text: str) -> tuple[str, int | None, str | None, str | None, float]:
    """Extracts marks, Bloom's level, Course Outcome, and returns cleaned text with confidence."""
    text = raw_text.strip()
    marks = None
    bl = None
    co = None
    confidence = 0.90

    # Extract marks
    marks_match = MARKS_PATTERN.search(text)
    if marks_match:
        try:
            marks = int(marks_match.group(1))
            # Remove marks token from clean text
            text = text[: marks_match.start()] + text[marks_match.end() :]
        except ValueError:
            pass

    # Extract Bloom's level
    bl_match = BL_PATTERN.search(text)
    if bl_match:
        raw_bl = bl_match.group(1).upper()
        bl = raw_bl if raw_bl.startswith("L") else f"L{raw_bl}"
        text = text[: bl_match.start()] + text[bl_match.end() :]

    # Extract CO
    co_match = CO_PATTERN.search(text)
    if co_match:
        raw_co = co_match.group(1).upper()
        co = raw_co if raw_co.startswith("CO") else f"CO{raw_co}"
        text = text[: co_match.start()] + text[co_match.end() :]

    # Clean whitespace
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[\s,;:-]+$", "", text).strip()

    if len(text) < 10:
        confidence = 0.50

    return text, marks, bl, co, confidence


def extract_from_pdf(content: bytes) -> ExtractionResult:
    result = ExtractionResult()
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Failed to parse PDF document: {exc}") from exc

    current_unit = None
    current_section = None
    raw_blocks: list[tuple[str, int, int]] = []  # (text, page_start, page_end)

    for page_idx in range(len(doc)):
        page_num = page_idx + 1
        page = doc[page_idx]
        page_text = page.get_text()

        if len(page_text.strip()) < 25:
            # Check if page has images (scanned PDF page)
            images = page.get_images()
            if images:
                result.warnings.append(
                    f"Page {page_num} has low embedded text density ({len(page_text.strip())} chars) and contains scanned images. OCR fallback flagged."
                )

        lines = [line.strip() for line in page_text.splitlines() if line.strip()]
        for line in lines:
            # Check for Unit/Module heading
            unit_match = UNIT_PATTERN.match(line)
            if unit_match:
                current_unit = line
                if current_unit not in result.units:
                    result.units.append(current_unit)
                continue

            # Check for Section heading
            sec_match = SECTION_PATTERN.match(line)
            if sec_match:
                current_section = line
                continue

            # Check for Question start
            q_match = QUESTION_START_PATTERN.match(line)
            if q_match:
                raw_blocks.append((line, page_num, page_num))
            elif raw_blocks:
                # Continuation of prior question
                prev_text, p_start, _ = raw_blocks[-1]
                raw_blocks[-1] = (f"{prev_text} {line}", p_start, page_num)
            else:
                # Text before any question
                if len(line) > 20:
                    result.warnings.append(f"Uncategorized text on page {page_num}: '{line[:60]}...'")

    # Segment collected blocks into questions
    for idx, (raw_block, p_start, p_end) in enumerate(raw_blocks):
        q_match = QUESTION_START_PATTERN.match(raw_block)
        q_num = None
        cleaned_block = raw_block
        if q_match:
            q_num = (q_match.group(1) or q_match.group(2) or "").strip().rstrip(".):")
            cleaned_block = raw_block[q_match.end() :].strip()

        cleaned_text, marks, bl, co, confidence = _parse_metadata_and_clean_text(cleaned_block)
        if not cleaned_text:
            cleaned_text = raw_block

        result.questions.append(
            ExtractedQuestion(
                unit_name=current_unit,
                section=current_section,
                question_number=q_num or str(idx + 1),
                question_text=cleaned_text,
                original_text=raw_block,
                marks=marks,
                bl=bl,
                co=co,
                source_page_start=p_start,
                source_page_end=p_end,
                source_excerpt=raw_block[:300],
                confidence=confidence,
            )
        )

    return result


def extract_from_docx(content: bytes) -> ExtractionResult:
    result = ExtractionResult()
    try:
        doc = DocxDocument(io.BytesIO(content))
    except Exception as exc:
        raise ValueError(f"Failed to parse DOCX document: {exc}") from exc

    current_unit = None
    current_section = None
    raw_blocks: list[str] = []

    # Extract from paragraphs
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue

        unit_match = UNIT_PATTERN.match(text)
        if unit_match:
            current_unit = text
            if current_unit not in result.units:
                result.units.append(current_unit)
            continue

        sec_match = SECTION_PATTERN.match(text)
        if sec_match:
            current_section = text
            continue

        q_match = QUESTION_START_PATTERN.match(text)
        if q_match:
            raw_blocks.append(text)
        elif raw_blocks:
            raw_blocks[-1] = f"{raw_blocks[-1]} {text}"
        else:
            if len(text) > 20:
                result.warnings.append(f"Uncategorized text: '{text[:60]}...'")

    # Extract from tables if any
    for table in doc.tables:
        for row in table.rows:
            row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            combined = " ".join(row_texts)
            if combined and QUESTION_START_PATTERN.match(combined):
                raw_blocks.append(combined)

    for idx, raw_block in enumerate(raw_blocks):
        q_match = QUESTION_START_PATTERN.match(raw_block)
        q_num = None
        cleaned_block = raw_block
        if q_match:
            q_num = (q_match.group(1) or q_match.group(2) or "").strip().rstrip(".):")
            cleaned_block = raw_block[q_match.end() :].strip()

        cleaned_text, marks, bl, co, confidence = _parse_metadata_and_clean_text(cleaned_block)
        if not cleaned_text:
            cleaned_text = raw_block

        result.questions.append(
            ExtractedQuestion(
                unit_name=current_unit,
                section=current_section,
                question_number=q_num or str(idx + 1),
                question_text=cleaned_text,
                original_text=raw_block,
                marks=marks,
                bl=bl,
                co=co,
                source_page_start=1,
                source_page_end=1,
                source_excerpt=raw_block[:300],
                confidence=confidence,
            )
        )

    return result


def extract_document(content: bytes, filename: str) -> ExtractionResult:
    ext, _ = validate_file_content(content, filename)
    if ext == ".pdf":
        return extract_from_pdf(content)
    elif ext == ".docx":
        return extract_from_docx(content)
    else:
        raise ValueError("Unsupported document format")
