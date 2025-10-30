from collections import defaultdict, deque
import time
import threading
from typing import Any, Dict, List, Optional
import psutil
from storage.sqlite_storage import SQLiteStorage
from consensus.block import Block
from contextlib import contextmanager

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

        # Resource/operation monitoring additions
        self.resource_metrics_history: deque[Dict[str, Any]] = deque(maxlen=100)
        self.operation_metrics: Dict[str, List[Dict[str, Any]]] = {
            'block_validation': [],
            'block_creation': [],
            'network_operations': [],
            'database_operations': []
        }
        self._lock = threading.Lock()

    @contextmanager
    def monitor_operation(self, operation_type: str, operation_id: Optional[str] = None):
        """Context manager to record detailed resource metrics for an operation."""
        start_time = time.time()
        # Initial snapshots
        cpu_initial = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        memory_initial_mb = mem.used / (1024 * 1024)
        net0 = psutil.net_io_counters()
        try:
            yield
        finally:
            end_time = time.time()
            duration = end_time - start_time
            cpu_final = psutil.cpu_percent(interval=None)
            cpu_avg = (cpu_initial + cpu_final) / 2.0
            mem2 = psutil.virtual_memory()
            memory_final_mb = mem2.used / (1024 * 1024)
            memory_delta_mb = memory_final_mb - memory_initial_mb
            net1 = psutil.net_io_counters()
            entry = {
                'operation_id': operation_id or f"{operation_type}-{int(start_time*1000)}",
                'operation_type': operation_type,
                'start_time': start_time,
                'end_time': end_time,
                'duration': duration,
                'cpu_usage': {
                    'initial': cpu_initial,
                    'final': cpu_final,
                    'avg': cpu_avg
                },
                'memory_usage': {
                    'initial_mb': memory_initial_mb,
                    'final_mb': memory_final_mb,
                    'memory_delta_mb': memory_delta_mb
                },
                'network_usage': {
                    'bytes_sent': max(0, net1.bytes_sent - net0.bytes_sent),
                    'bytes_recv': max(0, net1.bytes_recv - net0.bytes_recv),
                    'packets_sent': max(0, net1.packets_sent - net0.packets_sent),
                    'packets_recv': max(0, net1.packets_recv - net0.packets_recv)
                }
            }
            with self._lock:
                self.resource_metrics_history.append(entry)
                # Only block_* operations should be duplicated into operation_metrics for CSV
                if operation_type in ('block_creation', 'block_validation'):
                    self.operation_metrics[operation_type].append(entry)

    def record_network_operation(self, operation: str, bytes_transferred: float, duration: float, success: bool = True) -> None:
        throughput_mbps = 0.0
        if duration > 0 and bytes_transferred is not None:
            throughput_mbps = (bytes_transferred * 8.0) / (duration * 1_000_000)
        record = {
            'operation': operation,
            'timestamp': time.time(),
            'bytes_transferred': bytes_transferred or 0,
            'duration': duration,
            'success': success,
            'throughput_mbps': throughput_mbps
        }
        with self._lock:
            self.operation_metrics['network_operations'].append(record)

    def record_database_operation(self, operation: str, duration: float, rows_affected: int = 0) -> None:
        throughput_rows = (rows_affected / duration) if duration > 0 else 0.0
        record = {
            'operation': operation,
            'timestamp': time.time(),
            'duration': duration,
            'rows_affected': rows_affected,
            'throughput_rows_per_sec': throughput_rows
        }
        with self._lock:
            self.operation_metrics['database_operations'].append(record)

    def get_resource_metrics(self) -> Dict[str, Any]:
        try:
            # Summaries per type
            def summarize_block_ops(items: List[Dict[str, Any]]) -> Dict[str, Any]:
                if not items:
                    return {'count': 0, 'avg_duration': 0, 'avg_cpu': 0, 'avg_memory_delta': 0, 'total_network_bytes': 0}
                count = len(items)
                avg_duration = sum(i.get('duration', 0) for i in items) / count
                avg_cpu = sum(i.get('cpu_usage', {}).get('avg', 0) for i in items) / count
                avg_mem_delta = sum(i.get('memory_usage', {}).get('memory_delta_mb', 0) for i in items) / count
                total_net = sum((i.get('network_usage', {}).get('bytes_sent', 0) + i.get('network_usage', {}).get('bytes_recv', 0)) for i in items)
                return {
                    'count': count,
                    'avg_duration': avg_duration,
                    'avg_cpu': avg_cpu,
                    'avg_memory_delta_mb': avg_mem_delta,
                    'total_network_bytes': total_net
                }

            def summarize_network_ops(items: List[Dict[str, Any]]) -> Dict[str, Any]:
                if not items:
                    return {'count': 0, 'avg_duration': 0, 'total_bytes_transferred': 0, 'avg_throughput_mbps': 0}
                count = len(items)
                avg_duration = sum(i.get('duration', 0) for i in items) / count
                total_bytes = sum(i.get('bytes_transferred', 0) for i in items)
                avg_tp = sum(i.get('throughput_mbps', 0) for i in items) / count
                return {
                    'count': count,
                    'avg_duration': avg_duration,
                    'total_bytes_transferred': total_bytes,
                    'avg_throughput_mbps': avg_tp
                }

            def summarize_db_ops(items: List[Dict[str, Any]]) -> Dict[str, Any]:
                if not items:
                    return {'count': 0, 'avg_duration': 0, 'total_rows_affected': 0, 'avg_throughput_rows_per_sec': 0}
                count = len(items)
                avg_duration = sum(i.get('duration', 0) for i in items) / count
                total_rows = sum(i.get('rows_affected', 0) for i in items)
                avg_tp = sum(i.get('throughput_rows_per_sec', 0) for i in items) / count
                return {
                    'count': count,
                    'avg_duration': avg_duration,
                    'total_rows_affected': total_rows,
                    'avg_throughput_rows_per_sec': avg_tp
                }

            with self._lock:
                recent_ops = list(self.resource_metrics_history)
                summaries = {
                    'block_creation': summarize_block_ops(self.operation_metrics['block_creation']),
                    'block_validation': summarize_block_ops(self.operation_metrics['block_validation']),
                    'network_operations': summarize_network_ops(self.operation_metrics['network_operations']),
                    'database_operations': summarize_db_ops(self.operation_metrics['database_operations'])
                }

            # Current system state snapshot
            vm = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            net = psutil.net_io_counters()
            current_state = {
                'cpu_percent': psutil.cpu_percent(interval=None),
                'memory_percent': vm.percent,
                'memory_available_mb': vm.available / (1024 * 1024),
                'disk_usage_percent': disk.percent,
                'network_io': {
                    'bytes_sent': net.bytes_sent,
                    'bytes_recv': net.bytes_recv,
                    'packets_sent': net.packets_sent,
                    'packets_recv': net.packets_recv
                }
            }

            return {
                'recent_operations': recent_ops,
                'operation_summaries': summaries,
                'current_system_state': current_state
            }
        except Exception as e:
            return {
                'recent_operations': [],
                'operation_summaries': {},
                'current_system_state': {'error': str(e)}
            }

    def get_operation_metrics(self, operation_type: Optional[str] = None):
        with self._lock:
            if operation_type:
                return self.operation_metrics.get(operation_type, [])
            return self.operation_metrics

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