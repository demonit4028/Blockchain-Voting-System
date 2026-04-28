# app.py
"""
Точка входа для каждого узла P2P-сети.

Пример запуска 3 узлов:
  python app.py --node-id node1 --port 5001 --validators node1,node2,node3 --peers localhost:5002,localhost:5003
  python app.py --node-id node2 --port 5002 --validators node1,node2,node3 --peers localhost:5001,localhost:5003
  python app.py --node-id node3 --port 5003 --validators node1,node2,node3 --peers localhost:5001,localhost:5002
"""
import argparse
import threading
import time

from flask import Flask, jsonify

from core.blockchain import Blockchain
from consensus.poa import ProofOfAuthority
from network.node import P2PNode
from network.routes import create_routes
from voting.vote_pool import VotePool
from voting.ledger import VoteLedger
from client.verification import VoteVerifier

CANDIDATES = ["Alice", "Bob", "Charlie"]
BLOCK_INTERVAL = 10  # секунд между блоками


def create_app(node_id, host, port, validators, secret_key, seed_peers):
    app = Flask(__name__)

    # ─── Инициализация компонентов ────────────────────────────────────────
    blockchain = Blockchain()
    vote_pool  = VotePool(candidates=CANDIDATES)
    poa        = ProofOfAuthority(validators, node_id, secret_key)
    verifier   = VoteVerifier(blockchain)
    ledger     = VoteLedger(blockchain)

    node = P2PNode(node_id=node_id, host=host, port=port)
    node.blockchain = blockchain
    node.vote_pool  = vote_pool
    node.poa        = poa

    # ─── Маршруты ─────────────────────────────────────────────────────────
    app.register_blueprint(create_routes(node))

    @app.route("/verify/<vote_id>")
    def verify(vote_id):
        return jsonify(verifier.generate_receipt(vote_id))

    @app.route("/results")
    def results():
        return jsonify({
            "tally": ledger.tally(),
            "audit": verifier.full_audit(),
        })

    @app.route("/ledger/validate")
    def validate_ledger():
        return jsonify(ledger.validate_ledger())

    # ─── Фоновый поток: создание блоков ──────────────────────────────────
    def block_producer():
        time.sleep(5)  # дадим узлу стартовать
        while True:
            time.sleep(BLOCK_INTERVAL)
            next_index = blockchain.height
            if poa.is_my_turn(next_index):
                pending = vote_pool.get_pending_votes(max_count=20)
                if pending:
                    # Filter out votes already confirmed on-chain (race guard)
                    confirmed_ids = {v["vote_id"] for v in blockchain.get_all_votes()}
                    pending = [v for v in pending if v["vote_id"] not in confirmed_ids]
                    if not pending:
                        continue
                    block = poa.create_block(
                        votes=pending,
                        previous_hash=blockchain.last_block.hash,
                        index=next_index,
                    )
                    if block and blockchain.add_block(block):
                        confirmed_ids = {v["vote_id"] for v in pending}
                        vote_pool.remove_votes(confirmed_ids)
                        node.broadcast_block(block)
                        print(
                            f"[{node_id}] ✅ Block {block.index} "
                            f"({len(pending)} votes) broadcast to {len(node.peers)} peers"
                        )

    if poa.is_authorized(node_id):
        threading.Thread(target=block_producer, daemon=True).start()

    # ─── Фоновый поток: обнаружение пиров и синхронизация ────────────────
    def startup():
        time.sleep(2)
        node.discover_peers(seed_peers)
        node.sync_chain()

    threading.Thread(target=startup, daemon=True).start()
    node.start_sync_loop(interval=30)

    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Blockchain Voting Node")
    parser.add_argument("--node-id",    required=True)
    parser.add_argument("--host",       default="localhost")
    parser.add_argument("--port",       type=int, default=5001)
    parser.add_argument("--validators", required=True,
                        help="Comma-separated validator IDs")
    parser.add_argument("--secret",     default="shared_poa_secret_2024")
    parser.add_argument("--peers",      default="",
                        help="Comma-separated seed peers (host:port)")
    args = parser.parse_args()

    validators  = args.validators.split(",")
    seed_peers  = [p for p in args.peers.split(",") if p]

    app = create_app(
        node_id    = args.node_id,
        host       = args.host,
        port       = args.port,
        validators = validators,
        secret_key = args.secret,
        seed_peers = seed_peers,
    )
    print(f"[{args.node_id}] Starting on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)