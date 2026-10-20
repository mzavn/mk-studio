#!/usr/bin/env bash
# Install a skill of mk-studio (copies, never symlinks). Safe to re-run: missing pieces are added, existing ones kept or updated.
#   --skill <name>    → which skill folder (default mk-star; also --skill=<name>); the ones below say mk-star, read <name>
#   --global          → ~/.claude/skills/mk-star and ~/.agents/skills/mk-star
#   --project <dir>   → <dir>/.claude/skills/mk-star (only the skill folder — no config, no agent files)
#   --agents-dir      → with --project: also copy to <dir>/.agents/skills/mk-star (kept up to date once present)
#   --update          → first pull the latest release (fast-forward `main`), then install; alone = --update --global.
#                       Without --skill: refreshes every skill install.sh put there (mk-star if none yet)
#   --force           → overwrite a project copy that has local edits, or a skill folder install.sh did not create
#   --uninstall       → remove instead of install (with --global and/or --project)
# Flags combine: install.sh --update --global --project .
# The repo is private: gh repo clone mzavn/mk-studio ~/.mk-studio && bash ~/.mk-studio/install.sh --global
#   (run from elsewhere, e.g. piped, it clones to $MK_STUDIO_HOME, default ~/.mk-studio, then runs from there)
set -euo pipefail

DEFAULT_SKILL=mk-star
# Piped (`… | bash`) → BASH_SOURCE is empty: never trust the current directory, always bootstrap from the clone.
SELF="${BASH_SOURCE[0]:-}"
ROOT=""
if [ -n "$SELF" ] && [ -f "$SELF" ]; then ROOT="$(cd "$(dirname "$SELF")" && pwd)"; fi
MANIFEST=.mk-studio-manifest
SOURCE_FILE=.mk-studio-source  # global copies only: path of the mk-studio checkout, so agents can suggest the update command
REPO_URL="${MK_STUDIO_REPO:-https://github.com/mzavn/mk-studio.git}"
ARGS=("$@")

# The comment block at the top of this file, whatever its length.
usage() { awk 'NR == 1 { next } !/^#/ { exit } { sub(/^# ?/, ""); print }' "$ROOT/install.sh" 2>/dev/null; exit "${1:-0}"; }
die() { echo "install.sh: $*" >&2; exit 1; }
skill_list() {
  local f
  for f in "$ROOT"/skills/*/SKILL.md; do [ -f "$f" ] && basename "$(dirname "$f")"; done | LC_ALL=C sort | paste -sd, - | sed 's/,/, /g'
}
die_skill() { die "$* (skills: $(skill_list))"; }

# Code fetched from the remote runs only when it is a release: `main` holds tagged releases (vX.Y.Z) only.
require_release() {
  git -C "$1" tag --points-at HEAD | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$' ||
    die "$1 is not at a release tag (vX.Y.Z) — refusing to run unreleased code; check its remote and branch (main)"
}

# Not run from a checkout: clone or refresh $MK_STUDIO_HOME and run the installer from there.
if [ -z "$ROOT" ] || [ ! -f "$ROOT/skills/$DEFAULT_SKILL/SKILL.md" ]; then
  command -v git >/dev/null || die "git is required"
  home="${MK_STUDIO_HOME:-$HOME/.mk-studio}"
  if [ -d "$home/.git" ]; then
    git -C "$home" pull --ff-only -q || die "cannot fast-forward $home; fix or delete it, then re-run"
  else
    git clone -q --depth 1 "$REPO_URL" "$home" ||
      die "cannot clone $REPO_URL (private repo: gh auth login, then gh repo clone mzavn/mk-studio $home)"
  fi
  require_release "$home"
  MK_STUDIO_UPDATED=1 exec bash "$home/install.sh" ${ARGS[@]+"${ARGS[@]}"}
fi

# Only the syntax of --skill is checked here: the skill may exist only after --update has pulled.
set_skill() {
  [ -z "$SKILL_ARG" ] || die_skill "--skill given more than once"
  printf '%s\n' "$1" | grep -qE '^[a-z0-9][a-z0-9-]*$' || die_skill "--skill needs a skill name, got '$1'"
  SKILL_ARG="$1"
}

GLOBAL=0 FORCE=0 UNINSTALL=0 UPDATE=0 AGENTS_DIR=0 PROJECTS=() SKILL_ARG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --global) GLOBAL=1 ;;
    --project) [ $# -ge 2 ] || die "--project needs a directory"; PROJECTS+=("$2"); shift ;;
    --project=*) PROJECTS+=("${1#--project=}") ;;
    --skill) [ $# -ge 2 ] || die_skill "--skill needs a skill name"; set_skill "$2"; shift ;;
    --skill=*) set_skill "${1#--skill=}" ;;
    --force) FORCE=1 ;;
    --agents-dir) AGENTS_DIR=1 ;;
    --uninstall) UNINSTALL=1 ;;
    --update) UPDATE=1 ;;
    -h|--help) usage 0 ;;
    *) echo "install.sh: unknown option: $1" >&2; usage 1 ;;
  esac
  shift
done
if [ "$UPDATE" = 1 ]; then
  [ "$UNINSTALL" = 0 ] || die "--update and --uninstall do not combine"
  [ "$GLOBAL" = 1 ] || [ ${#PROJECTS[@]} -gt 0 ] || GLOBAL=1
  if [ -z "${MK_STUDIO_UPDATED:-}" ]; then
    git -C "$ROOT" rev-parse --git-dir >/dev/null 2>&1 ||
      die "--update needs a git checkout of mk-studio ($ROOT is not one); reinstall with: gh repo clone mzavn/mk-studio ~/.mk-studio"
    before="$(git -C "$ROOT" rev-parse --short HEAD)"
    git -C "$ROOT" pull --ff-only -q ||
      die "cannot fast-forward $ROOT (local commits or edits?); resolve them, then re-run"
    require_release "$ROOT"
    echo "mk-studio: $before → $(git -C "$ROOT" rev-parse --short HEAD)"
    MK_STUDIO_UPDATED=1 exec bash "$ROOT/install.sh" "${ARGS[@]}"  # the installer itself may have changed
  fi
fi
if [ -n "$SKILL_ARG" ] && [ ! -f "$ROOT/skills/$SKILL_ARG/SKILL.md" ]; then die_skill "no skill named '$SKILL_ARG'"; fi
[ "$GLOBAL" = 1 ] || [ ${#PROJECTS[@]} -gt 0 ] || usage 1

version_of() {
  [ -f "$1/SKILL.md" ] && grep -m1 -E '^[[:space:]]*version:' "$1/SKILL.md" | sed -E 's/.*version:[[:space:]]*"?([^"]*)"?.*/\1/' || echo none
}

# Checksum list of the installed files (manifest itself and caches excluded).
manifest_of() {
  (cd "$1" && find . -type f ! -name "$MANIFEST" ! -name "$SOURCE_FILE" ! -name '.DS_Store' ! -path '*/__pycache__/*' -print | LC_ALL=C sort |
    while IFS= read -r f; do printf '%s %s\n' "$(cksum < "$f" | tr -s ' ' | cut -d' ' -f1,2)" "$f"; done)
}

no_symlink() {
  if [ -L "$1" ]; then die "$1 is a symlink — replace it with a real folder (install.sh never writes or deletes through symlinks)"; fi
}

# Never replace or remove a skill folder install.sh did not create (no manifest), unless --force.
# Every destination of one place is checked before any of them is written or removed.
refuse_foreign() {
  local d
  [ "$FORCE" != 1 ] || return 0
  for d in "$@"; do
    if [ -e "$d" ] && [ ! -f "$d/$MANIFEST" ]; then
      die "$d was not installed by install.sh (no $MANIFEST) — it may belong to another tool; move it away or re-run with --force"
    fi
  done
}

copy_skill() {
  local dest="$1" tmp
  no_symlink "$dest"
  mkdir -p "$(dirname "$dest")"
  tmp="$(mktemp -d "$(dirname "$dest")/.$SKILL.XXXXXX")"
  (cd "$SRC" && tar cf - --exclude '__pycache__' --exclude '.DS_Store' .) | (cd "$tmp" && tar xf -)
  manifest_of "$tmp" > "$tmp/$MANIFEST"
  rm -rf "$dest"
  mv "$tmp" "$dest"
}

# Local edits = files that differ from what install.sh last wrote (the manifest), whether committed or not: an
# update would overwrite them. A copy that still matches the manifest is always safe to replace. Prints the offending paths.
has_local_edits() {
  local dest="$1" changed
  [ -f "$dest/$MANIFEST" ] || return 1
  changed="$(diff <(cat "$dest/$MANIFEST") <(manifest_of "$dest") | sed -n 's/^[<>] [0-9]* [0-9]* \.\///p' | LC_ALL=C sort -u)"
  [ -n "$changed" ] || return 1
  printf '%s\n' "$changed" | sed 's/^/  /' >&2
}

refuse_edits() {
  die "$1 has edits not made by install.sh (listed above); an update would overwrite them.
  Keep a copy if needed, then re-run with --force."
}

use_skill() { SKILL="$1"; SRC="$ROOT/skills/$1"; VERSION="$(version_of "$SRC")"; }

# Skills to handle at one place, given its two skill folders minus the skill name ("$1/<skill>" "$2/<skill>"):
# --skill → that one; --update alone → every skill install.sh put there (manifest), or mk-star when none is there yet;
# otherwise mk-star. In C order.
skills_at() {
  local f s
  if [ -n "$SKILL_ARG" ]; then echo "$SKILL_ARG"; return; fi
  if [ "$UPDATE" != 1 ]; then echo "$DEFAULT_SKILL"; return; fi
  for f in "$ROOT"/skills/*/SKILL.md; do
    [ -f "$f" ] || continue
    s="$(basename "$(dirname "$f")")"
    if [ -f "$1/$s/$MANIFEST" ] || [ -f "$2/$s/$MANIFEST" ]; then echo "$s"; fi
  done | LC_ALL=C sort | grep . || echo "$DEFAULT_SKILL"
}

do_global() {
  local base dest old p
  for p in "$HOME/.claude" "$HOME/.claude/skills" "$HOME/.agents" "$HOME/.agents/skills" \
           "$HOME/.claude/skills/$SKILL" "$HOME/.agents/skills/$SKILL"; do no_symlink "$p"; done
  refuse_foreign "$HOME/.claude/skills/$SKILL" "$HOME/.agents/skills/$SKILL"
  for base in "$HOME/.claude/skills" "$HOME/.agents/skills"; do
    dest="$base/$SKILL"
    if [ "$UNINSTALL" = 1 ]; then
      if [ -e "$dest" ]; then rm -rf "$dest" && echo "removed $dest"; else echo "not installed: $dest"; fi
    else
      old="$(version_of "$dest")"
      copy_skill "$dest"
      echo "$ROOT" > "$dest/$SOURCE_FILE"
      echo "global: $dest ($old → $VERSION)"
    fi
  done
}

do_project() {
  local proj="$1" dest="$1/.claude/skills/$SKILL" agents="$1/.agents/skills/$SKILL" p old
  # Inside the project nothing on the path may be a symlink (a linked .claude/skills could point at the global copy).
  for p in "$proj/.claude" "$proj/.claude/skills" "$dest" "$proj/.agents" "$proj/.agents/skills" "$agents"; do no_symlink "$p"; done
  refuse_foreign "$dest" "$agents"
  if [ "$FORCE" != 1 ] && has_local_edits "$dest"; then refuse_edits "$dest"; fi
  if [ "$UNINSTALL" = 1 ]; then
    if [ -e "$dest" ]; then rm -rf "$dest" && echo "removed $dest"; else echo "not installed: $dest"; fi
    if [ -d "$agents" ]; then rm -rf "$agents" && echo "removed $agents"; fi
    return
  fi
  if [ "$FORCE" != 1 ] && has_local_edits "$agents"; then refuse_edits "$agents"; fi
  old="$(version_of "$dest")"
  copy_skill "$dest"
  echo "project: $dest ($old → $VERSION)"
  if [ "$AGENTS_DIR" = 1 ] || [ -d "$agents" ]; then
    copy_skill "$agents"
    echo "project: $agents ($VERSION)"
  fi
}

# Plan every (place, skill) first, print each skill's version once, then act place by place.
PLACES=() PLAN_SKILLS=()
if [ "$GLOBAL" = 1 ]; then
  for s in $(skills_at "$HOME/.claude/skills" "$HOME/.agents/skills"); do PLACES+=(""); PLAN_SKILLS+=("$s"); done
fi
for proj in ${PROJECTS[@]+"${PROJECTS[@]}"}; do
  [ -d "$proj" ] || die "project directory not found: $proj"
  proj="$(cd "$proj" && pwd)"
  for s in $(skills_at "$proj/.claude/skills" "$proj/.agents/skills"); do PLACES+=("$proj"); PLAN_SKILLS+=("$s"); done
done

for s in $(printf '%s\n' "${PLAN_SKILLS[@]}" | awk '!seen[$0]++'); do
  use_skill "$s"
  echo "$SKILL $VERSION"
done

i=0
while [ "$i" -lt ${#PLACES[@]} ]; do
  use_skill "${PLAN_SKILLS[$i]}"
  if [ -z "${PLACES[$i]}" ]; then do_global; else do_project "${PLACES[$i]}"; fi
  i=$((i + 1))
done
