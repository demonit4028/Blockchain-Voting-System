from flask import Blueprint, jsonify, request

from core.block import Block


def create_routes(node) -> Blueprint:
    bp = Blueprint("node", __name__)

    @bp.route("/ping", methods=["GET"])
    def ping():
        return jsonify({"node_id": node.node_id, "status": "alive"})

    @bp.route("/status", methods=["GET"])
    def status():
        return jsonify(
            {
                "node_id": node.node_id,
                "address": node.address,
                "chain_height": node.blockchain.height,
                "pending_votes": node.vote_pool.count(),
                "peers": list(node.peers),
                "is_validator": node.poa.is_authorized(node.node_id),
                "next_validator": node.poa.expected_validator(node.blockchain.height),
                **node.poa.get_status(),
            }
        )

    @bp.route("/peers", methods=["GET"])
    def get_peers():
        return jsonify({"peers": list(node.peers)})

    @bp.route("/peers/register", methods=["POST"])
    def register_peer():
        data = request.get_json() or {}
        address = data.get("address")
        if address:
            node.add_peer(address)
        return jsonify({"registered": address})

    @bp.route("/chain", methods=["GET"])
    def get_chain():
        return jsonify(node.blockchain.to_dict())

    @bp.route("/blocks/receive", methods=["POST"])
    def receive_block():
        data = request.get_json() or {}
        block = Block.from_dict(data)
        valid, reason = node.poa.validate_block(block)
        if not valid:
            return jsonify({"accepted": False, "reason": reason}), 400

        accepted = node.blockchain.add_block(block)
        if accepted:
            confirmed_ids = {vote["vote_id"] for vote in block.votes}
            node.vote_pool.remove_votes(confirmed_ids)
            print(f"[Routes] Block {block.index} accepted from {block.validator}")

        return jsonify({"accepted": accepted})

    @bp.route("/votes/submit", methods=["POST"])
    def submit_vote():
        vote = request.get_json() or {}
        if node.vote_pool.already_voted_in_chain(vote.get("voter_id"), node.blockchain):
            return (
                jsonify(
                    {
                        "success": False,
                        "reason": "Voter already has a confirmed vote",
                    }
                ),
                409,
            )

        result = node.vote_pool.add_vote(vote)
        if result["success"]:
            node.broadcast_vote(vote)

        return jsonify(result)

    @bp.route("/votes/receive", methods=["POST"])
    def receive_vote():
        vote = request.get_json() or {}
        result = node.vote_pool.add_vote(vote)
        return jsonify(result)

    @bp.route("/votes/pending", methods=["GET"])
    def pending_votes():
        return jsonify(node.vote_pool.get_pending_votes())

    @bp.route("/log", methods=["GET"])
    def get_log():
        return jsonify(node.vote_pool.get_log())

    return bp
