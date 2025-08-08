import hashlib
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class MerkleNode:
    """Represents a node in the Merkle tree."""
    hash: str
    left: Optional['MerkleNode'] = None
    right: Optional['MerkleNode'] = None
    is_leaf: bool = False
    transaction_data: Optional[Dict[str, Any]] = None

class MerkleTree:
    """Merkle tree implementation for efficient transaction verification."""
    
    def __init__(self, transactions: List[Dict[str, Any]]):
        self.transactions = transactions
        self.root = None
        self.leaf_nodes = []
        self._build_tree()
    
    def _hash_data(self, data: str) -> str:
        """Create SHA-256 hash of data."""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _create_leaf_node(self, transaction: Dict[str, Any]) -> MerkleNode:
        """Create a leaf node from transaction data."""
        # Create a deterministic string representation of the transaction
        tx_string = json.dumps(transaction, sort_keys=True)
        tx_hash = self._hash_data(tx_string)
        
        return MerkleNode(
            hash=tx_hash,
            is_leaf=True,
            transaction_data=transaction
        )
    
    def _create_parent_node(self, left: MerkleNode, right: Optional[MerkleNode] = None) -> MerkleNode:
        """Create a parent node from two child nodes."""
        if right is None:
            # If no right child, duplicate the left child
            right = left
        
        # Combine hashes and create parent hash
        combined_hash = left.hash + right.hash
        parent_hash = self._hash_data(combined_hash)
        
        return MerkleNode(
            hash=parent_hash,
            left=left,
            right=right
        )
    
    def _build_tree(self) -> None:
        """Build the Merkle tree from transactions."""
        if not self.transactions:
            # Empty tree
            self.root = MerkleNode(hash="0" * 64)
            return
        
        # Create leaf nodes
        self.leaf_nodes = [self._create_leaf_node(tx) for tx in self.transactions]
        
        # Build tree bottom-up
        current_level = self.leaf_nodes.copy()
        
        while len(current_level) > 1:
            next_level = []
            
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else None
                
                parent = self._create_parent_node(left, right)
                next_level.append(parent)
            
            current_level = next_level
        
        self.root = current_level[0]
    
    def get_root_hash(self) -> str:
        """Get the root hash of the Merkle tree."""
        return self.root.hash if self.root else "0" * 64
    
    def get_proof(self, transaction_index: int) -> List[Dict[str, Any]]:
        """Generate a Merkle proof for a transaction at the given index."""
        if not self.leaf_nodes or transaction_index >= len(self.leaf_nodes):
            return []
        
        proof = []
        current_node = self.leaf_nodes[transaction_index]
        current_level = self.leaf_nodes.copy()
        
        while len(current_level) > 1:
            # Find the index of current node in this level
            node_index = None
            for i, node in enumerate(current_level):
                if node.hash == current_node.hash:
                    node_index = i
                    break
            
            if node_index is None:
                break
            
            # Determine if current node is left or right child
            is_left = node_index % 2 == 0
            sibling_index = node_index + 1 if is_left else node_index - 1
            
            # Add sibling to proof
            if sibling_index < len(current_level):
                sibling = current_level[sibling_index]
                proof.append({
                    'hash': sibling.hash,
                    'position': 'right' if is_left else 'left'
                })
            
            # Move to parent level
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                parent = self._create_parent_node(left, right)
                next_level.append(parent)
                
                # Update current_node if it's in this pair
                if i == node_index or i + 1 == node_index:
                    current_node = parent
            
            current_level = next_level
        
        return proof
    
    def verify_proof(self, transaction: Dict[str, Any], proof: List[Dict[str, Any]], root_hash: str) -> bool:
        """Verify a Merkle proof for a transaction."""
        # Create hash of the transaction
        tx_string = json.dumps(transaction, sort_keys=True)
        current_hash = self._hash_data(tx_string)
        
        # Reconstruct the path to root
        for proof_item in proof:
            if proof_item['position'] == 'left':
                # Sibling is on the left, so current hash goes on the right
                combined_hash = proof_item['hash'] + current_hash
            else:
                # Sibling is on the right, so current hash goes on the left
                combined_hash = current_hash + proof_item['hash']
            
            current_hash = self._hash_data(combined_hash)
        
        return current_hash == root_hash
    
    def get_leaf_count(self) -> int:
        """Get the number of leaf nodes (transactions)."""
        return len(self.leaf_nodes)
    
    def get_tree_height(self) -> int:
        """Get the height of the Merkle tree."""
        if not self.root:
            return 0
        
        height = 0
        current = self.root
        while current.left:
            height += 1
            current = current.left
        
        return height
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Merkle tree to dictionary for serialization."""
        return {
            'root_hash': self.get_root_hash(),
            'leaf_count': self.get_leaf_count(),
            'tree_height': self.get_tree_height(),
            'transactions': self.transactions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MerkleTree':
        """Create a Merkle tree from dictionary data."""
        return cls(data['transactions'])
    
    def get_transaction_hashes(self) -> List[str]:
        """Get all transaction hashes in the order they appear in the tree."""
        return [node.hash for node in self.leaf_nodes]
    
    def find_transaction_index(self, transaction: Dict[str, Any]) -> Optional[int]:
        """Find the index of a transaction in the tree."""
        tx_string = json.dumps(transaction, sort_keys=True)
        target_hash = self._hash_data(tx_string)
        
        for i, node in enumerate(self.leaf_nodes):
            if node.hash == target_hash:
                return i
        
        return None
