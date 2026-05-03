from __future__ import annotations

from typing import Any, Dict, List, Sequence

from core.merkle import MerkleTree
from voting.ledger import VoteLedger


class VoteVerifier:
    def __init__(self, blockchain):
        self.blockchain = blockchain

    def generate_receipt(self, vote_id: str) -> Dict[str, Any]:
        for block in self.blockchain.chain:
            if getattr(block, "index", None) == 0:
                continue

            votes = getattr(block, "votes", []) or []
            vote_ids = [vote["vote_id"] for vote in votes if "vote_id" in vote]

            if not vote_ids:
                continue

            if vote_id not in vote_ids:
                continue

            merkle_tree = MerkleTree(vote_ids)
            if merkle_tree.root != getattr(block, "merkle_root", ""):
                return {
                    "success": False,
                    "verified": False,
                    "reason": "Block Merkle root does not match block votes",
                    "vote_id": vote_id,
                    "block_index": block.index,
                }

            proof = merkle_tree.get_proof(vote_id)

            return {
                "success": True,
                "verified": True,
                "vote_id": vote_id,
                "block_index": block.index,
                "block_hash": block.hash,
                "validator": getattr(block, "validator", None),
                "merkle_root": block.merkle_root,
                "proof": proof,
                "merkle_proof": proof,
                "proof_length": len(proof or []),
            }

        return {
            "success": False,
            "verified": False,
            "reason": "Vote not found in confirmed blocks",
            "vote_id": vote_id,
        }

    @staticmethod
    def verify_receipt_locally(
        vote_id: str,
        proof: Sequence[Sequence[str]],
        root: str,
    ) -> bool:
        return MerkleTree.verify_proof(vote_id, proof, root)

    def full_audit(self) -> Dict[str, Any]:
        ledger = VoteLedger(self.blockchain)
        ledger_report = ledger.validate_ledger()
        chain_valid = self.blockchain.is_valid_chain()

        all_votes = self.blockchain.get_all_votes()

        seen_vote_ids = set()
        seen_voter_ids = set()
        duplicate_vote_ids = set()
        duplicate_voter_ids = set()

        for vote in all_votes:
            vote_id = vote.get("vote_id")
            voter_id = vote.get("voter_id")

            if vote_id in seen_vote_ids:
                duplicate_vote_ids.add(vote_id)
            else:
                seen_vote_ids.add(vote_id)

            if voter_id in seen_voter_ids:
                duplicate_voter_ids.add(voter_id)
            else:
                seen_voter_ids.add(voter_id)

        success = (
            bool(chain_valid)
            and len(duplicate_vote_ids) == 0
            and len(duplicate_voter_ids) == 0
            and bool(ledger_report.get("valid", False))
        )

        return {
            "success": success,
            "chain_valid": chain_valid,
            "total_blocks": len(self.blockchain.chain),
            "total_votes": len(all_votes),
            "duplicate_vote_ids": sorted(duplicate_vote_ids),
            "duplicate_voter_ids": sorted(duplicate_voter_ids),
            "ledger_report": ledger_report,
        }
