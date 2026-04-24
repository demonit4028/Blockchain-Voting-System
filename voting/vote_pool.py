import threading
from datetime import datetime
from typing import List, Dict, Any, Set


class VotePool:
    
    def __init__(self, candidates: List[str]):
        self.candidates = candidates
        self._pool: Dict[str, Dict[str, Any]] = {}
        self._voter_ids: Set[str] = set()
        self._lock = threading.RLock()
        self._log: List[Dict[str, Any]] = []
        self._write_log("init", "system", f"Pool created with candidates: {candidates}")
    
    def _write_log(self, event: str, vote_id: str, details: str):
        self._log.append({
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "vote_id": vote_id,
            "details": details
        })
    
    def count(self) -> int:
        with self._lock:
            return len(self._pool)
    
    def get_log(self) -> List[Dict[str, Any]]:
        with self._lock:
            return self._log.copy()
    
    def already_voted_in_chain(self, voter_id: str, blockchain) -> bool:
        if blockchain is None:
            return False
        
        all_votes = blockchain.get_all_votes()
        for vote in all_votes:
            if vote.get("voter_id") == voter_id:
                return True
        return False
    
    def add_vote(self, vote_data: Dict[str, Any], blockchain=None) -> Dict[str, Any]:
        with self._lock:
            if vote_data["candidate"] not in self.candidates:
                self._write_log("reject", vote_data.get("vote_id", ""), 
                               f"Invalid candidate: {vote_data['candidate']}")
                return {
                    "success": False, 
                    "reason": f"Candidate '{vote_data['candidate']}' not in {self.candidates}"
                }
            
            vote_id = vote_data["vote_id"]
            voter_id = vote_data["voter_id"]
            
            if vote_id in self._pool:
                self._write_log("reject", vote_id, "Duplicate vote_id in pool")
                return {"success": False, "reason": "Vote already in pool (duplicate vote_id)"}
            
            if voter_id in self._voter_ids:
                self._write_log("reject", vote_id, f"Duplicate voter_id {voter_id} in pool")
                return {"success": False, "reason": "You already have a pending vote"}
            
            if blockchain and self.already_voted_in_chain(voter_id, blockchain):
                self._write_log("reject", vote_id, f"Voter {voter_id} already voted in blockchain")
                return {"success": False, "reason": "You have already voted in a confirmed block"}
            
            self._pool[vote_id] = vote_data
            self._voter_ids.add(voter_id)
            self._write_log("accept", vote_id, f"Vote for {vote_data['candidate']} added")
            
            return {
                "success": True,
                "vote_id": vote_id,
                "receipt": vote_id,
                "reason": "Vote accepted. Save your vote_id to verify later!"
            }
    
    def get_pending_votes(self, max_count: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._pool.values())[:max_count]
    
    def remove_votes(self, vote_ids_set: set) -> int:
        with self._lock:
            removed_count = 0
            for vote_id in vote_ids_set:
                if vote_id in self._pool:
                    voter_id = self._pool[vote_id]["voter_id"]
                    self._voter_ids.discard(voter_id)
                    del self._pool[vote_id]
                    removed_count += 1
                    self._write_log("removed", vote_id, "Vote included in block")
            return removed_count