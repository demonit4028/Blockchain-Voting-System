from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

import requests

from voting.vote import Vote


class VotingClient:
    def __init__(self, node_url: str):
        self.node_url = node_url.rstrip("/")
        self.timeout = 3

    def _get(self, path: str) -> Any:
        response = requests.get(f"{self.node_url}{path}", timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = requests.post(f"{self.node_url}{path}", json=payload, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def submit_vote(self, real_voter_id: str, candidate: str, salt: str = "") -> Dict[str, Any]:
        vote = Vote.create(real_voter_id, candidate, salt=salt)
        payload = vote.to_dict()
        return self._post("/votes/submit", payload)

    def get_chain(self) -> Any:
        return self._get("/chain")

    @staticmethod
    def _extract_chain(chain_data: Union[Dict[str, Any], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        if isinstance(chain_data, dict):
            return chain_data.get("chain", [])
        return chain_data

    def get_status(self) -> Dict[str, Any]:
        return self._get("/status")

    def get_log(self) -> Dict[str, Any]:
        return self._get("/log")

    def get_pending_votes(self) -> Dict[str, Any]:
        return self._get("/votes/pending")

    def verify_vote(self, vote_id: str) -> Dict[str, Any]:
        chain = self._extract_chain(self.get_chain())

        from core.blockchain import Blockchain
        from client.verification import VoteVerifier

        blockchain = Blockchain.from_dict(chain)
        verifier = VoteVerifier(blockchain)
        receipt = verifier.generate_receipt(vote_id)

        if not receipt.get("success"):
            return receipt

        local_ok = VoteVerifier.verify_receipt_locally(
            receipt["vote_id"],
            receipt["proof"],
            receipt["merkle_root"],
        )

        receipt["local_verification"] = local_ok
        return receipt

    def get_results(self) -> Dict[str, Any]:
        chain = self._extract_chain(self.get_chain())

        from core.blockchain import Blockchain
        from voting.ledger import VoteLedger

        blockchain = Blockchain.from_dict(chain)
        ledger = VoteLedger(blockchain)
        tally = ledger.tally()
        total = sum(tally.values())

        results = []
        for candidate, votes in sorted(tally.items(), key=lambda item: (-item[1], item[0])):
            percent = 0.0 if total == 0 else (votes / total) * 100
            results.append(
                {
                    "candidate": candidate,
                    "votes": votes,
                    "percent": percent,
                }
            )

        return {
            "success": True,
            "total_votes": total,
            "results": results,
        }

    def validate_ledger(self) -> Dict[str, Any]:
        chain = self._extract_chain(self.get_chain())

        from core.blockchain import Blockchain
        from client.verification import VoteVerifier

        blockchain = Blockchain.from_dict(chain)
        verifier = VoteVerifier(blockchain)
        return verifier.full_audit()
