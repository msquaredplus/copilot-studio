# Copilot Studio Knowledge

## File Format: .mcs.yml
All Copilot Studio components use YAML with `.mcs.yml` extension.
Every file requires a `mcs.metadata.componentName` and a `kind` field.

## Component Kinds
- `GptComponentMetadata` — agent identity, instructions, model settings (agent.mcs.yml)
- `AdaptiveDialog` — conversation topic with triggers and actions (topics/*.topic.mcs.yml)
- `TaskDialog` — connector or MCP action (actions/*.mcs.yml)

## Trigger Types (AdaptiveDialog)
- `OnConversationStart` — fires when user opens conversation
- `OnRecognizedIntent` — fires when NLU matches trigger phrases
- `OnUnknownIntent` — fallback when no intent matched
- `OnError` — fires on runtime error

## Action Types
- `SendActivity` — send a message to user
- `Question` — ask user for input (text, number, boolean, choice)
- `ConditionGroup` — branching logic
- `SetVariable` — set a conversation variable
- `BeginDialog` — invoke another topic
- `EndDialog` — end conversation
- `InvokeConnectorTaskAction` — call Power Platform connector
- `InvokeExternalAgentTaskAction` — call MCP tool

## Required Topics (always generate these)
1. Greeting — `OnConversationStart`
2. Fallback — `OnUnknownIntent`
3. ErrorHandler — `OnError`

## Schema: agent.mcs.yml
```yaml
mcs.metadata:
  componentName: <schema_name>
kind: GptComponentMetadata
displayName: <display_name>
instructions: |
  <system_prompt>
conversationStarters:
  - title: <label>
    text: <utterance>
aISettings:
  model:
    modelNameHint: GPT4oChat
```

## Schema: settings.mcs.yml
```yaml
displayName: <display_name>
schemaName: <schema_name>
accessControlPolicy: ChatbotReaders
authenticationMode: None
configuration:
  settings:
    GenerativeActionsEnabled: true
  recognizer:
    kind: GenerativeAIRecognizer
language: 1033
```

## Schema: topic file
```yaml
mcs.metadata:
  componentName: <schema_name>_<TopicName>
kind: AdaptiveDialog
beginDialog:
  kind: OnRecognizedIntent
  id: main
  intent:
    displayName: <TopicName>
    triggerQueries:
      - <phrase1>
      - <phrase2>
  actions:
    - kind: SendActivity
      id: msg_1
      activity: <message>
```

## Schema: action file
```yaml
mcs.metadata:
  componentName: <schema_name>_<ActionName>
kind: TaskDialog
displayName: <ActionName>
inputs: []
outputs: []
actions:
  - kind: InvokeConnectorTaskAction
    id: action_1
    connectionReference:
      logicalName: <connector_logical_name>
    operationId: <operation_id>
    parameters: {}
```

## Rules
- schemaName: lowercase, underscores only (e.g. hr_support_bot)
- componentName: schemaName + underscore + PascalCase component
- All IDs must be unique within a file
- Use 2-space YAML indentation
- Connector actions: use `<connector_logical_name>` placeholder if unknown
- Every topic needs 3-5 triggerQueries for OnRecognizedIntent triggers
- Import via VS Code Power Platform Tools extension → syncPush
