import threading
import time
from typing import TYPE_CHECKING, Set

import requests

if TYPE_CHECKING:
    from consensus.poa import ProofOfAuthority
    from core.block import Block
    from core.blockchain import Blockchain
    from voting.vote_pool import VotePool


class P2PNode:
    def __init__(self, node_id: str, host: str, port: int):
        self.node_id = node_id
        self.host = host
        self.port = port
        self.peers: Set[str] = set()
        self.blockchain: "Blockchain" = None
        self.vote_pool: "VotePool" = None
        self.poa: "ProofOfAuthority" = None

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    def add_peer(self, address: str):
        if address and address != self.address:
            self.peers.add(address)
            print(f"[P2P] Registered peer: {address}")

    def remove_peer(self, address: str):
        self.peers.discard(address)

    def discover_peers(self, seed_peers: list):
        for peer in seed_peers:
            try:
                resp = requests.get(f"http://{peer}/peers", timeout=3)
                if resp.status_code == 200:
                    for candidate_peer in resp.json().get("peers", []):
                        self.add_peer(candidate_peer)
                self.add_peer(peer)
                requests.post(
                    f"http://{peer}/peers/register",
                    json={"address": self.address, "node_id": self.node_id},
                    timeout=3,
                )
            except Exception as error:
                print(f"[P2P] Cannot reach seed {peer}: {error}")

    def broadcast_block(self, block: "Block"):
        dead_peers = set()
        for peer in self.peers.copy():
            try:
                requests.post(
                    f"http://{peer}/blocks/receive",
                    json=block.to_dict(),
                    timeout=3,
                )
            except Exception:
                dead_peers.add(peer)
        for peer in dead_peers:
            self.remove_peer(peer)

    def broadcast_vote(self, vote: dict):
        for peer in self.peers.copy():
            try:
                requests.post(
                    f"http://{peer}/votes/receive",
                    json=vote,
                    timeout=3,
                )
            except Exception:
                pass

    def sync_chain(self):
        from core.block import Block as BlockModel

        for peer in self.peers.copy():
            try:
                resp = requests.get(f"http://{peer}/chain", timeout=5)
                if resp.status_code == 200:
                    chain_data = resp.json()
                    new_chain = [BlockModel.from_dict(block) for block in chain_data]
                    replaced = self.blockchain.replace_chain(new_chain)
                    if replaced:
                        print(f"[P2P] Chain synced from {peer}")
            except Exception as error:
                print(f"[P2P] Sync failed from {peer}: {error}")

    def start_sync_loop(self, interval: int = 30):
        def loop():
            time.sleep(5)
            while True:
                self.sync_chain()
                time.sleep(interval)

        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
