# Caveman Protocol — Inter-Agent Communication

Use minimal structured key:value blocks for agent output.
This keeps token count low and parsing reliable.

## Format Rules
- One key per line: `KEY: value`
- Multi-value lists: `KEY: item1 | item2 | item3`
- Multi-line values: indent continuation lines with two spaces
- Sections: `=== SECTION NAME ===`
- End marker: `END`

## Example
```
AGENT_NAME: HR Support Bot
AGENT_PURPOSE: Help employees with HR questions about leave, payroll, benefits
TOPICS: Leave Request | Payslip | Benefits Info | IT Support
INTEGRATIONS: SharePoint | SAP SuccessFactors
AUTH: None
LANGUAGE: 1033
IS_COMPLETE: true
CONFIDENCE: 0.9
MISSING: none
END
```

## Rules
- No prose, no markdown headers, no bullet points in structured output
- Keep values on one line where possible
- Boolean values: `true` or `false`
- Missing/unknown: use `none` or `unknown`
- Numbers as plain digits: `0.9` not `90%`
