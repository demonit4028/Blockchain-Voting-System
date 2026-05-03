import hashlib
import json
from dataclasses import dataclass, field
from typing import List

from core.merkle import MerkleTree


@dataclass
class Block:
    """
    Один блок в цепочке.
    
    index         — порядковый номер
    timestamp     — время создания
    votes         — список голосов (dict)
    previous_hash — хэш предыдущего блока
    validator     — ID узла, создавшего блок
    merkle_root   — Merkle root для vote_id в этом блоке
    signature     — HMAC-подпись валидатора
    hash          — SHA-256 хэш этого блока (вычисляется автоматически)
    """
    index: int
    timestamp: float
    votes: List[dict]
    previous_hash: str
    validator: str
    merkle_root: str = ""
    signature: str = ""
    hash: str = field(default="", init=False)

    def __post_init__(self):
        if not self.merkle_root:
            self.merkle_root = self.compute_merkle_root()
        self.hash = self.compute_hash()

    def compute_merkle_root(self) -> str:
        """Merkle root фиксирует набор vote_id, включённых в блок."""
        vote_ids = [vote["vote_id"] for vote in self.votes if "vote_id" in vote]
        return MerkleTree(vote_ids).root

    def compute_hash(self) -> str:
        """Хэшируем все поля кроме hash и signature (их ещё нет при вычислении)."""
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "votes": self.votes,
            "previous_hash": self.previous_hash,
            "validator": self.validator,
            "merkle_root": self.merkle_root,
        }
        return hashlib.sha256(
            json.dumps(block_data, sort_keys=True).encode()
        ).hexdigest()

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "votes": self.votes,
            "previous_hash": self.previous_hash,
            "validator": self.validator,
            "merkle_root": self.merkle_root,
            "signature": self.signature,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Block":
        block = cls(
            index=data["index"],
            timestamp=data["timestamp"],
            votes=data["votes"],
            previous_hash=data["previous_hash"],
            validator=data["validator"],
            merkle_root=data.get("merkle_root", ""),
        )
        block.signature = data.get("signature", "")
        block.hash = data["hash"]
        return block

    def __repr__(self):
        return (
            f"Block(index={self.index}, votes={len(self.votes)}, "
            f"validator={self.validator}, hash={self.hash[:12]}...)"
        )
