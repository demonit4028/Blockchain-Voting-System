#!/usr/bin/env bash
set -euo pipefail

VALIDATORS="node1,node2,node3"
SECRET="shared_poa_secret_2024"
PIDS=()

cleanup() {
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT

python app.py --node-id node1 --port 5001 --validators "$VALIDATORS" --secret "$SECRET" \
  --peers localhost:5002,localhost:5003 &
PIDS+=("$!")

python app.py --node-id node2 --port 5002 --validators "$VALIDATORS" --secret "$SECRET" \
  --peers localhost:5001,localhost:5003 &
PIDS+=("$!")

python app.py --node-id node3 --port 5003 --validators "$VALIDATORS" --secret "$SECRET" \
  --peers localhost:5001,localhost:5002 &
PIDS+=("$!")

echo "Nodes started. Waiting for startup..."
sleep 4

echo "Submitting votes..."
VOTE1_OUTPUT=$(python client/cli.py --node http://localhost:5001 vote \
  --voter-id "voter001" --candidate "Alice" --salt "2024")
echo "$VOTE1_OUTPUT"

python client/cli.py --node http://localhost:5002 vote \
  --voter-id "voter002" --candidate "Bob" --salt "2024"

VOTE_ID=$(printf '%s\n' "$VOTE1_OUTPUT" | sed -n 's/.*vote_id): //p' | tail -n 1)

echo "Waiting for a block..."
sleep 16

echo "Status:"
python client/cli.py --node http://localhost:5001 status

echo "Results:"
python client/cli.py --node http://localhost:5001 results

if [[ -n "$VOTE_ID" ]]; then
  echo "Verifying first vote:"
  python client/cli.py --node http://localhost:5001 verify --vote-id "$VOTE_ID"
fi

echo "Audit:"
python client/cli.py --node http://localhost:5001 audit
