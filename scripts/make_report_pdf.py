from pathlib import Path
from textwrap import wrap

out = Path("outputs")
out.mkdir(exist_ok=True)
pdf_path = out / "eval-report.pdf"

content = [
    "Scaler AI Persona - Evaluation Report",
    "",
    "Voice quality: Measure first-response latency from call connect to first synthesized token, transcription accuracy with a 20-utterance script, and booking completion across test calls. Replace this paragraph with final numbers after live Vapi/Retell testing.",
    "",
    "Chat groundedness: Use evals/golden.json plus manual labels over resume/repo questions. Track hallucination rate, retrieval precision@5, and recall against expected source files. Retrieval is hybrid: lexical scoring plus optional stored embeddings.",
    "",
    "Failure modes: 1. Sparse corpus caused vague answers; fixed by ingesting README and commit messages. 2. Calendar credentials missing caused fake success risk; fixed by hard failure unless provider confirms. 3. Prompt injection attempted to override evidence; fixed with instruction hierarchy and refusal tests.",
    "",
    "Tradeoff: The system uses file-backed hybrid RAG instead of a vector database to fit Render's 512 MB memory limit. This preserves semantic recall when embeddings are enabled while keeping deployment simple.",
    "",
    "With two more weeks: add reranking, streaming voice responses, automated phone-call evals, Google Calendar OAuth, richer repo mining, and a hosted eval dashboard.",
]

def pdf_escape(text):
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

lines = []
for paragraph in content:
    if not paragraph:
        lines.append("")
    else:
        lines.extend(wrap(paragraph, 92))

stream_lines = ["BT", "/F1 10 Tf", "50 780 Td", "14 TL"]
for i, line in enumerate(lines[:52]):
    if i:
        stream_lines.append("T*")
    stream_lines.append(f"({pdf_escape(line)}) Tj")
stream_lines.append("ET")
stream = "\n".join(stream_lines).encode("latin-1")

objects = []
objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
objects.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>")
objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream")

pdf = bytearray(b"%PDF-1.4\n")
offsets = [0]
for idx, obj in enumerate(objects, start=1):
    offsets.append(len(pdf))
    pdf.extend(f"{idx} 0 obj\n".encode("latin-1"))
    pdf.extend(obj)
    pdf.extend(b"\nendobj\n")
xref = len(pdf)
pdf.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode("latin-1"))
for offset in offsets[1:]:
    pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
pdf.extend(f"trailer << /Root 1 0 R /Size {len(objects)+1} >>\nstartxref\n{xref}\n%%EOF\n".encode("latin-1"))

pdf_path.write_bytes(pdf)
print(pdf_path)
