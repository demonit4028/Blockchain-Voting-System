# core/merkle.py
import hashlib
from typing import List, Optional, Tuple


def _hash(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


class MerkleTree:
    """
    Дерево Меркла для набора строк (vote_id'ов).
    
    Позволяет:
    - Получить root — отпечаток всего набора
    - Создать proof для одного элемента
    - Верифицировать proof без знания остальных элементов
    """

    def __init__(self, data_list: List[str]):
        if not data_list:
            self.leaves = [_hash("empty")]
        else:
            self.leaves = [_hash(d) for d in data_list]
        self._data_list = data_list
        self.tree = self._build(self.leaves)

    def _build(self, leaves: List[str]) -> List[List[str]]:
        """Строим дерево снизу вверх."""
        tree = [leaves[:]]
        current = leaves[:]
        while len(current) > 1:
            if len(current) % 2 == 1:
                current.append(current[-1])  # дублируем последний лист
            next_level = [
                _hash(current[i] + current[i + 1])
                for i in range(0, len(current), 2)
            ]
            tree.append(next_level)
            current = next_level
        return tree

    @property
    def root(self) -> str:
        return self.tree[-1][0]

    def get_proof(self, data: str) -> Optional[List[Tuple[str, str]]]:
        """
        Возвращает список пар (хэш_соседа, 'left'|'right').
        Зная proof и root, можно доказать включение data без знания остальных элементов.
        """
        target = _hash(data)
        if target not in self.leaves:
            return None

        proof = []
        idx = self.leaves.index(target)

        for level in self.tree[:-1]:  # все уровни кроме root
            if idx % 2 == 0:
                sibling = idx + 1 if idx + 1 < len(level) else idx
                proof.append((level[sibling], "right"))
            else:
                proof.append((level[idx - 1], "left"))
            idx //= 2

        return proof

    @staticmethod
    def verify_proof(data: str, proof: List[Tuple[str, str]], root: str) -> bool:
        """
        Верифицируем proof без знания всего дерева.
        Восстанавливаем путь от листа до корня и сравниваем с root.
        """
        current = _hash(data)
        for sibling, direction in proof:
            if direction == "right":
                current = _hash(current + sibling)
            else:
                current = _hash(sibling + current)
        return current == root