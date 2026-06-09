import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.llm import answer_with_evidence
from app.rag import retrieve

REFUSAL_RE = re.compile(r"do not know|don't know|not enough|not supported|not have enough|cannot", re.I)


async def main() -> None:
    golden = json.loads(Path("evals/golden.json").read_text())
    results = []
    for item in golden:
        evidence = retrieve(item["question"])
        response = await answer_with_evidence([{"role": "user", "content": item["question"]}], evidence)
        refused = bool(REFUSAL_RE.search(response["answer"]))
        passed = refused if item.get("expectRefusal") else bool(evidence)
        results.append(
            {
                "id": item["id"],
                "question": item["question"],
                "retrieved": [chunk["title"] for chunk in evidence],
                "answer": response["answer"],
                "passed": passed,
            }
        )
    Path("outputs").mkdir(exist_ok=True)
    Path("outputs/eval-results.json").write_text(json.dumps(results, indent=2))
    for result in results:
        print(f"{result['id']}: {'PASS' if result['passed'] else 'FAIL'} ({len(result['retrieved'])} retrieved)")


if __name__ == "__main__":
    asyncio.run(main())
