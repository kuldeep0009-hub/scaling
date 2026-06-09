import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from app.rag import attach_embeddings, build_index, embed_texts

DATA_DIR = Path("data")
RESUME_DIR = DATA_DIR / "resume"
SAFE_REPO_EXTENSIONS = {
    ".md",
    ".txt",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
}
SKIP_REPO_NAME_PARTS = {
    ".env",
    "secret",
    "token",
    "private",
    "key",
    "id_rsa",
    ".pem",
    ".pub",
}


def read_markdown_docs() -> list[dict[str, str]]:
    docs = []
    for path in sorted(DATA_DIR.glob("*.md")):
        docs.append(
            {
                "id": path.name.lower().replace(".", "-"),
                "title": path.name,
                "source": str(path),
                "text": path.read_text(),
            }
        )
    return docs


def read_resume_docs() -> list[dict[str, str]]:
    docs = []
    configured = [Path(value) for value in [os.getenv("RESUME_PATH", "")] if value]
    candidates = [*configured, *sorted(RESUME_DIR.glob("*.pdf")), *sorted(RESUME_DIR.glob("*.md"))]
    seen = set()
    for path in candidates:
        path = path.expanduser()
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen or not path.exists():
            continue
        seen.add(key)
        if path.suffix.lower() == ".pdf":
            text = extract_pdf_text(path)
        elif path.suffix.lower() in {".md", ".txt"}:
            text = path.read_text(errors="replace")
        else:
            continue
        docs.append(
            {
                "id": f"resume-{path.stem}".lower().replace(".", "-"),
                "title": f"Resume: {path.name}",
                "source": str(path),
                "text": text,
            }
        )
    return docs


def extract_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError("Install dependencies with `pip install -r requirements.txt` before ingesting PDF resumes.") from error
    reader = PdfReader(str(path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()


def fetch_text(url: str) -> str:
    request = Request(url, headers=github_headers())
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_json(url: str):
    return json.loads(fetch_text(url))


def github_headers() -> dict[str, str]:
    headers = {"user-agent": "ai-persona-ingest"}
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["authorization"] = f"Bearer {token}"
    return headers


def fetch_github_docs() -> list[dict[str, str]]:
    owner = os.getenv("GITHUB_OWNER", "").strip()
    if not owner:
        return []

    requested = [repo.strip() for repo in os.getenv("GITHUB_REPOS", "").split(",") if repo.strip()]
    try:
        repos = [{"name": name} for name in requested] if requested else fetch_json(f"https://api.github.com/users/{owner}/repos?per_page=100")
    except (HTTPError, URLError, TimeoutError):
        return []

    docs = []
    for repo in repos[:30]:
        name = repo["name"]
        parts = [f"Repository: {name}"]
        default_branch = "HEAD"
        try:
            meta = fetch_json(f"https://api.github.com/repos/{owner}/{name}")
            default_branch = meta.get("default_branch") or default_branch
            if meta.get("description"):
                parts.append(f"Description: {meta['description']}")
            if meta.get("language"):
                parts.append(f"Primary language: {meta['language']}")
        except (HTTPError, URLError, TimeoutError):
            pass
        try:
            readme = fetch_json(f"https://api.github.com/repos/{owner}/{name}/readme")
            parts.append("README:\n" + fetch_text(readme["download_url"]))
        except (HTTPError, URLError, TimeoutError):
            pass
        try:
            commits = fetch_json(f"https://api.github.com/repos/{owner}/{name}/commits?per_page=20")
            parts.append("Recent commits:\n" + "\n".join(f"- {item['commit']['message']}" for item in commits))
        except (HTTPError, URLError, TimeoutError, KeyError):
            pass
        repo_files = fetch_repo_files(owner, name, default_branch)
        if repo_files:
            parts.append("Repository files:\n" + "\n\n".join(repo_files))
        docs.append(
            {
                "id": f"github-{name}",
                "title": f"GitHub: {name}",
                "source": f"https://github.com/{owner}/{name}",
                "text": "\n\n".join(parts),
            }
        )
    return docs


def fetch_repo_files(owner: str, repo: str, branch: str) -> list[str]:
    try:
        tree = fetch_json(f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1")
    except (HTTPError, URLError, TimeoutError):
        return []
    files = []
    for item in tree.get("tree", []):
        file_path = item.get("path", "")
        if item.get("type") != "blob" or not should_ingest_repo_file(file_path, item.get("size", 0)):
            continue
        try:
            text = fetch_text(f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{file_path}")
        except (HTTPError, URLError, TimeoutError):
            continue
        files.append(f"File: {file_path}\n{text[:4000]}")
        if len(files) >= 20:
            break
    return files


def should_ingest_repo_file(file_path: str, size: int) -> bool:
    lowered = file_path.lower()
    name = Path(lowered).name
    if size > 60_000:
        return False
    if any(part in lowered for part in SKIP_REPO_NAME_PARTS):
        return False
    return Path(name).suffix in SAFE_REPO_EXTENSIONS


def main() -> None:
    documents = [*read_markdown_docs(), *read_resume_docs(), *fetch_github_docs()]
    index = build_index(documents)
    embedding_key = os.getenv("OPENAI_EMBEDDING_API_KEY", "")
    if embedding_key:
        model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        texts = [chunk["text"] for chunk in index["chunks"]]
        vectors = embed_texts(texts, api_key=embedding_key, model=model)
        index = attach_embeddings(index, vectors)
        print(f"Attached {len(vectors)} embeddings with {model}")
    DATA_DIR.mkdir(exist_ok=True)
    Path("data/corpus.json").write_text(json.dumps({"documents": documents}, indent=2))
    Path("data/index.json").write_text(json.dumps(index, indent=2))
    print(f"Indexed {len(documents)} documents into data/index.json")


if __name__ == "__main__":
    main()
