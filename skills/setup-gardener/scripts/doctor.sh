#!/usr/bin/env bash
# Read-only health check of the MLE-setup install. Never writes or installs.
# Usage: bash doctor.sh    Exit code: 1 if any FAIL.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
FAILS=0 WARNS=0
ok()   { printf '  OK    %s\n' "$*"; }
warn() { printf '  WARN  %s\n' "$*"; WARNS=$((WARNS + 1)); }
fail() { printf '  FAIL  %s\n' "$*"; FAILS=$((FAILS + 1)); }
section() { printf '\n%s\n' "$*"; }

find_claude() {
  command -v claude 2>/dev/null && return
  ls -d "$HOME"/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude 2>/dev/null | tail -1
}

section "Source ($ROOT)"
if git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  dirty="$(git -C "$ROOT" status --porcelain | wc -l | tr -d ' ')"
  branch="$(git -C "$ROOT" branch --show-current)"
  ahead="$(git -C "$ROOT" rev-list --count '@{u}..HEAD' 2>/dev/null \
    || git -C "$ROOT" rev-list --count "origin/$branch..HEAD" 2>/dev/null || echo '?')"
  ok "branch $branch, $dirty uncommitted, $ahead unpushed"
else
  warn "not a git checkout: edits here are not versioned"
fi

section "Copilot CLI"
if command -v copilot >/dev/null 2>&1; then
  plugins="$(copilot plugin list 2>/dev/null)"
  for p in mle-setup superpowers ponytail; do
    grep -q "$p@" <<<"$plugins" && ok "plugin $p" || fail "plugin $p not installed"
  done
else
  warn "copilot not on PATH"
fi

section "Claude Code"
CLAUDE="$(find_claude)"
if [ -n "$CLAUDE" ]; then
  plugins="$("$CLAUDE" plugin list 2>/dev/null)"
  for p in mle-setup superpowers ponytail; do
    grep -q "$p@" <<<"$plugins" && ok "plugin $p" || warn "plugin $p not installed (/plugin)"
  done
  grep -q "mle-setup@" <<<"$plugins" || echo "        session-only alternative: claude --plugin-dir $ROOT"
else
  warn "claude CLI not found"
fi
if [ -f "$HOME/.claude/settings.json" ]; then
  n="$(python3 -c 'import json,sys;print(len(json.load(open(sys.argv[1])).get("permissions",{}).get("deny",[])))' \
    "$HOME/.claude/settings.json" 2>/dev/null || echo err)"
  case "$n" in
    err) fail "~/.claude/settings.json is not valid JSON" ;;
    0) warn "no permissions.deny rules (secrets readable)" ;;
    *) ok "$n permissions.deny rules" ;;
  esac
fi

section "Personal skill links"
for d in "$HOME/.copilot/skills" "$HOME/.claude/skills"; do
  [ -d "$d" ] || { warn "$d missing"; continue; }
  for l in "$d"/*; do
    [ -L "$l" ] || continue
    if [ -e "$l" ]; then ok "${l/#$HOME/~}"; else fail "broken link ${l/#$HOME/~} -> $(readlink "$l")"; fi
  done
done

section "office-docs brands"
if python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
  out="$(PYTHONPATH="$ROOT/skills/office-docs/scripts" python3 - <<'EOF'
from brand import brand_search_path, load_brand
for d in brand_search_path()[1:]:  # skip ./brands of the current directory
    if not d.is_dir():
        continue
    for b in sorted(p for p in d.iterdir() if (p / "brand.toml").is_file()):
        try:
            load_brand(b)
            print(f"OK {b.name} ({d})")
        except Exception as e:
            try:
                load_brand(b, allow_draft=True)
                print(f"WARN {b.name} is a draft: {e}")
            except Exception as e2:
                print(f"FAIL {b.name}: {e2}")
EOF
)"
  while read -r level msg; do
    case "$level" in OK) ok "$msg" ;; WARN) warn "$msg" ;; FAIL) fail "$msg" ;; esac
  done <<<"$out"
else
  warn "python3 >= 3.11 not found; brands not checked"
fi

section "Engram (optional memory)"
if command -v engram >/dev/null 2>&1; then
  ok "$(engram version 2>/dev/null)"
  data="${ENGRAM_DATA_DIR:-$HOME/.engram}"
  if [ -f "$data/engram.db" ]; then ok "db at ${data/#$HOME/~}"; else warn "no db yet at ${data/#$HOME/~}"; fi
  if [ "$(cd "$data" 2>/dev/null && git rev-parse --is-inside-work-tree 2>/dev/null)" = true ]; then
    fail "db dir ${data/#$HOME/~} is inside a git repo"
  fi
  for cfg in "$HOME/.copilot/mcp-config.json" "$HOME/.claude.json"; do
    if python3 -c 'import json,sys;sys.exit("engram" not in json.load(open(sys.argv[1])).get("mcpServers",{}))' "$cfg" 2>/dev/null; then
      ok "MCP registered in ${cfg/#$HOME/~}"
    else
      warn "MCP not registered in ${cfg/#$HOME/~}"
    fi
  done
  excl="$(git config --global core.excludesFile || echo "${XDG_CONFIG_HOME:-$HOME/.config}/git/ignore")"
  if grep -qxE '/?\.engram/?' "${excl/#\~/$HOME}" 2>/dev/null; then
    ok ".engram/ globally git-ignored"
  else
    warn ".engram/ not in global gitignore (${excl/#$HOME/~})"
  fi
  checks="$(engram doctor 2>/dev/null | grep '^\[')"
  issues="$(grep -vc '^\[ok\]' <<<"$checks")"
  if [ "$issues" -eq 0 ]; then ok "engram doctor: all checks ok"; else warn "engram doctor: $issues issue(s); run 'engram doctor'"; fi
else
  warn "engram not installed (optional)"
fi

printf '\n%s FAIL, %s WARN\n' "$FAILS" "$WARNS"
[ "$FAILS" -eq 0 ]
