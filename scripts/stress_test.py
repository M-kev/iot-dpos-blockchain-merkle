#!/usr/bin/env python3
"""
IoT Blockchain Stress Test Suite
A comprehensive stress testing framework for IoT blockchain nodes.

This script can be used to test any blockchain implementation by configuring
the appropriate endpoints and parameters.

Features:
- CPU usage profiling
- Heat production monitoring
- Energy consumption tracking
- Performance degradation analysis
- Configurable transaction generation
- Real-time metrics collection
- Comprehensive reporting
"""

import asyncio
import aiohttp
import time
import json
import psutil
import subprocess
import threading
import statistics
import argparse
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import logging
import csv
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stress_test.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class NodeConfig:
    """Configuration for a blockchain node."""
    name: str
    host: str
    port: int
    api_base: str = "/api"
    username: Optional[str] = None
    password: Optional[str] = None

@dataclass
class TestConfig:
    """Configuration for stress test parameters."""
    duration_minutes: int = 30
    transaction_rate_per_second: int = 10
    concurrent_requests: int = 5
    warmup_seconds: int = 60
    cooldown_seconds: int = 30
    metrics_interval_seconds: int = 5
    enable_cpu_profiling: bool = True
    enable_heat_monitoring: bool = True
    enable_energy_monitoring: bool = True
    enable_performance_analysis: bool = True

@dataclass
class SystemMetrics:
    """System metrics collected during testing."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    temperature_celsius: Optional[float]
    power_consumption_watts: Optional[float]
    network_bytes_sent: int
    network_bytes_recv: int
    disk_io_read_bytes: int
    disk_io_write_bytes: int

@dataclass
class BlockchainMetrics:
    """Blockchain-specific metrics."""
    timestamp: float
    chain_length: int
    latest_block_hash: str
    transactions_per_second: float
    block_time_seconds: float
    pending_transactions: int
    node_status: str

@dataclass
class TestResult:
    """Results from a stress test."""
    test_name: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    avg_response_time: float
    max_response_time: float
    min_response_time: float
    system_metrics: List[SystemMetrics]
    blockchain_metrics: List[BlockchainMetrics]
    performance_degradation: Dict[str, float]

class IoTStressTester:
    """Main stress testing class for IoT blockchain nodes."""
    
    def __init__(self, nodes: List[NodeConfig], config: TestConfig):
        self.nodes = nodes
        self.config = config
        self.results: List[TestResult] = []
        self.running = False
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Metrics storage
        self.system_metrics: List[SystemMetrics] = []
        self.blockchain_metrics: List[BlockchainMetrics] = []
        self.response_times: List[float] = []
        
        # Performance tracking
        self.performance_baseline: Dict[str, float] = {}
        self.performance_current: Dict[str, float] = {}
        
        # Threading
        self.metrics_thread: Optional[threading.Thread] = None
        self.transaction_thread: Optional[threading.Thread] = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def get_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics."""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # Network I/O
            net_io = psutil.net_io_counters()
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            
            # Temperature (Raspberry Pi specific)
            temperature = self._get_temperature()
            
            # Power consumption (if available)
            power_consumption = self._get_power_consumption()
            
            return SystemMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                temperature_celsius=temperature,
                power_consumption_watts=power_consumption,
                network_bytes_sent=net_io.bytes_sent,
                network_bytes_recv=net_io.bytes_recv,
                disk_io_read_bytes=disk_io.read_bytes if disk_io else 0,
                disk_io_write_bytes=disk_io.write_bytes if disk_io else 0
            )
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics(
                timestamp=time.time(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                temperature_celsius=None,
                power_consumption_watts=None,
                network_bytes_sent=0,
                network_bytes_recv=0,
                disk_io_read_bytes=0,
                disk_io_write_bytes=0
            )
    
    def _get_temperature(self) -> Optional[float]:
        """Get CPU temperature for Raspberry Pi."""
        try:
            # Try different temperature file locations
            temp_files = [
                "/sys/class/thermal/thermal_zone0/temp",
                "/sys/devices/virtual/thermal/thermal_zone0/temp",
                "/proc/acpi/thermal_zone/THM0/temperature"
            ]
            
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    with open(temp_file, 'r') as f:
                        temp_raw = f.read().strip()
                        # Convert from millidegrees to degrees Celsius
                        return float(temp_raw) / 1000.0
            
            # Try using vcgencmd (Raspberry Pi specific)
            result = subprocess.run(
                ["vcgencmd", "measure_temp"], 
                capture_output=True, 
                text=True
            )
            if result.returncode == 0:
                temp_str = result.stdout.strip()
                return float(temp_str.replace("temp=", "").replace("'C", ""))
                
        except Exception as e:
            logger.warning(f"Could not read temperature: {e}")
        
        return None
    
    def _get_power_consumption(self) -> Optional[float]:
        """Get power consumption if available."""
        try:
            # Try to read from power monitoring tools
            # This is hardware-specific and may need customization
            
            # Example for devices with power monitoring
            power_files = [
                "/sys/class/power_supply/BAT0/power_now",
                "/sys/class/power_supply/AC/power_now"
            ]
            
            for power_file in power_files:
                if os.path.exists(power_file):
                    with open(power_file, 'r') as f:
                        power_raw = f.read().strip()
                        # Convert from microwatts to watts
                        return float(power_raw) / 1000000.0
                        
        except Exception as e:
            logger.warning(f"Could not read power consumption: {e}")
        
        return None
    
    async def get_blockchain_metrics(self, node: NodeConfig) -> BlockchainMetrics:
        """Collect blockchain-specific metrics from a node."""
        try:
            # Get chain info
            chain_info_url = f"http://{node.host}:{node.port}{node.api_base}/chain_info"
            async with self.session.get(chain_info_url) as response:
                if response.status == 200:
                    chain_data = await response.json()
                    chain_length = chain_data.get('chain_length', 0)
                    latest_block_hash = chain_data.get('latest_block_hash', '')
                else:
                    chain_length = 0
                    latest_block_hash = ''
            
            # Get performance metrics if available
            perf_url = f"http://{node.host}:{node.port}{node.api_base}/merkle-performance"
            tps = 0.0
            block_time = 0.0
            pending_tx = 0
            
            try:
                async with self.session.get(perf_url) as response:
                    if response.status == 200:
                        perf_data = await response.json()
                        # Extract TPS from performance data
                        efficiency = perf_data.get('efficiency_metrics', {})
                        tps = efficiency.get('block_creation_with_merkle_ops_per_second', 0.0)
            except:
                pass
            
            return BlockchainMetrics(
                timestamp=time.time(),
                chain_length=chain_length,
                latest_block_hash=latest_block_hash,
                transactions_per_second=tps,
                block_time_seconds=block_time,
                pending_transactions=pending_tx,
                node_status="online"
            )
            
        except Exception as e:
            logger.error(f"Error collecting blockchain metrics from {node.name}: {e}")
            return BlockchainMetrics(
                timestamp=time.time(),
                chain_length=0,
                latest_block_hash='',
                transactions_per_second=0.0,
                block_time_seconds=0.0,
                pending_transactions=0,
                node_status="error"
            )
    
    async def send_test_transaction(self, node: NodeConfig) -> Tuple[bool, float]:
        """Send a test transaction to a node."""
        start_time = time.time()
        success = False
        
        try:
            # Create a test transaction payload
            transaction = {
                "sender": f"stress_test_{int(time.time())}",
                "recipient": f"test_recipient_{int(time.time())}",
                "amount": 1.0,
                "timestamp": time.time(),
                "data": f"stress_test_transaction_{int(time.time())}"
            }
            
            # Try different transaction endpoints
            endpoints = [
                f"/transactions",
                f"/transaction",
                f"/tx",
                f"/submit_transaction"
            ]
            
            for endpoint in endpoints:
                try:
                    url = f"http://{node.host}:{node.port}{node.api_base}{endpoint}"
                    async with self.session.post(
                        url, 
                        json=transaction,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status in [200, 201, 202]:
                            success = True
                            break
                except:
                    continue
            
            response_time = time.time() - start_time
            return success, response_time
            
        except Exception as e:
            logger.error(f"Error sending transaction to {node.name}: {e}")
            response_time = time.time() - start_time
            return False, response_time
    
    def collect_metrics_loop(self):
        """Background thread for collecting system metrics."""
        while self.running:
            try:
                # Collect system metrics
                system_metric = self.get_system_metrics()
                self.system_metrics.append(system_metric)
                
                # Collect blockchain metrics from all nodes
                asyncio.run(self._collect_blockchain_metrics())
                
                time.sleep(self.config.metrics_interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in metrics collection loop: {e}")
                time.sleep(self.config.metrics_interval_seconds)
    
    async def _collect_blockchain_metrics(self):
        """Collect blockchain metrics from all nodes."""
        for node in self.nodes:
            try:
                metric = await self.get_blockchain_metrics(node)
                self.blockchain_metrics.append(metric)
            except Exception as e:
                logger.error(f"Error collecting metrics from {node.name}: {e}")
    
    def generate_transactions_loop(self):
        """Background thread for generating transactions."""
        while self.running:
            try:
                # Send transactions to all nodes
                asyncio.run(self._send_transactions_batch())
                
                # Sleep based on transaction rate
                sleep_time = 1.0 / self.config.transaction_rate_per_second
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error in transaction generation loop: {e}")
                time.sleep(1)
    
    async def _send_transactions_batch(self):
        """Send a batch of transactions to all nodes."""
        tasks = []
        for node in self.nodes:
            for _ in range(self.config.concurrent_requests):
                task = self.send_test_transaction(node)
                tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for success, response_time in results:
            if isinstance(success, bool):
                self.response_times.append(response_time)
    
    def calculate_performance_degradation(self) -> Dict[str, float]:
        """Calculate performance degradation over time."""
        if len(self.response_times) < 10:
            return {}
        
        # Split response times into quarters
        quarter_size = len(self.response_times) // 4
        quarters = [
            self.response_times[:quarter_size],
            self.response_times[quarter_size:2*quarter_size],
            self.response_times[2*quarter_size:3*quarter_size],
            self.response_times[3*quarter_size:]
        ]
        
        degradation = {}
        
        # Calculate degradation between quarters
        for i in range(1, len(quarters)):
            if quarters[i-1] and quarters[i]:
                baseline_avg = statistics.mean(quarters[i-1])
                current_avg = statistics.mean(quarters[i])
                degradation[f"q{i-1}_to_q{i}"] = ((current_avg - baseline_avg) / baseline_avg) * 100
        
        return degradation
    
    async def run_stress_test(self, test_name: str = "IoT_Blockchain_Stress_Test") -> TestResult:
        """Run the complete stress test."""
        logger.info(f"Starting stress test: {test_name}")
        start_time = datetime.now()
        
        # Initialize metrics
        self.system_metrics = []
        self.blockchain_metrics = []
        self.response_times = []
        
        # Start background threads
        self.running = True
        self.metrics_thread = threading.Thread(target=self.collect_metrics_loop)
        self.transaction_thread = threading.Thread(target=self.generate_transactions_loop)
        
        self.metrics_thread.start()
        self.transaction_thread.start()
        
        # Warmup period
        logger.info(f"Warmup period: {self.config.warmup_seconds} seconds")
        await asyncio.sleep(self.config.warmup_seconds)
        
        # Main test period
        logger.info(f"Main test period: {self.config.duration_minutes} minutes")
        await asyncio.sleep(self.config.duration_minutes * 60)
        
        # Cooldown period
        logger.info(f"Cooldown period: {self.config.cooldown_seconds} seconds")
        await asyncio.sleep(self.config.cooldown_seconds)
        
        # Stop background threads
        self.running = False
        self.metrics_thread.join()
        self.transaction_thread.join()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Calculate results
        successful_tx = len([rt for rt in self.response_times if rt < 10])  # Assume < 10s is success
        failed_tx = len(self.response_times) - successful_tx
        
        avg_response_time = statistics.mean(self.response_times) if self.response_times else 0
        max_response_time = max(self.response_times) if self.response_times else 0
        min_response_time = min(self.response_times) if self.response_times else 0
        
        performance_degradation = self.calculate_performance_degradation()
        
        result = TestResult(
            test_name=test_name,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            total_transactions=len(self.response_times),
            successful_transactions=successful_tx,
            failed_transactions=failed_tx,
            avg_response_time=avg_response_time,
            max_response_time=max_response_time,
            min_response_time=min_response_time,
            system_metrics=self.system_metrics,
            blockchain_metrics=self.blockchain_metrics,
            performance_degradation=performance_degradation
        )
        
        self.results.append(result)
        return result
    
    def generate_report(self, result: TestResult, output_dir: str = "stress_test_results"):
        """Generate comprehensive test report."""
        os.makedirs(output_dir, exist_ok=True)
        
        # Save raw data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save system metrics
        system_csv = os.path.join(output_dir, f"system_metrics_{timestamp}.csv")
        with open(system_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'cpu_percent', 'memory_percent', 'memory_used_mb',
                'temperature_celsius', 'power_consumption_watts',
                'network_bytes_sent', 'network_bytes_recv',
                'disk_io_read_bytes', 'disk_io_write_bytes'
            ])
            for metric in result.system_metrics:
                writer.writerow([
                    metric.timestamp, metric.cpu_percent, metric.memory_percent,
                    metric.memory_used_mb, metric.temperature_celsius,
                    metric.power_consumption_watts, metric.network_bytes_sent,
                    metric.network_bytes_recv, metric.disk_io_read_bytes,
                    metric.disk_io_write_bytes
                ])
        
        # Save blockchain metrics
        blockchain_csv = os.path.join(output_dir, f"blockchain_metrics_{timestamp}.csv")
        with open(blockchain_csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'timestamp', 'chain_length', 'latest_block_hash',
                'transactions_per_second', 'block_time_seconds',
                'pending_transactions', 'node_status'
            ])
            for metric in result.blockchain_metrics:
                writer.writerow([
                    metric.timestamp, metric.chain_length, metric.latest_block_hash,
                    metric.transactions_per_second, metric.block_time_seconds,
                    metric.pending_transactions, metric.node_status
                ])
        
        # Generate summary report
        report_file = os.path.join(output_dir, f"stress_test_report_{timestamp}.txt")
        with open(report_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("IoT BLOCKCHAIN STRESS TEST REPORT\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Test Name: {result.test_name}\n")
            f.write(f"Start Time: {result.start_time}\n")
            f.write(f"End Time: {result.end_time}\n")
            f.write(f"Duration: {result.duration_seconds:.2f} seconds\n\n")
            
            f.write("TRANSACTION RESULTS:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total Transactions: {result.total_transactions}\n")
            f.write(f"Successful: {result.successful_transactions}\n")
            f.write(f"Failed: {result.failed_transactions}\n")
            f.write(f"Success Rate: {(result.successful_transactions/result.total_transactions*100):.2f}%\n\n")
            
            f.write("RESPONSE TIME ANALYSIS:\n")
            f.write("-" * 40 + "\n")
            f.write(f"Average Response Time: {result.avg_response_time:.4f} seconds\n")
            f.write(f"Minimum Response Time: {result.min_response_time:.4f} seconds\n")
            f.write(f"Maximum Response Time: {result.max_response_time:.4f} seconds\n\n")
            
            if result.system_metrics:
                f.write("SYSTEM PERFORMANCE:\n")
                f.write("-" * 40 + "\n")
                cpu_values = [m.cpu_percent for m in result.system_metrics]
                memory_values = [m.memory_percent for m in result.system_metrics]
                temp_values = [m.temperature_celsius for m in result.system_metrics if m.temperature_celsius]
                
                f.write(f"Average CPU Usage: {statistics.mean(cpu_values):.2f}%\n")
                f.write(f"Peak CPU Usage: {max(cpu_values):.2f}%\n")
                f.write(f"Average Memory Usage: {statistics.mean(memory_values):.2f}%\n")
                f.write(f"Peak Memory Usage: {max(memory_values):.2f}%\n")
                
                if temp_values:
                    f.write(f"Average Temperature: {statistics.mean(temp_values):.2f}°C\n")
                    f.write(f"Peak Temperature: {max(temp_values):.2f}°C\n")
                f.write("\n")
            
            if result.performance_degradation:
                f.write("PERFORMANCE DEGRADATION:\n")
                f.write("-" * 40 + "\n")
                for period, degradation in result.performance_degradation.items():
                    f.write(f"{period}: {degradation:+.2f}%\n")
                f.write("\n")
            
            f.write("RECOMMENDATIONS:\n")
            f.write("-" * 40 + "\n")
            
            if result.avg_response_time > 5.0:
                f.write("- High response times detected. Consider optimizing transaction processing.\n")
            
            if result.failed_transactions > result.total_transactions * 0.1:
                f.write("- High failure rate detected. Check network stability and node capacity.\n")
            
            if result.system_metrics:
                avg_cpu = statistics.mean([m.cpu_percent for m in result.system_metrics])
                if avg_cpu > 80:
                    f.write("- High CPU usage detected. Consider reducing transaction load or optimizing processing.\n")
                
                temp_values = [m.temperature_celsius for m in result.system_metrics if m.temperature_celsius]
                if temp_values and max(temp_values) > 70:
                    f.write("- High temperature detected. Consider improving cooling or reducing load.\n")
        
        logger.info(f"Report generated: {report_file}")
        return report_file

def create_default_config() -> Tuple[List[NodeConfig], TestConfig]:
    """Create default configuration for testing."""
    nodes = [
        NodeConfig("node1", "192.168.2.101", 8001),
        NodeConfig("node2", "192.168.2.102", 8002),
        NodeConfig("node3", "192.168.2.103", 8003),
        NodeConfig("node4", "192.168.2.104", 8004),
        NodeConfig("node5", "192.168.2.105", 8005),
        NodeConfig("node6", "192.168.2.106", 8006),
    ]
    
    config = TestConfig(
        duration_minutes=30,
        transaction_rate_per_second=10,
        concurrent_requests=5,
        warmup_seconds=60,
        cooldown_seconds=30,
        metrics_interval_seconds=5,
        enable_cpu_profiling=True,
        enable_heat_monitoring=True,
        enable_energy_monitoring=True,
        enable_performance_analysis=True
    )
    
    return nodes, config

def main():
    """Main entry point for the stress test."""
    parser = argparse.ArgumentParser(description="IoT Blockchain Stress Test Suite")
    parser.add_argument("--config", help="Path to configuration JSON file")
    parser.add_argument("--duration", type=int, help="Test duration in minutes")
    parser.add_argument("--tx-rate", type=int, help="Transactions per second")
    parser.add_argument("--concurrent", type=int, help="Concurrent requests per node")
    parser.add_argument("--nodes", nargs="+", help="Node addresses (host:port)")
    parser.add_argument("--output-dir", default="stress_test_results", help="Output directory for results")
    parser.add_argument("--test-name", default="IoT_Blockchain_Stress_Test", help="Name of the test")
    
    args = parser.parse_args()
    
    # Load configuration
    if args.config and os.path.exists(args.config):
        with open(args.config, 'r') as f:
            config_data = json.load(f)
            nodes = [NodeConfig(**node_data) for node_data in config_data.get('nodes', [])]
            config = TestConfig(**config_data.get('config', {}))
    else:
        nodes, config = create_default_config()
    
    # Override with command line arguments
    if args.duration:
        config.duration_minutes = args.duration
    if args.tx_rate:
        config.transaction_rate_per_second = args.tx_rate
    if args.concurrent:
        config.concurrent_requests = args.concurrent
    if args.nodes:
        nodes = []
        for i, node_addr in enumerate(args.nodes):
            host, port = node_addr.split(':')
            nodes.append(NodeConfig(f"node{i+1}", host, int(port)))
    
    logger.info(f"Starting stress test with {len(nodes)} nodes")
    logger.info(f"Configuration: {asdict(config)}")
    
    async def run_test():
        async with IoTStressTester(nodes, config) as tester:
            result = await tester.run_stress_test(args.test_name)
            tester.generate_report(result, args.output_dir)
            
            # Print summary
            print("\n" + "=" * 60)
            print("STRESS TEST COMPLETED")
            print("=" * 60)
            print(f"Duration: {result.duration_seconds:.2f} seconds")
            print(f"Total Transactions: {result.total_transactions}")
            print(f"Success Rate: {(result.successful_transactions/result.total_transactions*100):.2f}%")
            print(f"Average Response Time: {result.avg_response_time:.4f} seconds")
            print(f"Results saved to: {args.output_dir}")
            print("=" * 60)
    
    asyncio.run(run_test())

if __name__ == "__main__":
    main()
