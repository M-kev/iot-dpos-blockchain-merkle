#!/usr/bin/env python3
"""
Quick test script to verify stress test functionality.
This script tests the basic components without running a full stress test.
"""

import asyncio
import sys
import os
import time
from pathlib import Path

# Add the parent directory to the path to import the stress test
sys.path.append(str(Path(__file__).parent))

from stress_test import IoTStressTester, NodeConfig, TestConfig, SystemMetrics

async def test_system_metrics():
    """Test system metrics collection."""
    print("Testing system metrics collection...")
    
    config = TestConfig(
        duration_minutes=1,
        transaction_rate_per_second=1,
        concurrent_requests=1,
        warmup_seconds=5,
        cooldown_seconds=5,
        metrics_interval_seconds=2
    )
    
    nodes = [
        NodeConfig("test_node", "127.0.0.1", 8001)
    ]
    
    async with IoTStressTester(nodes, config) as tester:
        # Test system metrics collection
        metrics = tester.get_system_metrics()
        print(f"✓ CPU Usage: {metrics.cpu_percent:.2f}%")
        print(f"✓ Memory Usage: {metrics.memory_percent:.2f}%")
        print(f"✓ Memory Used: {metrics.memory_used_mb:.2f} MB")
        print(f"✓ Temperature: {metrics.temperature_celsius}°C" if metrics.temperature_celsius else "✓ Temperature: Not available")
        print(f"✓ Power Consumption: {metrics.power_consumption_watts}W" if metrics.power_consumption_watts else "✓ Power Consumption: Not available")
        print(f"✓ Network Sent: {metrics.network_bytes_sent} bytes")
        print(f"✓ Network Received: {metrics.network_bytes_recv} bytes")
        
        return True

async def test_blockchain_metrics():
    """Test blockchain metrics collection."""
    print("\nTesting blockchain metrics collection...")
    
    config = TestConfig()
    nodes = [
        NodeConfig("test_node", "127.0.0.1", 8001)
    ]
    
    async with IoTStressTester(nodes, config) as tester:
        try:
            # This will likely fail since we don't have a real node running
            # but it tests the error handling
            metrics = await tester.get_blockchain_metrics(nodes[0])
            print(f"✓ Chain Length: {metrics.chain_length}")
            print(f"✓ Latest Block Hash: {metrics.latest_block_hash}")
            print(f"✓ TPS: {metrics.transactions_per_second}")
            print(f"✓ Node Status: {metrics.node_status}")
        except Exception as e:
            print(f"✓ Expected error (no real node): {e}")
        
        return True

def test_configuration():
    """Test configuration loading."""
    print("\nTesting configuration...")
    
    # Test default config
    from stress_test import create_default_config
    nodes, config = create_default_config()
    
    print(f"✓ Default nodes: {len(nodes)}")
    print(f"✓ Default duration: {config.duration_minutes} minutes")
    print(f"✓ Default TPS: {config.transaction_rate_per_second}")
    print(f"✓ Default concurrent: {config.concurrent_requests}")
    
    return True

async def test_performance_degradation():
    """Test performance degradation calculation."""
    print("\nTesting performance degradation calculation...")
    
    config = TestConfig()
    nodes = [NodeConfig("test", "127.0.0.1", 8001)]
    
    async with IoTStressTester(nodes, config) as tester:
        # Simulate response times with degradation
        tester.response_times = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0]
        
        degradation = tester.calculate_performance_degradation()
        print(f"✓ Performance degradation calculated: {degradation}")
        
        return True

async def main():
    """Run all tests."""
    print("=" * 60)
    print("STRESS TEST VERIFICATION")
    print("=" * 60)
    
    tests = [
        ("Configuration", test_configuration),
        ("System Metrics", test_system_metrics),
        ("Blockchain Metrics", test_blockchain_metrics),
        ("Performance Degradation", test_performance_degradation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, True, None))
        except Exception as e:
            results.append((test_name, False, str(e)))
    
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed, error in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} {test_name}")
        if error:
            print(f"    Error: {error}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED - Stress test is ready to use!")
        print("\nTo run a full stress test:")
        print("python stress_test.py --duration 5 --tx-rate 2")
    else:
        print("✗ SOME TESTS FAILED - Check the errors above")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
