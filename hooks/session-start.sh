#!/usr/bin/env bash
# MLE-setup SessionStart hook.
# Emits hooks/session-context.md as additionalContext.
# Best-effort: it must never break session startup.
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTENT_FILE="$DIR/session-context.md"

[ -f "$CONTENT_FILE" ] || { echo '{}'; exit 0; }
CONTEXT="$(cat "$CONTENT_FILE")"

# Claude Code expects hookSpecificOutput.additionalContext; Copilot CLI (sets
# COPILOT_CLI) expects top-level additionalContext. Emit only the one consumed.
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -z "${COPILOT_CLI:-}" ]; then
  FORMAT=claude
else
  FORMAT=copilot
fi

PY='import json,os,sys
c=os.environ["CONTEXT"]
o={"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":c}} if os.environ["FORMAT"]=="claude" else {"additionalContext":c}
sys.stdout.write(json.dumps(o))'
JS='const c=process.env.CONTEXT;process.stdout.write(JSON.stringify(process.env.FORMAT==="claude"?{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:c}}:{additionalContext:c}))'

if command -v python3 >/dev/null 2>&1; then
  CONTEXT="$CONTEXT" FORMAT="$FORMAT" python3 -c "$PY"
elif command -v node >/dev/null 2>&1; then
  CONTEXT="$CONTEXT" FORMAT="$FORMAT" node -e "$JS"
else
  # No serializer available: skip injection instead of breaking.
  echo '{}'
fi
