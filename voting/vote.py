import hashlib
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any


@dataclass
class Vote:
    voter_id: str
    voter_hash: str
    candidate: str
    timestamp: float
    vote_id: str
    
    @classmethod
    def create(cls, real_voter_id: str, candidate: str, salt: str = "") -> "Vote":
        voter_id = hashlib.sha256(real_voter_id.encode()).hexdigest()
        voter_hash = hashlib.sha256(f"{real_voter_id}{salt}".encode()).hexdigest()
        unique_string = f"{voter_id}{candidate}{datetime.now().timestamp()}{uuid.uuid4()}"
        vote_id = hashlib.sha256(unique_string.encode()).hexdigest()
        
        return cls(
            voter_id=voter_id,
            voter_hash=voter_hash,
            candidate=candidate,
            timestamp=datetime.now().timestamp(),
            vote_id=vote_id
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Vote":
        return cls(**data)