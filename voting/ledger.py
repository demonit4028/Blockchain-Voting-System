from typing import Dict, List, Any, Optional
from collections import Counter


class VoteLedger:
    
    def __init__(self, blockchain):
        self.blockchain = blockchain
    
    def tally(self) -> Dict[str, int]:
        all_votes = self.blockchain.get_all_votes()
        candidates = [vote["candidate"] for vote in all_votes]
        return dict(Counter(candidates))
    
    def get_all_votes(self) -> List[Dict[str, Any]]:
        return self.blockchain.get_all_votes()
    
    def get_vote_by_id(self, vote_id: str) -> Optional[Dict[str, Any]]:
        all_votes = self.blockchain.get_all_votes()
        for vote in all_votes:
            if vote["vote_id"] == vote_id:
                return vote
        return None
    
    def get_voter_receipt(self, voter_id: str) -> List[Dict[str, Any]]:
        all_votes = self.blockchain.get_all_votes()
        return [v for v in all_votes if v["voter_id"] == voter_id]
    
    def validate_ledger(self) -> Dict[str, Any]:
        all_votes = self.blockchain.get_all_votes()
        
        vote_ids = [v["vote_id"] for v in all_votes]
        duplicate_vote_ids = [vid for vid, count in Counter(vote_ids).items() if count > 1]
        
        voter_ids = [v["voter_id"] for v in all_votes]
        duplicate_voter_ids = [vid for vid, count in Counter(voter_ids).items() if count > 1]
        
        is_valid = (len(duplicate_vote_ids) == 0 and len(duplicate_voter_ids) == 0)
        
        return {
            "valid": is_valid,
            "total_votes": len(all_votes),
            "duplicate_vote_ids": duplicate_vote_ids,
            "duplicate_voter_ids": duplicate_voter_ids,
            "message": "✅ Ledger is valid (no duplicates)" if is_valid 
                      else "❌ Ledger has duplicates!"
        }