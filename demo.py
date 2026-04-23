from __future__ import annotations

from client.verification import VoteVerifier
from consensus.poa import ProofOfAuthority
from core.blockchain import Blockchain
from voting.ledger import VoteLedger
from voting.vote import Vote
from voting.vote_pool import VotePool


def print_title(text: str) -> None:
    print("\n" + "=" * 72)
    print(text)
    print("=" * 72)


def main() -> None:
    validators = ["node1", "node2", "node3"]
    secret = "shared_poa_secret_2024"

    blockchain = Blockchain()
    vote_pool = VotePool(candidates=["Alice", "Bob"])
    poa = ProofOfAuthority(validators=validators, node_id="node1", secret_key=secret)

    print_title("BLOCKCHAIN VOTING SYSTEM DEMO")

    vote_inputs = [
        ("ivan", "Alice", "2024"),
        ("maria", "Bob", "2024"),
        ("alex", "Alice", "2024"),
    ]

    created_votes = []

    print_title("1. SUBMIT VOTES")
    for real_voter_id, candidate, salt in vote_inputs:
        vote = Vote.create(real_voter_id, candidate, salt=salt)
        created_votes.append(vote)
        result = vote_pool.add_vote(vote.to_dict(), blockchain)
        print(f"{real_voter_id} -> {candidate}: {result}")

    print_title("2. VOTE LOG")
    for entry in vote_pool.get_log():
        print(entry)

    print_title("3. CREATE BLOCK")
    pending_votes = vote_pool.get_pending_votes(max_count=10)
    block = poa.create_block(blockchain, pending_votes)

    if block is None:
        print("Block was not created")
        return

    added = blockchain.add_block(block)
    print(f"Block added: {added}")

    confirmed_vote_ids = {vote["vote_id"] for vote in pending_votes}
    vote_pool.remove_votes(confirmed_vote_ids)

    print_title("4. RESULTS")
    ledger = VoteLedger(blockchain)
    tally = ledger.tally()
    total_votes = sum(tally.values())

    for candidate, votes in sorted(tally.items(), key=lambda item: (-item[1], item[0])):
        percent = 0.0 if total_votes == 0 else (votes / total_votes) * 100
        bar = "█" * round(percent / 5)
        print(f"{candidate:<14} {bar:<20} {votes} votes ({percent:.0f}%)")

    print_title("5. VALIDATE LEDGER")
    ledger_report = ledger.validate_ledger()
    print(ledger_report)

    print_title("6. MERKLE RECEIPT")
    verifier = VoteVerifier(blockchain)
    target_vote_id = created_votes[0].vote_id
    receipt = verifier.generate_receipt(target_vote_id)
    print(receipt)

    print_title("7. LOCAL VERIFICATION")
    if receipt.get("success"):
        local_ok = VoteVerifier.verify_receipt_locally(
            receipt["vote_id"],
            receipt["proof"],
            receipt["merkle_root"],
        )
        print({"local_verification": local_ok})

    print_title("8. FULL AUDIT")
    audit = verifier.full_audit()
    print(audit)


if __name__ == "__main__":
    main()
