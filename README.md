# Copilot Studio Automation Pipeline

Automated generation of Microsoft Copilot Studio agent packages from GitHub Issues.

Built on [microsoft/skills-for-copilot-studio](https://github.com/microsoft/skills-for-copilot-studio).

## How it works

```
GitHub Issue  →  Analyst  →  Clarifier (if needed)  →  Architect  →  Generator  →  .mcs.yml files
     ↑                           ↓
     └─── user answers questions ┘
```

1. **Create an issue** using the "Copilot Studio Workflow Request" template
2. The label `copilot-studio` triggers the pipeline automatically
3. The **Analyst Agent** extracts structured requirements from your description
4. If information is missing, the **Clarifier Agent** posts questions as a comment
5. Answer in a new comment — the pipeline re-runs automatically
6. Once complete, the **Architect Agent** designs the component structure
7. The **Generator Agent** produces valid `.mcs.yml` files
8. Files are committed to `output/issue-{number}/` and linked in the issue

## Generated file structure

```
output/issue-{number}/
├── agent.mcs.yml           # Agent identity & instructions
├── settings.mcs.yml        # Auth, language, recognizer
├── topics/
│   ├── Greeting.topic.mcs.yml
│   ├── Fallback.topic.mcs.yml
│   ├── ErrorHandler.topic.mcs.yml
│   └── {YourTopic}.topic.mcs.yml
└── actions/
    └── {YourAction}.mcs.yml
```

## Importing into Copilot Studio

1. Install the [Power Platform Tools](https://marketplace.visualstudio.com/items?itemName=microsoft-IsvExpTools.powerplatform-vscode) VS Code extension
2. Clone this repo and navigate to `output/issue-{number}/`
3. Connect to your Copilot Studio environment
4. Copy files into your agent workspace
5. Use `syncPush` to deploy to Copilot Studio

> **Note:** Connector actions require the connection reference to be created first
> in the Copilot Studio portal UI before the YAML can be synced.

## Setup

### Required secrets

| Secret | Description |
|--------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key for the agent team |

Add in: Repository → Settings → Secrets and variables → Actions

### Labels

The pipeline only processes issues with the `copilot-studio` label.

| Label | Meaning |
|-------|---------|
| `copilot-studio` | Issue is a workflow request (triggers pipeline) |
| `awaiting-info` | Agent team is waiting for more details |
| `generating` | Pipeline is running |
| `copilot-generated` | Package has been generated |

## Architecture

| Agent | Role |
|-------|------|
| **Analyst** | Parses issue text → structured `WorkflowRequirements` |
| **Clarifier** | Identifies gaps → posts GitHub comment with questions |
| **Architect** | Designs component blueprint (topics, actions, agent config) |
| **Generator** | Produces valid `.mcs.yml` YAML files |

All agents run on `claude-sonnet-4-6` via the Anthropic SDK.

## Templates

Base templates in `templates/` follow the official schema from
[microsoft/skills-for-copilot-studio](https://github.com/microsoft/skills-for-copilot-studio):

- `agent.mcs.yml` — `GptComponentMetadata`
- `settings.mcs.yml` — Auth & recognizer config
- `topics/greeting.topic.mcs.yml` — `OnConversationStart`
- `topics/fallback.topic.mcs.yml` — `OnUnknownIntent`
- `topics/error-handler.topic.mcs.yml` — `OnError`
- `actions/connector-action.mcs.yml` — `InvokeConnectorTaskAction`
- `actions/mcp-action.mcs.yml` — `InvokeExternalAgentTaskAction` (MCP)
