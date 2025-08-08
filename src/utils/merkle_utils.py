import hashlib
import json
from typing import List, Dict, Any, Optional
from .merkle_tree import MerkleTree

def create_merkle_tree_from_transactions(transactions: List[Dict[str, Any]]) -> MerkleTree:
    """Create a Merkle tree from a list of transactions."""
    return MerkleTree(transactions)

def verify_transaction_in_block(block_merkle_root: str, transaction: Dict[str, Any], proof: List[Dict[str, Any]]) -> bool:
    """Verify that a transaction is included in a block using its Merkle proof."""
    # Create a temporary Merkle tree to verify the proof
    temp_tree = MerkleTree([transaction])
    return temp_tree.verify_proof(transaction, proof, block_merkle_root)

def calculate_merkle_root(transactions: List[Dict[str, Any]]) -> str:
    """Calculate the Merkle root for a list of transactions."""
    if not transactions:
        return "0" * 64
    
    tree = MerkleTree(transactions)
    return tree.get_root_hash()

def generate_merkle_proof(transactions: List[Dict[str, Any]], target_transaction: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    """Generate a Merkle proof for a specific transaction."""
    tree = MerkleTree(transactions)
    tx_index = tree.find_transaction_index(target_transaction)
    
    if tx_index is not None:
        return tree.get_proof(tx_index)
    return None

def batch_verify_transactions(block_merkle_root: str, transactions: List[Dict[str, Any]], proofs: List[List[Dict[str, Any]]]) -> List[bool]:
    """Verify multiple transactions in a block using their Merkle proofs."""
    if len(transactions) != len(proofs):
        return [False] * len(transactions)
    
    results = []
    for tx, proof in zip(transactions, proofs):
        result = verify_transaction_in_block(block_merkle_root, tx, proof)
        results.append(result)
    
    return results

def get_merkle_tree_stats(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Get statistics about a Merkle tree."""
    if not transactions:
        return {
            "leaf_count": 0,
            "tree_height": 0,
            "root_hash": "0" * 64
        }
    
    tree = MerkleTree(transactions)
    return {
        "leaf_count": tree.get_leaf_count(),
        "tree_height": tree.get_tree_height(),
        "root_hash": tree.get_root_hash()
    }

def optimize_merkle_tree_for_verification(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Optimize Merkle tree structure for efficient verification."""
    tree = MerkleTree(transactions)
    
    # Pre-compute all proofs for quick access
    proofs = {}
    for i, tx in enumerate(transactions):
        proofs[i] = tree.get_proof(i)
    
    return {
        "tree": tree,
        "proofs": proofs,
        "root_hash": tree.get_root_hash(),
        "transaction_hashes": tree.get_transaction_hashes()
    }

def validate_merkle_tree_integrity(merkle_root: str, transactions: List[Dict[str, Any]]) -> bool:
    """Validate that the Merkle root matches the transactions."""
    if not transactions:
        return merkle_root == "0" * 64
    
    tree = MerkleTree(transactions)
    return tree.get_root_hash() == merkle_root

def get_merkle_path_for_transaction(transactions: List[Dict[str, Any]], target_transaction: Dict[str, Any]) -> Optional[List[str]]:
    """Get the Merkle path (list of hashes) for a specific transaction."""
    tree = MerkleTree(transactions)
    tx_index = tree.find_transaction_index(target_transaction)
    
    if tx_index is None:
        return None
    
    proof = tree.get_proof(tx_index)
    path = []
    
    # Reconstruct the path from the proof
    tx_string = json.dumps(target_transaction, sort_keys=True)
    current_hash = hashlib.sha256(tx_string.encode()).hexdigest()
    path.append(current_hash)
    
    for proof_item in proof:
        path.append(proof_item['hash'])
    
    return path

def calculate_merkle_tree_size(transactions: List[Dict[str, Any]]) -> Dict[str, int]:
    """Calculate the size of a Merkle tree in terms of nodes."""
    if not transactions:
        return {"total_nodes": 0, "leaf_nodes": 0, "internal_nodes": 0}
    
    tree = MerkleTree(transactions)
    leaf_count = tree.get_leaf_count()
    height = tree.get_tree_height()
    
    # Calculate total nodes in a complete binary tree
    total_nodes = 2 ** (height + 1) - 1
    internal_nodes = total_nodes - leaf_count
    
    return {
        "total_nodes": total_nodes,
        "leaf_nodes": leaf_count,
        "internal_nodes": internal_nodes,
        "tree_height": height
    }
