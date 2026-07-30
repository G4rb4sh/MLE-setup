#!/usr/bin/env bash
# MLE-setup SessionStart hook.
# Emits always-on content (gateway + simplicity + prefs) as
# additionalContext for Copilot, plus a reminder if there are lessons
# waiting to be digested. Best-effort: it must never break session startup.
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTENT_FILE="$DIR/session-context.md"
LESSONS="$HOME/.mle-setup/lessons.md"

[ -f "$CONTENT_FILE" ] || { echo '{}'; exit 0; }
CONTEXT="$(cat "$CONTENT_FILE")"

# Reminder for undigested lessons (>= 5)
if [ -f "$LESSONS" ]; then
  COUNT=$(grep -cE '^[0-9]{4}-[0-9]{2}-[0-9]{2} \|' "$LESSONS" 2>/dev/null || echo 0)
  if [ "${COUNT:-0}" -ge 5 ] 2>/dev/null; then
    CONTEXT="${CONTEXT}

Setup notice: there are ${COUNT} undigested lessons in ~/.mle-setup/lessons.md. Suggest running the setup-gardener skill when it is a good time."
  fi
fi

# Serialize to JSON {"additionalContext": ...}. python3 ships with macOS.
if command -v python3 >/dev/null 2>&1; then
  CONTEXT="$CONTEXT" python3 -c 'import json,os,sys; sys.stdout.write(json.dumps({"additionalContext": os.environ["CONTEXT"]}))'
elif command -v node >/dev/null 2>&1; then
  CONTEXT="$CONTEXT" node -e 'process.stdout.write(JSON.stringify({additionalContext: process.env.CONTEXT}))'
else
  # No serializer available: skip injection instead of breaking.
  echo '{}'
fi
