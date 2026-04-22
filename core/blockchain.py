# core/blockchain.py
from typing import List, Optional
from .block import Block


class Blockchain:
    """
    Управляет цепочкой блоков.
    
    Правила добавления блока:
    1. index = последний_блок.index + 1
    2. previous_hash == хэш последнего блока
    3. hash == пересчитанный хэш (никто не подменил данные)
    """

    def __init__(self):
        self.chain: List[Block] = []
        self._create_genesis()

    def _create_genesis(self):
        """Нулевой блок — точка отсчёта цепочки."""
        genesis = Block(
            index=0,
            timestamp=0.0,
            votes=[],
            previous_hash="0" * 64,
            validator="genesis",
        )
        genesis.signature = "genesis"
        self.chain.append(genesis)

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    @property
    def height(self) -> int:
        return len(self.chain)

    def add_block(self, block: Block) -> bool:
        if not self._is_valid_new_block(block):
            print(f"[Blockchain] Rejected block {block.index}: invalid")
            return False
        self.chain.append(block)
        return True

    def _is_valid_new_block(self, block: Block) -> bool:
        last = self.last_block
        if block.index != last.index + 1:
            return False
        if block.previous_hash != last.hash:
            return False
        if block.hash != block.compute_hash():
            return False
        return True

    def is_valid_chain(self) -> bool:
        """Полная проверка всей цепочки."""
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i - 1]
            if curr.previous_hash != prev.hash:
                return False
            if curr.hash != curr.compute_hash():
                return False
        return True

    def get_all_votes(self) -> List[dict]:
        """Все подтверждённые голоса из всей цепочки."""
        votes = []
        for block in self.chain[1:]:  # пропускаем genesis
            votes.extend(block.votes)
        return votes

    def replace_chain(self, new_chain: List[Block]) -> bool:
        """
        Правило «самая длинная валидная цепочка побеждает».
        Используется при синхронизации с другими узлами.
        """
        candidate = Blockchain.__new__(Blockchain)
        candidate.chain = new_chain
        if len(new_chain) > len(self.chain) and candidate.is_valid_chain():
            self.chain = new_chain
            print(f"[Blockchain] Chain replaced, new height={len(self.chain)}")
            return True
        return False

    def to_dict(self) -> List[dict]:
        return [b.to_dict() for b in self.chain]

    @classmethod
    def from_dict(cls, data: List[dict]) -> "Blockchain":
        bc = cls.__new__(cls)
        bc.chain = [Block.from_dict(b) for b in data]
        return bc