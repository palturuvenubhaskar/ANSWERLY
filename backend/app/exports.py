import io
import json
from docx import Document as DocxDocument
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def render_markdown(doc_title: str, items: list[dict]) -> str:
    lines = [f"# {doc_title}\n"]
    current_unit = None

    for item in items:
        unit = item.get("unit_name")
        if unit and unit != current_unit:
            lines.append(f"\n## {unit}\n")
            current_unit = unit

        q_num = item.get("question_number") or ""
        marks = item.get("marks")
        marks_label = f" [{marks} Marks]" if marks else ""
        lines.append(f"### Question {q_num}: {item.get('question_text')}{marks_label}\n")

        if item.get("is_unapproved"):
            lines.append("> **[DRAFT / MANUAL REVIEW REQUIRED]** This answer has not passed verification or approval.\n")

        answer = item.get("answer")
        if answer:
            if answer.get("introduction"):
                lines.append(f"{answer['introduction']}\n")

            for sec in answer.get("sections", []):
                lines.append(f"#### {sec.get('heading')}\n")
                lines.append(f"{sec.get('content')}\n")
                for bullet in sec.get("bullets", []):
                    lines.append(f"- {bullet}")
                if sec.get("formula"):
                    lines.append(f"\n$$\n{sec['formula']}\n$$\n")
                if sec.get("example"):
                    lines.append(f"\n*Example:* {sec['example']}\n")

            if answer.get("conclusion"):
                lines.append(f"\n**Conclusion:** {answer['conclusion']}\n")
        else:
            lines.append("*No generated answer available.*\n")

        lines.append("\n---\n")

    return "\n".join(lines)


def render_json(doc_title: str, items: list[dict]) -> bytes:
    payload = {
        "title": doc_title,
        "question_count": len(items),
        "items": items,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def render_docx(doc_title: str, items: list[dict]) -> bytes:
    doc = DocxDocument()
    doc.add_heading(doc_title, level=0)
    current_unit = None

    for item in items:
        unit = item.get("unit_name")
        if unit and unit != current_unit:
            doc.add_heading(unit, level=1)
            current_unit = unit

        q_num = item.get("question_number") or ""
        marks = item.get("marks")
        marks_str = f" [{marks} Marks]" if marks else ""
        q_heading = doc.add_heading(f"Q{q_num}. {item.get('question_text')}{marks_str}", level=2)

        if item.get("is_unapproved"):
            p_alert = doc.add_paragraph()
            run = p_alert.add_run("[DRAFT / MANUAL REVIEW REQUIRED] This answer has not been approved.")
            run.bold = True

        answer = item.get("answer")
        if answer:
            if answer.get("introduction"):
                doc.add_paragraph(answer["introduction"])

            for sec in answer.get("sections", []):
                doc.add_heading(sec.get("heading", "Details"), level=3)
                doc.add_paragraph(sec.get("content", ""))
                for bullet in sec.get("bullets", []):
                    doc.add_paragraph(bullet, style="List Bullet")
                if sec.get("formula"):
                    doc.add_paragraph(f"Formula: {sec['formula']}")
                if sec.get("example"):
                    doc.add_paragraph(f"Example: {sec['example']}")

            if answer.get("conclusion"):
                p_c = doc.add_paragraph()
                r_c = p_c.add_run(f"Conclusion: {answer['conclusion']}")
                r_c.italic = True
        else:
            doc.add_paragraph("No generated answer available.")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def render_pdf(doc_title: str, items: list[dict]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()

    story = []
    story.append(Paragraph(doc_title, styles["Title"]))
    story.append(Spacer(1, 14))

    current_unit = None
    for item in items:
        unit = item.get("unit_name")
        if unit and unit != current_unit:
            story.append(Spacer(1, 10))
            story.append(Paragraph(unit, styles["Heading1"]))
            story.append(Spacer(1, 6))
            current_unit = unit

        q_num = item.get("question_number") or ""
        marks = item.get("marks")
        marks_str = f" [{marks} Marks]" if marks else ""
        q_text = f"<b>Q{q_num}. {item.get('question_text')}</b>{marks_str}"
        story.append(Paragraph(q_text, styles["Heading2"]))
        story.append(Spacer(1, 4))

        if item.get("is_unapproved"):
            story.append(Paragraph("<font color='red'><b>[DRAFT / MANUAL REVIEW REQUIRED]</b></font>", styles["Normal"]))
            story.append(Spacer(1, 4))

        answer = item.get("answer")
        if answer:
            if answer.get("introduction"):
                story.append(Paragraph(answer["introduction"], styles["BodyText"]))
                story.append(Spacer(1, 4))

            for sec in answer.get("sections", []):
                story.append(Paragraph(f"<b>{sec.get('heading')}</b>", styles["Heading3"]))
                story.append(Paragraph(sec.get("content", ""), styles["BodyText"]))
                for bullet in sec.get("bullets", []):
                    story.append(Paragraph(f"&bull; {bullet}", styles["BodyText"]))
                if sec.get("formula"):
                    story.append(Paragraph(f"<i>Formula:</i> {sec['formula']}", styles["Italic"]))
                if sec.get("example"):
                    story.append(Paragraph(f"<i>Example:</i> {sec['example']}", styles["Italic"]))
                story.append(Spacer(1, 4))

            if answer.get("conclusion"):
                story.append(Paragraph(f"<b>Conclusion:</b> {answer['conclusion']}", styles["BodyText"]))
                story.append(Spacer(1, 6))
        else:
            story.append(Paragraph("<i>No generated answer available.</i>", styles["Italic"]))
            story.append(Spacer(1, 6))

    doc.build(story)
    return buf.getvalue()


def generate_export(doc_title: str, items: list[dict], export_format: str) -> tuple[bytes, str, str]:
    fmt = export_format.lower().strip()
    if fmt == "md" or fmt == "markdown":
        content = render_markdown(doc_title, items).encode("utf-8")
        return content, ".md", "text/markdown"
    elif fmt == "json":
        content = render_json(doc_title, items)
        return content, ".json", "application/json"
    elif fmt == "docx":
        content = render_docx(doc_title, items)
        return content, ".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif fmt == "pdf":
        content = render_pdf(doc_title, items)
        return content, ".pdf", "application/pdf"
    else:
        raise ValueError(f"Unsupported export format: {export_format}")
