#!/usr/bin/env bash
# Post-launch metrics tracker — stars, forks, traffic, issues
# Cron: 매 6시간 (런치 후 활성화)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
METRICS_LOG="$LOG_DIR/metrics.csv"
REPO="kimimgo/viznoir"
LAUNCH_DATE="2026-03-09"

mkdir -p "$LOG_DIR"

# CSV header if new
if [ ! -f "$METRICS_LOG" ]; then
  echo "timestamp,day,stars,forks,open_issues,views_14d,clones_14d,watchers" > "$METRICS_LOG"
fi

today=$(date +%Y-%m-%d)
day_num=$(( ($(date -d "$today" +%s) - $(date -d "$LAUNCH_DATE" +%s)) / 86400 ))

stars=$(gh api repos/$REPO --jq '.stargazers_count' 2>/dev/null || echo 0)
forks=$(gh api repos/$REPO --jq '.forks_count' 2>/dev/null || echo 0)
open_issues=$(gh api repos/$REPO --jq '.open_issues_count' 2>/dev/null || echo 0)
watchers=$(gh api repos/$REPO --jq '.subscribers_count' 2>/dev/null || echo 0)
views=$(gh api repos/$REPO/traffic/views --jq '.count' 2>/dev/null || echo 0)
clones=$(gh api repos/$REPO/traffic/clones --jq '.count' 2>/dev/null || echo 0)

ts=$(date '+%Y-%m-%d %H:%M:%S')
echo "$ts,D+$day_num,$stars,$forks,$open_issues,$views,$clones,$watchers" >> "$METRICS_LOG"

# Terminal output
echo "viznoir Metrics (D+$day_num, $ts)"
echo "  Stars: $stars | Forks: $forks | Watchers: $watchers"
echo "  Open Issues: $open_issues"
echo "  Views (14d): $views | Clones (14d): $clones"

# KPI alert
if [ "$day_num" -eq 7 ]; then
  if [ "$stars" -lt 10 ]; then
    echo "  [ALERT] D+7 stars < 10 — quiet launch, pivot strategy needed"
  elif [ "$stars" -ge 200 ]; then
    echo "  [GREAT] D+7 stars >= 200 — viral launch!"
  elif [ "$stars" -ge 50 ]; then
    echo "  [GOOD] D+7 stars >= 50 — successful launch"
  fi
fi

# New issues alert (last 24h)
new_issues=$(gh issue list --repo $REPO --state open --json createdAt --jq "[.[] | select(.createdAt > \"$(date -d '1 day ago' --iso-8601=seconds)\")] | length" 2>/dev/null || echo 0)
if [ "$new_issues" -gt 0 ]; then
  echo "  [ACTION] $new_issues new issues in last 24h — respond within 24h!"
fi
