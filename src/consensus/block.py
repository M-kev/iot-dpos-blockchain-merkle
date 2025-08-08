from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from typing import List, Dict, Any, Optional
from utils.merkle_tree import MerkleTree

@dataclass
class Block:
    block_index: int
    timestamp: float
    transactions: List[Dict[str, Any]]
    previous_hash: str
    validator: str
    energy_metrics: Dict[str, float]
    merkle_root: Optional[str] = None
    merkle_tree: Optional[MerkleTree] = None
    
    def __post_init__(self):
        # Build Merkle tree from transactions
        self.merkle_tree = MerkleTree(self.transactions)
        self.merkle_root = self.merkle_tree.get_root_hash()
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate the block hash using SHA-256 with Merkle root."""
        block_string = json.dumps({
            'block_index': self.block_index,
            'timestamp': self.timestamp,
            'merkle_root': self.merkle_root,
            'previous_hash': self.previous_hash,
            'validator': self.validator,
            'energy_metrics': self.energy_metrics
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def get_merkle_proof(self, transaction_index: int) -> List[Dict[str, Any]]:
        """Get Merkle proof for a transaction at the given index."""
        if self.merkle_tree:
            return self.merkle_tree.get_proof(transaction_index)
        return []
    
    def verify_transaction_inclusion(self, transaction: Dict[str, Any], proof: List[Dict[str, Any]]) -> bool:
        """Verify that a transaction is included in this block using Merkle proof."""
        if self.merkle_tree:
            return self.merkle_tree.verify_proof(transaction, proof, self.merkle_root)
        return False
    
    def get_transaction_index(self, transaction: Dict[str, Any]) -> Optional[int]:
        """Get the index of a transaction in this block."""
        if self.merkle_tree:
            return self.merkle_tree.find_transaction_index(transaction)
        return None
    
    def get_transaction_hashes(self) -> List[str]:
        """Get all transaction hashes in the block."""
        if self.merkle_tree:
            return self.merkle_tree.get_transaction_hashes()
        return []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert block to dictionary for serialization."""
        return {
            'block_index': self.block_index,
            'timestamp': self.timestamp,
            'transactions': self.transactions,
            'previous_hash': self.previous_hash,
            'hash': self.hash,
            'validator': self.validator,
            'energy_metrics': self.energy_metrics,
            'merkle_root': self.merkle_root
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Block':
        """Create a Block instance from a dictionary."""
        return cls(
            block_index=data['block_index'],
            timestamp=data['timestamp'],
            transactions=data['transactions'],
            previous_hash=data['previous_hash'],
            validator=data['validator'],
            energy_metrics=data['energy_metrics'],
            merkle_root=data.get('merkle_root')
        ) 