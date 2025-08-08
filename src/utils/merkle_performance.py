import time
import statistics
from typing import Dict, List, Any
from collections import defaultdict
from .merkle_tree import MerkleTree

class MerklePerformanceMonitor:
    """Monitor performance metrics for Merkle tree operations."""
    
    def __init__(self):
        self.operation_times = defaultdict(list)
        self.operation_counts = defaultdict(int)
        self.tree_sizes = []
        self.verification_times = []
        self.proof_generation_times = []
        
    def record_operation(self, operation: str, duration: float, **kwargs):
        """Record the time taken for a Merkle tree operation."""
        self.operation_times[operation].append(duration)
        self.operation_counts[operation] += 1
        
        # Store additional metrics
        if operation == "tree_creation":
            self.tree_sizes.append(kwargs.get('transaction_count', 0))
        elif operation == "proof_verification":
            self.verification_times.append(duration)
        elif operation == "proof_generation":
            self.proof_generation_times.append(duration)
    
    def measure_tree_creation(self, transactions: List[Dict[str, Any]]) -> MerkleTree:
        """Measure the time taken to create a Merkle tree."""
        start_time = time.time()
        tree = MerkleTree(transactions)
        duration = time.time() - start_time
        
        self.record_operation("tree_creation", duration, transaction_count=len(transactions))
        return tree
    
    def measure_proof_generation(self, tree: MerkleTree, transaction_index: int) -> List[Dict[str, Any]]:
        """Measure the time taken to generate a Merkle proof."""
        start_time = time.time()
        proof = tree.get_proof(transaction_index)
        duration = time.time() - start_time
        
        self.record_operation("proof_generation", duration)
        return proof
    
    def measure_proof_verification(self, tree: MerkleTree, transaction: Dict[str, Any], proof: List[Dict[str, Any]]) -> bool:
        """Measure the time taken to verify a Merkle proof."""
        start_time = time.time()
        result = tree.verify_proof(transaction, proof, tree.get_root_hash())
        duration = time.time() - start_time
        
        self.record_operation("proof_verification", duration)
        return result
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        stats = {}
        
        for operation, times in self.operation_times.items():
            if times:
                stats[operation] = {
                    "count": self.operation_counts[operation],
                    "avg_time": statistics.mean(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "total_time": sum(times)
                }
        
        # Additional Merkle-specific stats
        if self.tree_sizes:
            stats["tree_sizes"] = {
                "avg_transactions": statistics.mean(self.tree_sizes),
                "max_transactions": max(self.tree_sizes),
                "min_transactions": min(self.tree_sizes)
            }
        
        if self.verification_times:
            stats["verification_performance"] = {
                "avg_verification_time": statistics.mean(self.verification_times),
                "verification_count": len(self.verification_times)
            }
        
        if self.proof_generation_times:
            stats["proof_generation_performance"] = {
                "avg_generation_time": statistics.mean(self.proof_generation_times),
                "generation_count": len(self.proof_generation_times)
            }
        
        return stats
    
    def get_efficiency_metrics(self) -> Dict[str, float]:
        """Get efficiency metrics for Merkle tree operations."""
        stats = self.get_performance_stats()
        efficiency = {}
        
        # Calculate operations per second
        for operation, data in stats.items():
            if isinstance(data, dict) and "total_time" in data and data["total_time"] > 0:
                efficiency[f"{operation}_ops_per_second"] = data["count"] / data["total_time"]
        
        # Calculate average proof size (if available)
        if "proof_generation" in stats:
            # Estimate proof size based on tree height
            avg_tree_height = stats.get("tree_sizes", {}).get("avg_transactions", 10)
            if avg_tree_height > 0:
                estimated_proof_size = max(1, int(statistics.log2(avg_tree_height)))
            else:
                estimated_proof_size = 1
            efficiency["estimated_avg_proof_size"] = estimated_proof_size
        
        return efficiency
    
    def compare_with_linear_search(self, transaction_count: int) -> Dict[str, Any]:
        """Compare Merkle tree performance with linear search."""
        # Simulate linear search time (O(n))
        linear_search_time = transaction_count * 0.0001  # 0.1ms per transaction
        
        # Get Merkle tree verification time
        avg_verification_time = 0
        if self.verification_times:
            avg_verification_time = statistics.mean(self.verification_times)
        
        improvement_factor = linear_search_time / avg_verification_time if avg_verification_time > 0 else 1
        
        return {
            "linear_search_time": linear_search_time,
            "merkle_verification_time": avg_verification_time,
            "improvement_factor": improvement_factor,
            "efficiency_gain": f"{improvement_factor:.2f}x faster"
        }
    
    def reset_metrics(self):
        """Reset all performance metrics."""
        self.operation_times.clear()
        self.operation_counts.clear()
        self.tree_sizes.clear()
        self.verification_times.clear()
        self.proof_generation_times.clear()
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for analysis."""
        return {
            "performance_stats": self.get_performance_stats(),
            "efficiency_metrics": self.get_efficiency_metrics(),
            "operation_counts": dict(self.operation_counts),
            "tree_sizes": self.tree_sizes.copy(),
            "verification_times": self.verification_times.copy(),
            "proof_generation_times": self.proof_generation_times.copy()
        }

# Global instance for easy access
merkle_performance_monitor = MerklePerformanceMonitor()
