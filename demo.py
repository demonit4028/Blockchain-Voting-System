# demo.py
"""
Демонстрация всей системы локально — без запуска серверов.
Запуск: python demo.py
"""
import time

from core.blockchain import Blockchain
from core.merkle import MerkleTree
from consensus.poa import ProofOfAuthority
from voting.vote import Vote
from voting.vote_pool import VotePool
from voting.ledger import VoteLedger
from client.verification import VoteVerifier

VALIDATORS  = ["node1", "node2", "node3"]
SECRET      = "demo_secret"
CANDIDATES  = ["Alice", "Bob", "Charlie"]

print("=" * 60)
print("  Blockchain-Based Voting System — Demo")
print("=" * 60)

# Инициализация
blockchain = Blockchain()
vote_pool  = VotePool(candidates=CANDIDATES)

next_index = blockchain.height
expected_validator = sorted(VALIDATORS)[(next_index - 1) % len(VALIDATORS)]
poa = ProofOfAuthority(VALIDATORS, expected_validator, SECRET)

ledger     = VoteLedger(blockchain)
verifier   = VoteVerifier(blockchain)

# ─── Шаг 1: Голосование ────────────────────────────────────────────────────
print("\n[1] Submitting votes...")
voters = [
    ("voter_alice_001", "Alice"),
    ("voter_bob_001",   "Bob"),
    ("voter_charlie_1", "Alice"),
    ("voter_dave_001",  "Bob"),
    ("voter_eve_001",   "Alice"),
]

receipts = {}
for real_id, candidate in voters:
    vote = Vote.create(real_id, candidate, salt="election2024")
    result = vote_pool.add_vote(vote.to_dict())
    if result["success"]:
        receipts[real_id] = vote.vote_id
        print(f"  ✅ {real_id} → {candidate} | receipt: {vote.vote_id[:16]}...")

# ─── Шаг 2: Попытка двойного голосования ──────────────────────────────────
print("\n[2] Testing double vote prevention...")
vote2 = Vote.create("voter_alice_001", "Bob", salt="election2024")
result = vote_pool.add_vote(vote2.to_dict())
print(f"  Double vote result: {result}")

# ─── Шаг 3: Создание блока (node1 — первый валидатор) ─────────────────────
print("\n[3] Creating block (node1's turn)...")
pending = vote_pool.get_pending_votes()
block = poa.create_block(
    votes=pending,
    previous_hash=blockchain.last_block.hash,
    index=blockchain.height,
)
added = blockchain.add_block(block)
vote_pool.remove_votes({v["vote_id"] for v in pending})
print(f"  Block #{block.index} added: {added}")
print(f"  Block hash: {block.hash[:24]}...")
print(f"  Validator:  {block.validator}")
print(f"  Votes:      {len(block.votes)}")

# ─── Шаг 4: Верификация PoA подписи ────────────────────────────────────────
print("\n[4] Verifying PoA signature...")
valid, msg = poa.validate_block(block)
print(f"  PoA validation: {'✅' if valid else '❌'} {msg}")

# ─── Шаг 5: Merkle Proof ──────────────────────────────────────────────────
print("\n[5] Merkle Proof verification...")
vote_id = receipts["voter_alice_001"]
receipt = verifier.generate_receipt(vote_id)
if receipt["verified"]:
    print(f"  Vote found in block #{receipt['block_index']}")
    proof_ok = VoteVerifier.verify_receipt_locally(
        vote_id, receipt["merkle_proof"], receipt["merkle_root"]
    )
    print(f"  Merkle proof: {'✅ VALID' if proof_ok else '❌ INVALID'}")

# ─── Шаг 6: Результаты и аудит ────────────────────────────────────────────
print("\n[6] Election Results:")
tally = ledger.tally()
total = sum(tally.values())
for c, n in sorted(tally.items(), key=lambda x: -x[1]):
    bar = "█" * n
    print(f"  {c:<10} {bar} {n} ({n/total*100:.0f}%)")

print("\n[7] Ledger Validation:")
audit = ledger.validate_ledger()
print(f"  Total votes:     {audit['total_votes']}")
print(f"  Unique voters:   {audit['unique_voters']}")
print(f"  Ledger valid:    {'✅' if audit['ledger_valid'] else '❌'}")

print("\n[8] Chain Validity:", "✅" if blockchain.is_valid_chain() else "❌")
print(f"  Chain height: {blockchain.height} blocks")
print("\n" + "=" * 60)
print("  Demo complete!")
print("=" * 60)
