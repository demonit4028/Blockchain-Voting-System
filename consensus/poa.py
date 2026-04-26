# consensus/poa.py
import hashlib
import hmac
import time
from typing import List, Optional

from core.block import Block


class ProofOfAuthority:
    """
    Proof of Authority консенсус с round-robin ротацией.

    Каждый валидатор знает общий secret_key (в реальной системе
    используются RSA/ECDSA ключевые пары, здесь HMAC для простоты).
    """

    def __init__(self, validators: List[str], node_id: str, secret_key: str):
        """
        validators  — отсортированный список ID авторизованных валидаторов
        node_id     — ID этого узла
        secret_key  — общий секрет для подписи/верификации
        """
        self.validators = sorted(validators)
        if not self.validators:
            raise ValueError("At least one validator is required")
        self.node_id = node_id
        self.secret_key = secret_key

    # ─── Определение очерёдности ───────────────────────────────────────────

    def expected_validator(self, block_index: int) -> str:
        """Кто должен создать блок с данным индексом (round-robin)."""
        if block_index <= 0:
            return self.validators[0]
        return self.validators[(block_index - 1) % len(self.validators)]

    def is_my_turn(self, block_index: int) -> bool:
        """Является ли этот узел следующим валидатором."""
        return self.expected_validator(block_index) == self.node_id

    def is_authorized(self, node_id: str) -> bool:
        """Входит ли узел в список валидаторов."""
        return node_id in self.validators

    # ─── Подпись и верификация ─────────────────────────────────────────────

    def sign_block(self, block: Block) -> str:
        """
        Подписываем блок: HMAC-SHA256(hash:validator_id, secret).
        В production заменить на ECDSA с приватным ключом.
        """
        message = f"{block.hash}:{self.node_id}".encode()
        return hmac.new(
            self.secret_key.encode(), message, hashlib.sha256
        ).hexdigest()

    def verify_signature(self, block: Block) -> bool:
        """Проверяем подпись блока (зная общий secret)."""
        message = f"{block.hash}:{block.validator}".encode()
        expected = hmac.new(
            self.secret_key.encode(), message, hashlib.sha256
        ).hexdigest()
        try:
            return hmac.compare_digest(block.signature, expected)
        except Exception:
            return False

    # ─── Валидация блока ───────────────────────────────────────────────────

    def validate_block(self, block: Block) -> tuple[bool, str]:
        """
        Полная PoA-валидация:
        1. Валидатор авторизован
        2. Валидатор — правильный по round-robin
        3. Подпись корректна
        """
        if not self.is_authorized(block.validator):
            return False, f"Validator '{block.validator}' not in authority list"

        expected = self.expected_validator(block.index)
        if block.validator != expected:
            return False, (
                f"Wrong validator: expected '{expected}', got '{block.validator}'"
            )

        if not self.verify_signature(block):
            return False, "Invalid block signature"

        return True, "OK"

    # ─── Создание блока ────────────────────────────────────────────────────

    def create_block(
        self, votes: List[dict], previous_hash: str, index: int
    ) -> Optional[Block]:
        """
        Создаём и подписываем новый блок, если сейчас наша очередь.
        Возвращает None если не наша очередь.
        """
        if not self.is_my_turn(index):
            print(
                f"[PoA] Not my turn for block {index}. "
                f"Expected: {self.expected_validator(index)}"
            )
            return None

        block = Block(
            index=index,
            timestamp=time.time(),
            votes=votes,
            previous_hash=previous_hash,
            validator=self.node_id,
        )
        block.signature = self.sign_block(block)
        print(f"[PoA] Block {index} created and signed by {self.node_id}")
        return block

    def get_status(self) -> dict:
        return {
            "validators": self.validators,
            "node_id": self.node_id,
            "is_validator": self.is_authorized(self.node_id),
        }
