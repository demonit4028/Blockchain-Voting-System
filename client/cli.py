from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from client.client import VotingClient


def format_bar(percent: float, width: int = 20) -> str:
    filled = round((percent / 100) * width)
    return "█" * filled + " " * (width - filled)


def cmd_vote(client: VotingClient, args: argparse.Namespace) -> None:
    result = client.submit_vote(args.voter_id, args.candidate, salt=args.salt)

    if result.get("success"):
        print("✅ Vote accepted!")
        if "vote_id" in result:
            print(f"📄 Your receipt (vote_id): {result['vote_id']}")
        elif "receipt" in result and isinstance(result["receipt"], dict) and "vote_id" in result["receipt"]:
            print(f"📄 Your receipt (vote_id): {result['receipt']['vote_id']}")
        print("⚠️ Save your vote_id to verify your vote was counted!")
    else:
        print(f"❌ Vote rejected: {result.get('reason', 'unknown error')}")


def cmd_verify(client: VotingClient, args: argparse.Namespace) -> None:
    result = client.verify_vote(args.vote_id)

    if not result.get("success"):
        print(f"❌ Verification failed: {result.get('reason', 'unknown error')}")
        return

    status = "✅ PASSED" if result.get("local_verification") else "❌ FAILED"
    print(f"✅ Vote is confirmed in block #{result['block_index']}")
    print(f"   Block hash:    {result['block_hash']}")
    print(f"   Merkle root:   {result['merkle_root']}")
    print(f"🔐 Local Merkle verification: {status}")


def cmd_results(client: VotingClient, args: argparse.Namespace) -> None:
    result = client.get_results()

    if not result.get("success"):
        print(f"❌ Cannot load results: {result.get('reason', 'unknown error')}")
        return

    rows = result.get("results", [])
    if not rows:
        print("📊 No confirmed votes yet.")
        return

    for row in rows:
        candidate = row["candidate"]
        votes = row["votes"]
        percent = row["percent"]
        bar = format_bar(percent)
        print(f"{candidate:<14} {bar} {votes} votes ({percent:.0f}%)")


def cmd_status(client: VotingClient, args: argparse.Namespace) -> None:
    result = client.get_status()

    print("📡 Node status")
    for key, value in result.items():
        print(f"{key}: {value}")


def cmd_audit(client: VotingClient, args: argparse.Namespace) -> None:
    result = client.validate_ledger()

    print("🔎 Audit report")
    print(f"chain_valid: {result.get('chain_valid')}")
    print(f"total_blocks: {result.get('total_blocks')}")
    print(f"total_votes: {result.get('total_votes')}")
    print(f"duplicate_vote_ids: {result.get('duplicate_vote_ids')}")
    print(f"duplicate_voter_ids: {result.get('duplicate_voter_ids')}")

    if result.get("success"):
        print("✅ Audit: PASSED")
    else:
        print("❌ Audit: FAILED")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--node", required=True)

    subparsers = parser.add_subparsers(dest="command", required=True)

    vote_parser = subparsers.add_parser("vote")
    vote_parser.add_argument("--voter-id", required=True)
    vote_parser.add_argument("--candidate", required=True)
    vote_parser.add_argument("--salt", default="")

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--vote-id", required=True)

    subparsers.add_parser("results")
    subparsers.add_parser("status")
    subparsers.add_parser("audit")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    client = VotingClient(args.node)

    try:
        if args.command == "vote":
            cmd_vote(client, args)
        elif args.command == "verify":
            cmd_verify(client, args)
        elif args.command == "results":
            cmd_results(client, args)
        elif args.command == "status":
            cmd_status(client, args)
        elif args.command == "audit":
            cmd_audit(client, args)
    except requests.exceptions.ConnectionError:
        print("Cannot connect to node. Is it running?")


if __name__ == "__main__":
    main()
