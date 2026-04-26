# Blockchain Voting System

An educational blockchain-based voting prototype written in Python. Votes are submitted to a pending pool, validators create blocks using a simple Proof of Authority consensus mechanism, and P2P nodes share blocks and votes with each other.

The project demonstrates the core ideas behind blockchain voting:

- one-vote-per-voter protection;
- confirmed votes stored in a blockchain;
- chain integrity checks through block hashes;
- Proof of Authority with round-robin validator rotation;
- Merkle proofs for verifying that a vote was included in a block;
- a local CLI client and Flask API for node interaction.

## Project Structure

```text
.
├── app.py                 # starts a Flask P2P node
├── demo.py                # local demo without HTTP servers
├── run_nodes_test.sh      # smoke test with three local nodes
├── core/
│   ├── block.py           # block model
│   ├── blockchain.py      # blockchain storage and integrity checks
│   └── merkle.py          # Merkle tree and proof verification
├── consensus/
│   └── poa.py             # Proof of Authority logic
├── voting/
│   ├── vote.py            # vote model
│   ├── vote_pool.py       # pending vote pool
│   └── ledger.py          # vote tallying and ledger audit
├── network/
│   ├── node.py            # P2P node behavior
│   └── routes.py          # HTTP API routes
└── client/
    ├── cli.py             # command-line client
    ├── client.py          # HTTP client wrapper
    └── verification.py    # receipts and audit helpers
```

## Installation

Python 3.10+ is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Dependencies:

- Flask
- requests

## Quick Demo

Run the local demo without starting any servers:

```bash
python demo.py
```

The demo:

1. Creates a blockchain, vote pool, and PoA validator.
2. Submits several votes.
3. Tests double-vote prevention.
4. Creates a block containing the votes.
5. Verifies the PoA signature.
6. Verifies a Merkle proof for one vote.
7. Prints election results and a ledger audit.

## Running Three Local Nodes

Use the smoke-test script:

```bash
./run_nodes_test.sh
```

The script starts three nodes:

- `node1` on `localhost:5001`
- `node2` on `localhost:5002`
- `node3` on `localhost:5003`

It then submits two votes, waits for a block to be produced, prints node status, shows election results, verifies the first vote receipt, and runs an audit.

## Manual Node Startup

Run each command in a separate terminal:

```bash
python app.py --node-id node1 --port 5001 \
  --validators node1,node2,node3 \
  --peers localhost:5002,localhost:5003
```

```bash
python app.py --node-id node2 --port 5002 \
  --validators node1,node2,node3 \
  --peers localhost:5001,localhost:5003
```

```bash
python app.py --node-id node3 --port 5003 \
  --validators node1,node2,node3 \
  --peers localhost:5001,localhost:5002
```

The default shared PoA secret is:

```text
shared_poa_secret_2024
```

You can override it with the `--secret` argument.

## CLI Usage

Submit a vote:

```bash
python client/cli.py --node http://localhost:5001 vote \
  --voter-id voter001 \
  --candidate Alice \
  --salt 2024
```

The CLI returns a `vote_id`. Save it so you can later verify that the vote was included in a block.

Verify a vote:

```bash
python client/cli.py --node http://localhost:5001 verify \
  --vote-id <vote_id>
```

Show results:

```bash
python client/cli.py --node http://localhost:5001 results
```

Show node status:

```bash
python client/cli.py --node http://localhost:5001 status
```

Run an audit:

```bash
python client/cli.py --node http://localhost:5001 audit
```

## HTTP API

Main node endpoints:

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/ping` | Check whether the node is alive |
| `GET` | `/status` | Node status, chain height, peers, and next validator |
| `GET` | `/peers` | List known peers |
| `POST` | `/peers/register` | Register a peer node |
| `GET` | `/chain` | Return the current blockchain |
| `POST` | `/votes/submit` | Submit a new vote |
| `POST` | `/votes/receive` | Receive a vote from another node |
| `GET` | `/votes/pending` | Return pending votes |
| `POST` | `/blocks/receive` | Receive a block from another node |
| `GET` | `/verify/<vote_id>` | Return a receipt and Merkle proof |
| `GET` | `/results` | Return tally results and audit data |
| `GET` | `/ledger/validate` | Validate the ledger |
| `GET` | `/log` | Return the vote pool audit log |

Example vote submission through HTTP:

```bash
curl -X POST http://localhost:5001/votes/submit \
  -H "Content-Type: application/json" \
  -d '{
    "vote_id": "example-vote-id",
    "voter_id": "example-voter-hash",
    "voter_hash": "example-voter-salted-hash",
    "candidate": "Alice",
    "timestamp": 1710000000
  }'
```

In normal use, the CLI is easier because it creates the vote payload automatically.

The vote pool audit log records every submission attempt with:

- timestamp;
- event status, such as `accept`, `reject`, or `confirmed`;
- `vote_id`;
- hashed `voter_id`;
- salted `voter_hash`;
- selected candidate;
- `vote_hash`, a SHA-256 hash of the submitted vote payload.

## Voting Flow

1. The client creates a vote with `Vote.create(...)`.
2. The real voter id is hashed and is not stored in plain text.
3. The node checks that the candidate is valid and that the voter has not already voted.
4. The vote is added to `VotePool`.
5. The node broadcasts the vote to its peers.
6. When a validator's turn arrives, it collects pending votes into a block.
7. The block is signed with the PoA signature and appended to the chain.
8. The node broadcasts the block to its peers.
9. Other nodes validate the PoA signature, block index, previous hash, and block hash.
10. Once confirmed, the vote can be verified by its `vote_id`.

## Proof of Authority

Validators are configured with a comma-separated list:

```text
node1,node2,node3
```

Blocks are produced in round-robin order:

```text
block #1 -> node1
block #2 -> node2
block #3 -> node3
block #4 -> node1
...
```

This prototype signs blocks with HMAC-SHA256 and a shared secret. In a production system, this should be replaced with real public/private key signatures such as ECDSA or Ed25519.

## Vote Verification

After a vote is submitted, it receives a `vote_id`. Once the vote is included in a block, this endpoint:

```text
/verify/<vote_id>
```

returns:

- block index;
- block hash;
- validator id;
- Merkle root;
- Merkle proof.

The local Merkle proof check verifies that the given `vote_id` belongs to the set of votes stored in that block.

## Limitations

This is a demonstration project, not a production-ready voting system.

Important limitations:

- no real cryptographic voter identity;
- all validators share the same PoA secret;
- no database or persistent storage;
- restarting a node resets its in-memory blockchain;
- no Sybil resistance or advanced network conflict handling;
- synchronization uses the longest valid chain rule;
- Flask's development server is not suitable for production.

## Health Checks

Useful commands:

```bash
python demo.py
python -m compileall app.py demo.py core consensus voting network client
./run_nodes_test.sh
```

If everything works, the demo ends with `Demo complete!`, and the smoke test prints election results, a successful Merkle verification, and `Audit: PASSED`.

![Cat](assets/cat.gif)
![not Cat](assets/cute.gif)
