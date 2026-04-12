#!/usr/bin/env node
// Shamash hook handler for Claude Code UserPromptSubmit events.
//
// Phase 1: retrieval with deliberation (Talmud layer).
// The query is passed to EDEN for coverage checking, knowledge surfacing,
// dissent detection, edge traversal, and precedent retrieval.
//
// Flow:
//   Claude Code -> stdin (hook JSON) -> this script
//   -> write query to temp file
//   -> eden --shamash-retrieve --query FILE --db ~/.eden/shamash.db
//   -> read context from stdout
//   -> format as hook response JSON -> stdout -> Claude Code
//
// Node.js handles JSON; EDEN handles the graph. Clean separation.
//
// Note: On MSYS2, Node.js (win32) needs explicit bash.exe path and
// MSYS2-native Unix paths for the eden binary.

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const EDEN_BIN = '/home/natanh/Adam/eden-idris/build/exec/eden.exe';
const DB_PATH = '/home/natanh/.eden/shamash.db';
const QUERY_FILE = '/tmp/shamash_query.txt';
const BASH = String.raw`C:\msys64\usr\bin\bash.exe`;

function sh(cmd, opts = {}) {
  return execSync(cmd, { shell: BASH, encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'], ...opts });
}

let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => { input += chunk; });
process.stdin.on('end', () => {
  try {
    const hookInput = JSON.parse(input);
    const prompt = hookInput.prompt || '';

    // Skip empty or trivial prompts
    if (!prompt || prompt.trim().length < 2) return;

    // Ensure DB directory exists
    try { sh('mkdir -p /home/natanh/.eden'); } catch (_) {}

    // Write query to temp file for EDEN deliberation
    try { sh('mkdir -p /tmp'); } catch (_) {}
    fs.writeFileSync(
      path.resolve(String.raw`C:\msys64\tmp\shamash_query.txt`),
      prompt.trim()
    );

    // Retrieve graph context with deliberation (Talmud layer)
    let context = sh(
      EDEN_BIN + ' --shamash-retrieve --query "' + QUERY_FILE + '" --db "' + DB_PATH + '"',
      { timeout: 8000 }
    ).trim();

    // Strip diagnostic lines and normalize line endings
    context = context.replace(/\r\n/g, '\n');
    const lines = context.split('\n');
    const ctxStart = lines.findIndex(l => l.startsWith('[Shamash Graph Context]'));
    const cleanContext = ctxStart >= 0 ? lines.slice(ctxStart).join('\n') : context;

    // Output hook response with graph context
    if (cleanContext && cleanContext.length > 0) {
      const output = {
        hookSpecificOutput: {
          hookEventName: 'UserPromptSubmit',
          additionalContext: cleanContext
        }
      };
      process.stdout.write(JSON.stringify(output));
    }
  } catch (e) {
    // Silent failure - never block the conversation.
    // Uncomment for debugging:
    // process.stderr.write(`shamash-hook error: ${e.message}\n`);
  }
});
