#!/usr/bin/env node
// Copilot Studio agent team pipeline
// Pattern: msquaredplus/designthinking-team
import { spawnSync } from 'node:child_process';
import { readFileSync, mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Octokit } from '@octokit/rest';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');

// ── Config ────────────────────────────────────────────────────────────────────

const CLAUDE_BIN = process.env.CLAUDE_BIN || 'claude';
const MODEL = 'claude-sonnet-4-6';
const CONFIDENCE_THRESHOLD = 0.75;

const ISSUE_NUMBER = parseInt(process.env.ISSUE_NUMBER, 10);
const ISSUE_TITLE = process.env.ISSUE_TITLE || '';
const ISSUE_BODY = process.env.ISSUE_BODY || '';
const ISSUE_COMMENTS = process.env.ISSUE_COMMENTS || '';
const REPO = process.env.REPO || process.env.GITHUB_REPOSITORY || '';
const [REPO_OWNER, REPO_NAME] = REPO.split('/');

const octokit = new Octokit({ auth: process.env.GITHUB_TOKEN });

// ── Skills loader ─────────────────────────────────────────────────────────────

function loadSkills(...names) {
  return names
    .map(n => readFileSync(join(ROOT, 'skills', `${n}.md`), 'utf8'))
    .join('\n\n---\n\n');
}

function loadAgent(name) {
  return readFileSync(join(ROOT, 'agents', `${name}.md`), 'utf8');
}

const skills = loadSkills('copilot-studio', 'caveman');

// ── Claude CLI call ───────────────────────────────────────────────────────────

function runAgent(agentName, userMessage) {
  console.log(`\n[pipeline] Running ${agentName}...`);

  const systemPrompt = [skills, loadAgent(agentName)].join('\n\n---\n\n');

  const result = spawnSync(
    CLAUDE_BIN,
    [
      '--print',
      '--system-prompt', systemPrompt,
      '--model', MODEL,
      '--no-session-persistence',
      '--dangerously-skip-permissions',
      '--tools', '',
    ],
    {
      input: userMessage,
      encoding: 'utf-8',
      maxBuffer: 10 * 1024 * 1024,
      timeout: 300_000,
    }
  );

  if (result.status !== 0) {
    console.error(`[${agentName}] stderr:`, result.stderr);
    throw new Error(`Agent ${agentName} failed with status ${result.status}`);
  }

  const output = result.stdout.trim();
  console.log(`[${agentName}] output (${output.length} chars)`);
  return output;
}

// ── Caveman parser ────────────────────────────────────────────────────────────

function parseField(text, key) {
  const match = text.match(new RegExp(`^${key}:\\s*(.+)$`, 'm'));
  return match ? match[1].trim() : null;
}

function parseBool(text, key) {
  const val = parseField(text, key);
  return val === 'true';
}

function parseFloat_(text, key) {
  const val = parseField(text, key);
  return val ? parseFloat(val) : 0;
}

// ── GitHub helpers ────────────────────────────────────────────────────────────

async function postComment(body) {
  await octokit.issues.createComment({
    owner: REPO_OWNER,
    repo: REPO_NAME,
    issue_number: ISSUE_NUMBER,
    body,
  });
}

async function setLabel(label) {
  try {
    await octokit.issues.addLabels({
      owner: REPO_OWNER,
      repo: REPO_NAME,
      issue_number: ISSUE_NUMBER,
      labels: [label],
    });
  } catch (_) { /* label may not exist yet */ }
}

async function removeLabel(label) {
  try {
    await octokit.issues.removeLabel({
      owner: REPO_OWNER,
      repo: REPO_NAME,
      issue_number: ISSUE_NUMBER,
      name: label,
    });
  } catch (_) { /* ignore if not present */ }
}

// ── File parser (Generator output) ───────────────────────────────────────────

function parseGeneratedFiles(generatorOutput) {
  const files = {};
  const pattern = /=== FILE: (.+?) ===\n([\s\S]+?)(?==== FILE:|END)/g;
  let match;
  while ((match = pattern.exec(generatorOutput)) !== null) {
    const filename = match[1].trim();
    const content = match[2].trim();
    files[filename] = content;
  }
  return files;
}

// ── Output writer ─────────────────────────────────────────────────────────────

function writeOutputFiles(files) {
  const outDir = join(ROOT, 'output', `issue-${ISSUE_NUMBER}`);
  for (const [filename, content] of Object.entries(files)) {
    const fullPath = join(outDir, filename);
    mkdirSync(dirname(fullPath), { recursive: true });
    writeFileSync(fullPath, content, 'utf8');
    console.log(`[output] wrote ${filename}`);
  }
  return outDir;
}

function commitAndPush() {
  const run = (cmd, args) => {
    const r = spawnSync(cmd, args, { cwd: ROOT, encoding: 'utf-8' });
    if (r.status !== 0) throw new Error(`${cmd} failed: ${r.stderr}`);
  };
  run('git', ['config', 'user.email', 'copilot-bot@github.com']);
  run('git', ['config', 'user.name', 'Copilot Studio Bot']);
  run('git', ['add', `output/issue-${ISSUE_NUMBER}`]);
  run('git', ['commit', '-m', `feat: generate Copilot Studio package for issue #${ISSUE_NUMBER}`]);
  run('git', ['push']);
}

// ── Pipeline ──────────────────────────────────────────────────────────────────

async function main() {
  console.log(`[pipeline] Issue #${ISSUE_NUMBER}: ${ISSUE_TITLE}`);

  const issueContext = [
    `ISSUE #${ISSUE_NUMBER}: ${ISSUE_TITLE}`,
    `\nDESCRIPTION:\n${ISSUE_BODY}`,
    ISSUE_COMMENTS ? `\nCOMMENTS (user answers to clarification):\n${ISSUE_COMMENTS}` : '',
  ].filter(Boolean).join('\n\n---\n\n');

  // ── Stage 1: Analyst ────────────────────────────────────────────────────────
  const analysisOutput = runAgent('analyst', issueContext);

  const isComplete = parseBool(analysisOutput, 'IS_COMPLETE');
  const confidence = parseFloat_(analysisOutput, 'CONFIDENCE');
  const missing = parseField(analysisOutput, 'MISSING') || 'none';

  console.log(`[analyst] complete=${isComplete}, confidence=${confidence}, missing=${missing}`);

  // ── Stage 2: Clarifier (if needed) ──────────────────────────────────────────
  if (!isComplete || (confidence < CONFIDENCE_THRESHOLD && missing !== 'none')) {
    const clarifierInput = [
      `ANALYSIS OUTPUT:\n${analysisOutput}`,
      `ISSUE CONTEXT:\n${issueContext}`,
    ].join('\n\n---\n\n');

    const clarificationComment = runAgent('clarifier', clarifierInput);

    await setLabel('awaiting-info');
    await removeLabel('generating');
    await postComment(clarificationComment);
    console.log('[pipeline] Clarification posted. Waiting for user response.');
    process.exit(0);
  }

  // ── Stage 3: Architect ───────────────────────────────────────────────────────
  await setLabel('generating');
  await removeLabel('awaiting-info');

  const architectInput = [
    `ANALYSIS OUTPUT:\n${analysisOutput}`,
    `ISSUE CONTEXT:\n${issueContext}`,
  ].join('\n\n---\n\n');

  const blueprintOutput = runAgent('architect', architectInput);

  // ── Stage 4: Generator ───────────────────────────────────────────────────────
  const generatorInput = [
    `BLUEPRINT:\n${blueprintOutput}`,
    `ANALYSIS:\n${analysisOutput}`,
  ].join('\n\n---\n\n');

  const generatorOutput = runAgent('generator', generatorInput);
  const files = parseGeneratedFiles(generatorOutput);

  console.log(`[generator] ${Object.keys(files).length} files: ${Object.keys(files).join(', ')}`);

  if (Object.keys(files).length === 0) {
    throw new Error('Generator produced no files — check agent output');
  }

  // ── Write & commit ────────────────────────────────────────────────────────────
  writeOutputFiles(files);
  commitAndPush();

  // ── Stage 5: Orchestrator (completion comment) ────────────────────────────────
  const fileList = Object.keys(files).map(f => `- \`output/issue-${ISSUE_NUMBER}/${f}\``).join('\n');
  const connectorWarnings = Object.entries(files)
    .filter(([, c]) => c.includes('<connector_logical_name>'))
    .map(([f]) => `- ⚠️ \`${f}\`: Replace \`<connector_logical_name>\` with your actual connector ID from Copilot Studio portal.`);

  const orchestratorInput = [
    `ISSUE #${ISSUE_NUMBER}: ${ISSUE_TITLE}`,
    `ANALYSIS:\n${analysisOutput}`,
    `BLUEPRINT:\n${blueprintOutput}`,
    `GENERATED FILES:\n${fileList}`,
    `OUTPUT PATH: output/issue-${ISSUE_NUMBER}/`,
    connectorWarnings.length ? `WARNINGS:\n${connectorWarnings.join('\n')}` : 'WARNINGS: none',
  ].join('\n\n---\n\n');

  const completionComment = runAgent('orchestrator', orchestratorInput);

  await removeLabel('generating');
  await setLabel('copilot-generated');
  await postComment(completionComment);

  console.log('[pipeline] Done!');
}

main().catch(err => {
  console.error('[pipeline] Fatal error:', err);
  process.exit(1);
});
