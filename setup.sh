#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
AGENT_SKILLS_DIR="$HOME/.agent/skills"

mkdir -p "$HOME/.agent"
ln -sfn "${SCRIPT_DIR}/skills" "$AGENT_SKILLS_DIR"

link_skills_target() {
  local target="$1"
  local entry
  local name

  mkdir -p "$(dirname "$target")"

  if [ -d "$target" ] && [ ! -L "$target" ]; then
    # Keep existing directories (for example ~/.codex/skills/.system)
    # and link each shared skill directly under the directory.
    rm -f "$target/skills"
    for entry in "$AGENT_SKILLS_DIR"/*; do
      [ -e "$entry" ] || continue
      name="$(basename "$entry")"
      if [ "$name" = "skills" ] && [ -L "$entry" ]; then
        continue
      fi
      ln -sfn "$entry" "$target/$name"
    done
    return
  fi

  ln -sfn "$AGENT_SKILLS_DIR" "$target"
}

link_skills_target "$HOME/.claude/skills"
link_skills_target "$HOME/.codex/skills"
link_skills_target "$HOME/.gemini/skills"
link_skills_target "$HOME/.copilot/skills"
