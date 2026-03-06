#!/usr/bin/env bash
# Update roadmap task status
# Usage: ./update-roadmap.sh <task-id> <status>
# Status: todo | in_progress | done | blocked
# Example: ./update-roadmap.sh pypi-trusted-publisher done
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROADMAP="$SCRIPT_DIR/roadmap.json"

if [ $# -lt 2 ]; then
  echo "Usage: $0 <task-id> <status>"
  echo "  status: todo | in_progress | done | blocked"
  echo ""
  echo "Available tasks:"
  python3 -c "
import json
with open('$ROADMAP') as f:
    data = json.load(f)
for phase in data['phases'].values():
    for t in phase['tasks']:
        icon = {'done':'v','in_progress':'~','blocked':'!','todo':' '}.get(t['status'],' ')
        print(f\"  [{icon}] {t['id']:30s} ({t['status']})\")
"
  exit 1
fi

TASK_ID="$1"
STATUS="$2"

if [[ ! "$STATUS" =~ ^(todo|in_progress|done|blocked)$ ]]; then
  echo "Error: status must be one of: todo, in_progress, done, blocked"
  exit 1
fi

python3 -c "
import json, sys
with open('$ROADMAP') as f:
    data = json.load(f)
found = False
for phase in data['phases'].values():
    for t in phase['tasks']:
        if t['id'] == '$TASK_ID':
            old = t['status']
            t['status'] = '$STATUS'
            found = True
            print(f\"Updated: {t['id']} ({old} -> $STATUS)\")
            break
if not found:
    print(f\"Error: task '$TASK_ID' not found\", file=sys.stderr)
    sys.exit(1)
with open('$ROADMAP', 'w') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
    f.write('\n')
"
