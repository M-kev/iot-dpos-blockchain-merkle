import unittest
import time
import json
from typing import List, Dict, Any
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.merkle_tree import MerkleTree, MerkleNode
from utils.merkle_utils import (
    create_merkle_tree_from_transactions,
    verify_transaction_in_block,
    calculate_merkle_root,
    generate_merkle_proof,
    batch_verify_transactions,
    get_merkle_tree_stats,
    optimize_merkle_tree_for_verification,
    validate_merkle_tree_integrity,
    get_merkle_path_for_transaction,
    calculate_merkle_tree_size
)
from utils.merkle_performance import MerklePerformanceMonitor

class TestMerkleTree(unittest.TestCase):
    
    def setUp(self):
        """Set up test data."""
        self.sample_transactions = [
            {"type": "transfer", "from": "alice", "to": "bob", "amount": 100, "timestamp": 1234567890},
            {"type": "transfer", "from": "bob", "to": "charlie", "amount": 50, "timestamp": 1234567891},
            {"type": "stake", "from": "alice", "amount": 1000, "timestamp": 1234567892},
            {"type": "transfer", "from": "charlie", "to": "david", "amount": 25, "timestamp": 1234567893}
        ]
        
        self.empty_transactions = []
        self.single_transaction = [{"type": "transfer", "from": "alice", "to": "bob", "amount": 100}]
    
    def test_merkle_tree_creation(self):
        """Test basic Merkle tree creation."""
        tree = MerkleTree(self.sample_transactions)
        
        self.assertIsNotNone(tree.root)
        self.assertEqual(len(tree.leaf_nodes), 4)
        self.assertEqual(tree.get_leaf_count(), 4)
        self.assertGreater(tree.get_tree_height(), 0)
    
    def test_empty_merkle_tree(self):
        """Test Merkle tree with no transactions."""
        tree = MerkleTree(self.empty_transactions)
        
        self.assertIsNotNone(tree.root)
        self.assertEqual(tree.get_root_hash(), "0" * 64)
        self.assertEqual(tree.get_leaf_count(), 0)
        self.assertEqual(tree.get_tree_height(), 0)
    
    def test_single_transaction_merkle_tree(self):
        """Test Merkle tree with single transaction."""
        tree = MerkleTree(self.single_transaction)
        
        self.assertIsNotNone(tree.root)
        self.assertEqual(tree.get_leaf_count(), 1)
        self.assertEqual(tree.get_tree_height(), 0)
    
    def test_merkle_proof_generation(self):
        """Test Merkle proof generation."""
        tree = MerkleTree(self.sample_transactions)
        
        # Test proof for first transaction
        proof = tree.get_proof(0)
        self.assertIsInstance(proof, list)
        self.assertGreater(len(proof), 0)
        
        # Test proof for last transaction
        proof = tree.get_proof(3)
        self.assertIsInstance(proof, list)
    
    def test_merkle_proof_verification(self):
        """Test Merkle proof verification."""
        tree = MerkleTree(self.sample_transactions)
        
        # Generate proof for first transaction
        proof = tree.get_proof(0)
        transaction = self.sample_transactions[0]
        
        # Verify the proof
        is_valid = tree.verify_proof(transaction, proof, tree.get_root_hash())
        self.assertTrue(is_valid)
        
        # Test with invalid transaction
        invalid_transaction = {"type": "invalid", "data": "fake"}
        is_valid = tree.verify_proof(invalid_transaction, proof, tree.get_root_hash())
        self.assertFalse(is_valid)
    
    def test_merkle_tree_serialization(self):
        """Test Merkle tree serialization and deserialization."""
        tree = MerkleTree(self.sample_transactions)
        
        # Convert to dictionary
        tree_dict = tree.to_dict()
        self.assertIn('root_hash', tree_dict)
        self.assertIn('leaf_count', tree_dict)
        self.assertIn('transactions', tree_dict)
        
        # Recreate from dictionary
        new_tree = MerkleTree.from_dict(tree_dict)
        self.assertEqual(new_tree.get_root_hash(), tree.get_root_hash())
        self.assertEqual(new_tree.get_leaf_count(), tree.get_leaf_count())
    
    def test_transaction_index_finding(self):
        """Test finding transaction index in Merkle tree."""
        tree = MerkleTree(self.sample_transactions)
        
        # Find existing transaction
        index = tree.find_transaction_index(self.sample_transactions[1])
        self.assertEqual(index, 1)
        
        # Find non-existent transaction
        index = tree.find_transaction_index({"type": "fake"})
        self.assertIsNone(index)
    
    def test_merkle_utils_functions(self):
        """Test utility functions."""
        # Test create_merkle_tree_from_transactions
        tree = create_merkle_tree_from_transactions(self.sample_transactions)
        self.assertIsInstance(tree, MerkleTree)
        
        # Test calculate_merkle_root
        root = calculate_merkle_root(self.sample_transactions)
        self.assertEqual(root, tree.get_root_hash())
        
        # Test generate_merkle_proof
        proof = generate_merkle_proof(self.sample_transactions, self.sample_transactions[0])
        self.assertIsInstance(proof, list)
        
        # Test verify_transaction_in_block
        is_valid = verify_transaction_in_block(root, self.sample_transactions[0], proof)
        self.assertTrue(is_valid)
        
        # Test batch verification
        proofs = [tree.get_proof(i) for i in range(len(self.sample_transactions))]
        results = batch_verify_transactions(root, self.sample_transactions, proofs)
        self.assertEqual(len(results), len(self.sample_transactions))
        self.assertTrue(all(results))
        
        # Test get_merkle_tree_stats
        stats = get_merkle_tree_stats(self.sample_transactions)
        self.assertIn('leaf_count', stats)
        self.assertIn('tree_height', stats)
        self.assertIn('root_hash', stats)
        
        # Test validate_merkle_tree_integrity
        is_valid = validate_merkle_tree_integrity(root, self.sample_transactions)
        self.assertTrue(is_valid)
        
        # Test calculate_merkle_tree_size
        size_info = calculate_merkle_tree_size(self.sample_transactions)
        self.assertIn('total_nodes', size_info)
        self.assertIn('leaf_nodes', size_info)
        self.assertIn('internal_nodes', size_info)
    
    def test_merkle_performance_monitor(self):
        """Test Merkle performance monitoring."""
        monitor = MerklePerformanceMonitor()
        
        # Test tree creation measurement
        tree = monitor.measure_tree_creation(self.sample_transactions)
        self.assertIsInstance(tree, MerkleTree)
        
        # Test proof generation measurement
        proof = monitor.measure_proof_generation(tree, 0)
        self.assertIsInstance(proof, list)
        
        # Test proof verification measurement
        is_valid = monitor.measure_proof_verification(tree, self.sample_transactions[0], proof)
        self.assertTrue(is_valid)
        
        # Test performance stats
        stats = monitor.get_performance_stats()
        self.assertIn('tree_creation', stats)
        self.assertIn('proof_generation', stats)
        self.assertIn('proof_verification', stats)
        
        # Test efficiency metrics
        efficiency = monitor.get_efficiency_metrics()
        self.assertIsInstance(efficiency, dict)
        
        # Test comparison with linear search
        comparison = monitor.compare_with_linear_search(100)
        self.assertIn('improvement_factor', comparison)
        self.assertIn('efficiency_gain', comparison)
    
    def test_merkle_tree_performance(self):
        """Test Merkle tree performance with larger datasets."""
        # Create larger dataset
        large_transactions = []
        for i in range(100):
            large_transactions.append({
                "type": "transfer",
                "from": f"user_{i}",
                "to": f"user_{(i + 1) % 100}",
                "amount": i * 10,
                "timestamp": 1234567890 + i
            })
        
        # Measure performance
        start_time = time.time()
        tree = MerkleTree(large_transactions)
        creation_time = time.time() - start_time
        
        # Verify reasonable performance
        self.assertLess(creation_time, 1.0)  # Should complete within 1 second
        
        # Test proof generation performance
        start_time = time.time()
        proof = tree.get_proof(50)
        proof_time = time.time() - start_time
        
        self.assertLess(proof_time, 0.1)  # Should complete within 100ms
        
        # Test verification performance
        start_time = time.time()
        is_valid = tree.verify_proof(large_transactions[50], proof, tree.get_root_hash())
        verification_time = time.time() - start_time
        
        self.assertTrue(is_valid)
        self.assertLess(verification_time, 0.1)  # Should complete within 100ms
    
    def test_merkle_tree_edge_cases(self):
        """Test edge cases for Merkle tree."""
        # Test with very large number of transactions
        many_transactions = [{"id": i, "data": f"transaction_{i}"} for i in range(1000)]
        tree = MerkleTree(many_transactions)
        
        self.assertEqual(tree.get_leaf_count(), 1000)
        self.assertGreater(tree.get_tree_height(), 0)
        
        # Test proof for middle transaction
        proof = tree.get_proof(500)
        is_valid = tree.verify_proof(many_transactions[500], proof, tree.get_root_hash())
        self.assertTrue(is_valid)
        
        # Test with duplicate transactions
        duplicate_transactions = self.sample_transactions + self.sample_transactions
        tree = MerkleTree(duplicate_transactions)
        self.assertEqual(tree.get_leaf_count(), 8)
    
    def test_merkle_tree_consistency(self):
        """Test that Merkle trees are consistent for same transactions."""
        tree1 = MerkleTree(self.sample_transactions)
        tree2 = MerkleTree(self.sample_transactions)
        
        self.assertEqual(tree1.get_root_hash(), tree2.get_root_hash())
        
        # Test that proofs from one tree work with the other
        proof = tree1.get_proof(0)
        is_valid = tree2.verify_proof(self.sample_transactions[0], proof, tree2.get_root_hash())
        self.assertTrue(is_valid)

if __name__ == '__main__':
    unittest.main()
