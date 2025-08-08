from collections import defaultdict, deque
import time
from storage.sqlite_storage import SQLiteStorage
from consensus.block import Block

class BlockchainMetrics:
    def __init__(self, local_node_id: str, storage: SQLiteStorage):
        self.metrics = {}
        self.tps_history = []
        self.consensus_time_history = []
        self.block_time_history = []
        self.cpu_history = []
        self.memory_history = []
        self.power_usage_history = []
        
        self.local_node_id = local_node_id
        self.storage = storage
        
        # Rolling window of transaction timestamps (seconds)
        self.transaction_events: deque[float] = deque()
        self.tps_window_seconds: int = 10
        
        # New: Store metrics for all nodes
        self.all_nodes_metrics = defaultdict(lambda: {
            'cpu_percent': 0,
            'memory_percent': 0,
            'temperature': 0,
            'power_usage': 0,
            'block_count': 0,
            'pending_transactions': 0,
            'current_stake': 0,
            'is_validator': False,
            'timestamp': 0
        })
        self.network_validators = {}
        self.current_network_validator = None

    def record_block_time(self, value):
        self.block_time_history.append(value)
        if len(self.block_time_history) > 20: # Keep last 20 for chart
            self.block_time_history.pop(0)

    def record_consensus_time(self, value):
        self.consensus_time_history.append(value)
        if len(self.consensus_time_history) > 20:
            self.consensus_time_history.pop(0)

    def record_transactions(self, count):
        """Record 'count' new transactions at the current timestamp for TPS calculation."""
        now = time.time()
        for _ in range(max(0, int(count))):
            self.transaction_events.append(now)
        # Drop events older than the window
        cutoff = now - self.tps_window_seconds
        while self.transaction_events and self.transaction_events[0] < cutoff:
            self.transaction_events.popleft()

    def record_propagation_delay(self, value):
        # For future use or specific tracking
        pass

    def record_node_metrics(self, node_id: str, metrics_data: dict):
        """Record and update metrics for a specific node."""
        self.all_nodes_metrics[node_id].update({
            'cpu_percent': metrics_data.get('cpu_percent', 0),
            'memory_percent': metrics_data.get('memory_percent', 0),
            'temperature': metrics_data.get('temperature', 0),
            'power_usage': metrics_data.get('power_usage', 0),
            'block_count': metrics_data.get('block_count', 0),
            'pending_transactions': metrics_data.get('pending_transactions', 0),
            'current_stake': metrics_data.get('current_stake', 0),
            'timestamp': time.time() # Timestamp of last update
        })
        
        # Update global validator list if included
        if 'all_validators' in metrics_data:
            self.network_validators = metrics_data['all_validators']
        
        # Update current network validator
        if 'current_network_validator' in metrics_data:
            self.current_network_validator = metrics_data['current_network_validator']

    def get_system_metrics(self) -> dict:
        # This now returns a dict of all nodes' system metrics
        return {
            node_id: {
                'cpu_percent': data['cpu_percent'],
                'memory_percent': data['memory_percent'],
                'temperature': data['temperature'],
                'power_usage': data['power_usage'],
                'block_count': data.get('block_count', 0),  # Include block count
                'pending_transactions': data.get('pending_transactions', 0),  # Include pending transactions
                'timestamp': data['timestamp']
            } for node_id, data in self.all_nodes_metrics.items()
        }

    def get_cumulative_mining_power(self) -> float:
        """Calculate cumulative power used for mining from genesis to current block."""
        # Get all blocks from storage
        total_blocks = self.get_chain_length()
        if total_blocks == 0:
            return 0.0
        
        # Get blocks from storage to calculate actual cumulative power
        blocks = self.storage.get_blocks(0, total_blocks - 1)
        cumulative_power = 0.0
        
        for block in blocks:
            # Extract power usage from block's energy metrics
            if hasattr(block, 'energy_metrics') and block.energy_metrics:
                power_usage = block.energy_metrics.get('power_usage', 0.5)
                cumulative_power += power_usage
            else:
                # Fallback to estimated power per block
                cumulative_power += 0.5
        
        return cumulative_power

    def get_power_metrics(self) -> dict:
        # Return cumulative mining power instead of current total power
        cumulative_mining_power = self.get_cumulative_mining_power()
        return {"total_power": cumulative_mining_power}

    def get_blockchain_metrics(self) -> dict:
        # This will be refined, currently mostly local node's perspective
        total_blocks = self.get_chain_length()
        return {
            "tps": self.get_tps(),
            "consensus_time_avg": sum(self.consensus_time_history) / len(self.consensus_time_history) if self.consensus_time_history else 0,
            "block_time_avg": sum(self.block_time_history) / len(self.block_time_history) if self.block_time_history else 0,
            "total_blocks": total_blocks, # Updated to use get_chain_length
            "merkle_tree_stats": self.get_merkle_tree_stats()
        }
    
    def get_merkle_tree_stats(self) -> dict:
        """Get statistics about Merkle tree usage across the blockchain."""
        try:
            # Get recent blocks to analyze Merkle tree statistics
            recent_blocks = self.storage.get_blocks(max(0, self.get_chain_length() - 10), -1)
            
            total_transactions = 0
            merkle_roots_present = 0
            avg_tree_height = 0
            tree_heights = []
            
            for block in recent_blocks:
                if block.merkle_tree:
                    merkle_roots_present += 1
                    total_transactions += block.merkle_tree.get_leaf_count()
                    tree_heights.append(block.merkle_tree.get_tree_height())
            
            avg_tree_height = sum(tree_heights) / len(tree_heights) if tree_heights else 0
            
            return {
                "blocks_with_merkle_trees": merkle_roots_present,
                "total_transactions_in_trees": total_transactions,
                "average_tree_height": avg_tree_height,
                "merkle_tree_utilization_rate": merkle_roots_present / len(recent_blocks) if recent_blocks else 0
            }
        except Exception as e:
            print(f"[METRICS] Error getting Merkle tree stats: {e}")
            return {
                "blocks_with_merkle_trees": 0,
                "total_transactions_in_trees": 0,
                "average_tree_height": 0,
                "merkle_tree_utilization_rate": 0
            }

    def get_blockchain_size(self) -> int:
        """Return a proxy for the total blockchain size (e.g., total blocks * average block size)."""
        # This is a rough estimation. A more accurate size would involve serializing and measuring actual blocks.
        total_blocks = self.get_chain_length()
        # Assuming an average block size of 1KB (1024 bytes) as a rough estimate
        # In a real scenario, you'd calculate actual block sizes or store them.
        approx_block_size_bytes = 1024 
        return total_blocks * approx_block_size_bytes # Updated to use total_blocks from get_chain_length

    def get_all_validators_metrics(self) -> dict:
        """Return the current view of all validators and their stakes."""
        return self.network_validators

    def get_current_elected_validator(self) -> str | None:
        """Return the current elected validator."""
        return self.current_network_validator

    def get_tps(self) -> float:
        """Compute transactions per second across all nodes over the rolling window."""
        now = time.time()
        cutoff = now - self.tps_window_seconds
        # Trim old events
        while self.transaction_events and self.transaction_events[0] < cutoff:
            self.transaction_events.popleft()
        if not self.transaction_events:
            return 0.0
        window_span = max(1e-6, min(self.tps_window_seconds, (self.transaction_events[-1] - self.transaction_events[0]) or self.tps_window_seconds))
        return len(self.transaction_events) / window_span

    def get_chain_length(self) -> int:
        """Return the current length of the blockchain from storage."""
        return self.storage.get_chain_length()

    def get_latest_block_hash(self) -> str | None:
        """Return the hash of the latest block from storage."""
        latest_block = self.storage.get_latest_block()
        return latest_block.hash if latest_block else None

    def get_blocks_from_storage(self, start_block_index: int, end_block_index: int) -> list:
        """Retrieve a range of blocks from storage."""
        return self.storage.get_blocks(start_block_index, end_block_index) 