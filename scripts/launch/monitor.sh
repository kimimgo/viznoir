#!/usr/bin/env bash
# parapilot Launch Monitor — 런치 준비 상태 자동 점검
# Cron: */4 * * * (4시간마다) or 수동 실행
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
ROADMAP="$SCRIPT_DIR/roadmap.json"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/monitor-$(date +%Y%m%d).log"
REPO="kimimgo/parapilot"
LAUNCH_DATE="2026-03-09"

mkdir -p "$LOG_DIR"

# Colors (skip in cron/pipe)
if [ -t 1 ]; then
  RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
  CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
else
  RED=''; GREEN=''; YELLOW=''; CYAN=''; BOLD=''; NC=''
fi

out() { echo -e "$*"; echo "$*" >> "$LOG_FILE"; }
log()  { out "[$(date '+%H:%M:%S')] $*"; }
pass() { out "  ${GREEN}[PASS]${NC} $*"; }
fail() { out "  ${RED}[FAIL]${NC} $*"; }
warn() { out "  ${YELLOW}[WARN]${NC} $*"; }
info() { out "  ${CYAN}[INFO]${NC} $*"; }

# ── D-Day countdown ──
today=$(date +%Y-%m-%d)
days_left=$(( ($(date -d "$LAUNCH_DATE" +%s) - $(date -d "$today" +%s)) / 86400 ))

out ""
out "${BOLD}═══════════════════════════════════════════════════${NC}"
out "${BOLD}  parapilot Launch Monitor — D-${days_left} (Launch: $LAUNCH_DATE)${NC}"
out "${BOLD}  $(date '+%Y-%m-%d %H:%M:%S KST')${NC}"
out "${BOLD}═══════════════════════════════════════════════════${NC}"

total=0; passed=0; failed=0

check() {
  local label="$1" cmd="$2"
  total=$((total + 1))
  if eval "$cmd" >/dev/null 2>&1; then
    pass "$label"
    passed=$((passed + 1))
  else
    fail "$label"
    failed=$((failed + 1))
  fi
}

# ── 1. Release & Distribution ──
log "1. Release & Distribution"
check "v0.1.0 GitHub Release exists" \
  "gh release view v0.1.0 --repo $REPO >/dev/null 2>&1"
check "PyPI package published" \
  "pip index versions mcp-server-parapilot 2>/dev/null | grep -q 'Available'"
check "pip install works" \
  "pip install --dry-run mcp-server-parapilot >/dev/null 2>&1"

# ── 2. OSS Infrastructure ──
log "2. OSS Infrastructure"
check "SECURITY.md exists" \
  "test -f $PROJECT_DIR/SECURITY.md"
check "CONTRIBUTING.md exists" \
  "test -f $PROJECT_DIR/CONTRIBUTING.md"
check "CHANGELOG.md exists" \
  "test -f $PROJECT_DIR/CHANGELOG.md"
check "CITATION.cff exists" \
  "test -f $PROJECT_DIR/CITATION.cff"
check "Issue templates exist" \
  "test -f $PROJECT_DIR/.github/ISSUE_TEMPLATE/bug_report.yml"
check "PR template exists" \
  "test -f $PROJECT_DIR/.github/PULL_REQUEST_TEMPLATE.md"
check "dependabot.yml exists" \
  "test -f $PROJECT_DIR/.github/dependabot.yml"
check "GitHub Discussions enabled" \
  "gh api repos/$REPO --jq '.has_discussions' 2>/dev/null | grep -q 'true'"
check "GitHub Topics set (>5)" \
  "test \$(gh api repos/$REPO --jq '.topics | length' 2>/dev/null) -gt 5"

# ── 3. CI/CD Health ──
log "3. CI/CD Health"
check "Latest CI green" \
  "gh run list --repo $REPO --branch main --limit 1 --json conclusion --jq '.[0].conclusion' 2>/dev/null | grep -q 'success'"
check "publish.yml workflow exists" \
  "test -f $PROJECT_DIR/.github/workflows/publish.yml"

# ── 4. Content Assets ──
log "4. Content Assets"
check "Social Preview set" \
  "gh api repos/$REPO --jq '.has_social_preview' 2>/dev/null | grep -q 'true'"
check "Demo GIF exists" \
  "test -f $PROJECT_DIR/assets/demo.gif"
check "HN post draft ready" \
  "test -f $SCRIPT_DIR/posts/hn.md"
check "Reddit drafts ready" \
  "test -f $SCRIPT_DIR/posts/reddit.md"

# ── 5. MCP Registry ──
log "5. MCP Registry"
check "smithery.yaml in repo" \
  "test -f $PROJECT_DIR/smithery.yaml"
# Registry presence checks (best-effort, may need manual verification)
check "awesome-mcp-servers PR submitted" \
  "gh pr list --repo punkpeye/awesome-mcp-servers --author kimimgo --state all --json number --jq 'length' 2>/dev/null | grep -qv '^0$'"

# ── 6. Repo Metrics ──
log "6. Repo Metrics (informational)"
stars=$(gh api repos/$REPO --jq '.stargazers_count' 2>/dev/null || echo "?")
forks=$(gh api repos/$REPO --jq '.forks_count' 2>/dev/null || echo "?")
open_issues=$(gh api repos/$REPO --jq '.open_issues_count' 2>/dev/null || echo "?")
info "Stars: $stars | Forks: $forks | Open Issues: $open_issues"

# traffic (requires push access)
views=$(gh api repos/$REPO/traffic/views --jq '.count' 2>/dev/null || echo "?")
clones=$(gh api repos/$REPO/traffic/clones --jq '.count' 2>/dev/null || echo "?")
info "Views (14d): $views | Clones (14d): $clones"

# ── Summary ──
out ""
out "${BOLD}───────────────────────────────────────────────────${NC}"
pct=$( (( total > 0 )) && echo $((passed * 100 / total)) || echo 0 )

if [ "$failed" -eq 0 ]; then
  out "${GREEN}${BOLD}  LAUNCH READY: $passed/$total checks passed (${pct}%)${NC}"
elif [ "$days_left" -le 0 ]; then
  out "${RED}${BOLD}  LAUNCH DAY: $failed blockers remain! ($passed/$total, ${pct}%)${NC}"
elif [ "$days_left" -le 1 ]; then
  out "${RED}${BOLD}  D-${days_left} CRITICAL: $failed items not ready ($passed/$total, ${pct}%)${NC}"
else
  out "${YELLOW}${BOLD}  D-${days_left}: $passed/$total ready (${pct}%), $failed remaining${NC}"
fi
out "${BOLD}───────────────────────────────────────────────────${NC}"
out ""

# ── Roadmap task status (from JSON) ──
if command -v python3 >/dev/null 2>&1 && [ -f "$ROADMAP" ]; then
  log "Roadmap Task Summary:"
  python3 -c "
import json, sys
with open('$ROADMAP') as f:
    data = json.load(f)
for phase_key in ['prep', 'launch', 'post_launch']:
    phase = data['phases'][phase_key]
    tasks = phase['tasks']
    done = sum(1 for t in tasks if t['status'] == 'done')
    total = len(tasks)
    print(f\"  {phase['label']}: {done}/{total} done\")
    for t in tasks:
        icon = 'x' if t['status'] == 'done' else (' ' if t['status'] == 'todo' else '~')
        print(f\"    [{icon}] {t['priority']} {t['title']}\")
"
fi

exit $failed
