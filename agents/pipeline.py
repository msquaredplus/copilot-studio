"""
Main orchestrator for the Copilot Studio agent team pipeline.
Runs via `claude -p` CLI — no API key required, uses existing claude login session.
"""
from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

from pydantic import ValidationError

from prompts import (
    ANALYST_SYSTEM,
    ARCHITECT_SYSTEM,
    CLARIFIER_SYSTEM,
    COMPLETION_COMMENT,
    GENERATOR_SYSTEM,
    AWAITING_INFO_LABEL,
    COMPLETED_LABEL,
    IN_PROGRESS_LABEL,
)
from schemas import AnalysisResult, GenerationResult, WorkflowRequirements

# ── Config ───────────────────────────────────────────────────────────────────

CONFIDENCE_THRESHOLD = 0.75


# ── GitHub helpers ────────────────────────────────────────────────────────────

def gh(cmd: str) -> str:
    result = subprocess.run(
        f"gh {cmd}", shell=True, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh command failed: {result.stderr}")
    return result.stdout.strip()


def get_issue(issue_number: int) -> dict:
    data = gh(f"issue view {issue_number} --json number,title,body,labels,comments")
    return json.loads(data)


def post_comment(issue_number: int, body: str) -> None:
    subprocess.run(
        ["gh", "issue", "comment", str(issue_number), "--body", body],
        check=True,
    )


def set_labels(issue_number: int, labels: list[str]) -> None:
    existing = gh(f"issue view {issue_number} --json labels")
    current = [l["name"] for l in json.loads(existing)["labels"]]
    all_labels = list(set(current + labels))
    gh(f"issue edit {issue_number} --add-label {','.join(all_labels)}")


def remove_label(issue_number: int, label: str) -> None:
    try:
        gh(f"issue edit {issue_number} --remove-label {label}")
    except RuntimeError:
        pass


def commit_output(issue_number: int, files: dict[str, str]) -> None:
    output_dir = Path(f"output/issue-{issue_number}")
    output_dir.mkdir(parents=True, exist_ok=True)

    for filename, content in files.items():
        file_path = output_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    subprocess.run(["git", "config", "user.email", "copilot-bot@github.com"], check=True)
    subprocess.run(["git", "config", "user.name", "Copilot Studio Bot"], check=True)
    subprocess.run(["git", "add", str(output_dir)], check=True)
    subprocess.run(
        ["git", "commit", "-m", f"feat: generate Copilot Studio package for issue #{issue_number}"],
        check=True,
    )
    subprocess.run(["git", "push"], check=True)


# ── Agent calls ───────────────────────────────────────────────────────────────

def call_agent(system: str, user_message: str, context: str | None = None) -> str:
    """Invoke claude CLI in non-interactive print mode."""
    parts = [system]
    if context:
        parts.append(f"Context:\n{context}")
    parts.append(user_message)
    full_prompt = "\n\n---\n\n".join(parts)

    result = subprocess.run(
        ["claude", "-p", full_prompt],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def extract_json(text: str) -> dict:
    """Extract JSON from model output, handling markdown code blocks."""
    import re
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        return json.loads(match.group(1))
    # Try raw JSON
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    raise ValueError(f"No JSON found in response: {text[:200]}")


# ── Agent: Analyst ────────────────────────────────────────────────────────────

def run_analyst(issue: dict) -> AnalysisResult:
    issue_text = f"""
Issue #{issue['number']}: {issue['title']}

Description:
{issue['body']}

Previous comments (if any):
{chr(10).join(c['body'] for c in issue.get('comments', []))}
""".strip()

    schema_hint = textwrap.dedent("""
    Return JSON with this structure:
    {
      "requirements": {
        "agent_name": "string or null",
        "agent_purpose": "string or null",
        "topics": [{"name": "str", "trigger_type": "OnRecognizedIntent", "trigger_phrases": [], "description": "str", "steps": []}],
        "actions": [],
        "integrations": [],
        "variables": [],
        "knowledge_sources": [],
        "auth_required": false,
        "language": "en",
        "raw_description": "original text"
      },
      "missing_fields": [{"field": "str", "question": "str", "why_needed": "str"}],
      "confidence": 0.0,
      "is_complete": false
    }
    """)

    raw = call_agent(
        ANALYST_SYSTEM,
        f"Analyze this issue and extract requirements:\n\n{issue_text}\n\n{schema_hint}",
    )

    data = extract_json(raw)
    return AnalysisResult(**data)


# ── Agent: Clarifier ──────────────────────────────────────────────────────────

def run_clarifier(analysis: AnalysisResult, issue: dict) -> str:
    context = f"Requirements extracted so far:\n{analysis.requirements.model_dump_json(indent=2)}"
    missing = json.dumps([q.model_dump() for q in analysis.missing_fields], indent=2)

    comment = call_agent(
        CLARIFIER_SYSTEM,
        f"Missing information:\n{missing}\n\nGenerate a GitHub comment asking for the missing details.",
        context=context,
    )
    return comment


# ── Agent: Architect ──────────────────────────────────────────────────────────

def run_architect(requirements: WorkflowRequirements) -> dict:
    blueprint_hint = textwrap.dedent("""
    Return a JSON blueprint:
    {
      "agent": { "display_name": "...", "schema_name": "...", "instructions": "...",
                 "conversation_starters": [], "model": "GPT4oChat", "language": 1033,
                 "authentication_mode": "None", "generative_actions_enabled": true },
      "topics": [...],
      "actions": [...]
    }
    """)

    raw = call_agent(
        ARCHITECT_SYSTEM,
        f"Design the Copilot Studio component blueprint for:\n\n"
        f"{requirements.model_dump_json(indent=2)}\n\n{blueprint_hint}",
    )
    return extract_json(raw)


# ── Agent: Generator ─────────────────────────────────────────────────────────

def run_generator(blueprint: dict, issue_number: int) -> GenerationResult:
    raw = call_agent(
        GENERATOR_SYSTEM,
        f"Generate all .mcs.yml files for this blueprint:\n\n"
        f"{json.dumps(blueprint, indent=2)}\n\n"
        f"Return JSON: {{ \"filename\": \"yaml content\", ... }}\n"
        f"Include agent.mcs.yml, settings.mcs.yml, and all topic/action files.",
    )

    files = extract_json(raw)
    warnings = []

    # Validate connector placeholders
    for fname, content in files.items():
        if "InvokeConnectorTaskAction" in content and "<connector_logical_name>" in content:
            warnings.append(
                f"`{fname}`: Replace `<connector_logical_name>` with your actual connector ID "
                "from Copilot Studio portal."
            )

    agent_name = blueprint.get("agent", {}).get("display_name", "Agent")
    return GenerationResult(
        issue_number=issue_number,
        files=files,
        summary=f"Generated Copilot Studio package for '{agent_name}' with "
                f"{len(files)} files: {', '.join(files.keys())}",
        warnings=warnings,
    )


# ── Pipeline orchestrator ─────────────────────────────────────────────────────

def run_pipeline(issue_number: int, event_type: str) -> None:
    print(f"[pipeline] Processing issue #{issue_number}, event: {event_type}")

    issue = get_issue(issue_number)
    current_labels = [l["name"] for l in issue.get("labels", [])]

    # Skip if already completed
    if COMPLETED_LABEL in current_labels:
        print("[pipeline] Issue already completed, skipping.")
        return

    # Step 1: Analyst
    print("[pipeline] Running Analyst...")
    analysis = run_analyst(issue)
    print(f"[pipeline] Confidence: {analysis.confidence:.0%}, Complete: {analysis.is_complete}")

    # Step 2: Check completeness
    if not analysis.is_complete or analysis.confidence < CONFIDENCE_THRESHOLD:
        if analysis.missing_fields:
            print(f"[pipeline] {len(analysis.missing_fields)} missing fields, asking clarification...")
            comment = run_clarifier(analysis, issue)
            post_comment(issue_number, comment)
            set_labels(issue_number, [AWAITING_INFO_LABEL])
            print("[pipeline] Clarification posted, waiting for user response.")
            return
        else:
            print("[pipeline] Low confidence but no missing fields, proceeding with caution...")

    # Step 3: Architect
    remove_label(issue_number, AWAITING_INFO_LABEL)
    set_labels(issue_number, [IN_PROGRESS_LABEL])
    print("[pipeline] Running Architect...")
    blueprint = run_architect(analysis.requirements)

    # Step 4: Generator
    print("[pipeline] Running Generator...")
    result = run_generator(blueprint, issue_number)

    # Step 5: Commit output
    print(f"[pipeline] Committing {len(result.files)} files...")
    commit_output(issue_number, result.files)

    # Step 6: Post completion comment
    file_list = "\n".join(f"- `output/issue-{issue_number}/{f}`" for f in result.files)
    warnings_text = "\n".join(f"- ⚠️ {w}" for w in result.warnings) if result.warnings else "None"

    comment = COMPLETION_COMMENT.format(
        file_list=file_list,
        issue_number=issue_number,
        warnings=warnings_text,
        summary=result.summary,
    )
    post_comment(issue_number, comment)

    remove_label(issue_number, IN_PROGRESS_LABEL)
    set_labels(issue_number, [COMPLETED_LABEL])
    print("[pipeline] Done!")


if __name__ == "__main__":
    issue_number = int(sys.argv[1])
    event_type = sys.argv[2] if len(sys.argv) > 2 else "opened"
    run_pipeline(issue_number, event_type)
