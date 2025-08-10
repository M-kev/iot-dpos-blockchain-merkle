# IoT Blockchain Stress Test Suite

A comprehensive stress testing framework for IoT blockchain nodes that can be used with any blockchain implementation.

## Features

✅ **CPU Usage Profiling** - Real-time CPU monitoring and analysis
✅ **Heat Production Monitoring** - Temperature tracking for IoT devices (Raspberry Pi)
✅ **Energy Consumption Tracking** - Power usage monitoring (hardware-dependent)
✅ **Performance Degradation Analysis** - Response time analysis over time
✅ **Configurable Transaction Generation** - Customizable load patterns
✅ **Real-time Metrics Collection** - Continuous system and blockchain monitoring
✅ **Comprehensive Reporting** - Detailed CSV and text reports

## Requirements

- Python 3.7+
- Network access to blockchain nodes
- Root/sudo access for temperature monitoring (Raspberry Pi)

## Installation

1. Install dependencies:
```bash
pip install -r stress_test_requirements.txt
```

2. Make the script executable:
```bash
chmod +x stress_test.py
```

## Usage

### Basic Usage

Run with default configuration (6 nodes, 30 minutes, 10 TPS):
```bash
python stress_test.py
```

### Custom Configuration

#### Using Configuration File
```bash
python stress_test.py --config stress_test_config.json
```

#### Command Line Options
```bash
python stress_test.py \
  --duration 60 \
  --tx-rate 20 \
  --concurrent 10 \
  --nodes 192.168.2.101:8001 192.168.2.102:8002 \
  --output-dir my_results \
  --test-name "High_Load_Test"
```

### Parameters

- `--config`: Path to JSON configuration file
- `--duration`: Test duration in minutes (default: 30)
- `--tx-rate`: Transactions per second (default: 10)
- `--concurrent`: Concurrent requests per node (default: 5)
- `--nodes`: List of node addresses (host:port)
- `--output-dir`: Output directory for results (default: stress_test_results)
- `--test-name`: Name of the test (default: IoT_Blockchain_Stress_Test)

## Configuration File Format

```json
{
  "nodes": [
    {
      "name": "node1",
      "host": "192.168.2.101",
      "port": 8001,
      "api_base": "/api"
    }
  ],
  "config": {
    "duration_minutes": 30,
    "transaction_rate_per_second": 10,
    "concurrent_requests": 5,
    "warmup_seconds": 60,
    "cooldown_seconds": 30,
    "metrics_interval_seconds": 5,
    "enable_cpu_profiling": true,
    "enable_heat_monitoring": true,
    "enable_energy_monitoring": true,
    "enable_performance_analysis": true
  }
}
```

## Test Phases

1. **Warmup Period** (60 seconds default)
   - System stabilization
   - Initial metrics collection

2. **Main Test Period** (configurable duration)
   - Continuous transaction generation
   - Real-time metrics collection
   - Performance monitoring

3. **Cooldown Period** (30 seconds default)
   - System recovery
   - Final metrics collection

## Metrics Collected

### System Metrics
- CPU usage percentage
- Memory usage and consumption
- Temperature (Raspberry Pi)
- Power consumption (if available)
- Network I/O statistics
- Disk I/O statistics

### Blockchain Metrics
- Chain length
- Latest block hash
- Transactions per second
- Block time
- Pending transactions
- Node status

### Performance Metrics
- Response times
- Success/failure rates
- Performance degradation analysis
- Throughput analysis

## Output Files

The test generates several output files in the specified directory:

### CSV Files
- `system_metrics_TIMESTAMP.csv` - Raw system metrics
- `blockchain_metrics_TIMESTAMP.csv` - Raw blockchain metrics

### Report Files
- `stress_test_report_TIMESTAMP.txt` - Comprehensive text report

### Log Files
- `stress_test.log` - Detailed execution log

## Example Reports

### System Performance Summary
```
SYSTEM PERFORMANCE:
----------------------------------------
Average CPU Usage: 45.23%
Peak CPU Usage: 89.67%
Average Memory Usage: 67.89%
Peak Memory Usage: 82.34%
Average Temperature: 52.45°C
Peak Temperature: 68.12°C
```

### Transaction Results
```
TRANSACTION RESULTS:
----------------------------------------
Total Transactions: 18000
Successful: 17850
Failed: 150
Success Rate: 99.17%
```

### Performance Degradation
```
PERFORMANCE DEGRADATION:
----------------------------------------
q0_to_q1: +12.34%
q1_to_q2: +8.76%
q2_to_q3: +15.23%
```

## Customization for Different Blockchains

### Ethereum-based Blockchains
```json
{
  "nodes": [
    {
      "name": "geth_node",
      "host": "192.168.2.101",
      "port": 8545,
      "api_base": ""
    }
  ]
}
```

### Hyperledger Fabric
```json
{
  "nodes": [
    {
      "name": "peer1",
      "host": "192.168.2.101",
      "port": 7051,
      "api_base": "/api/v1"
    }
  ]
}
```

### Custom Blockchain APIs
Modify the `send_test_transaction` method in `IoTStressTester` class to match your blockchain's API endpoints.

## Troubleshooting

### Temperature Monitoring Issues
- Ensure running with sudo/root access
- Check if `/sys/class/thermal/thermal_zone0/temp` exists
- Verify `vcgencmd` is available (Raspberry Pi)

### Power Monitoring Issues
- Hardware-specific implementation required
- Check power supply file paths
- May require additional hardware sensors

### Network Connectivity Issues
- Verify node addresses and ports
- Check firewall settings
- Ensure blockchain nodes are running

### High Resource Usage
- Reduce transaction rate
- Decrease concurrent requests
- Increase metrics interval
- Monitor system resources during test

## Advanced Usage

### Long-term Testing
```bash
python stress_test.py --duration 480 --tx-rate 5 --concurrent 3
```

### High-load Testing
```bash
python stress_test.py --duration 60 --tx-rate 50 --concurrent 20
```

### Network Simulation
```bash
# Run multiple instances on different machines
python stress_test.py --nodes 192.168.2.101:8001 --duration 120
```

### Custom Transaction Types
Modify the transaction payload in the `send_test_transaction` method:

```python
transaction = {
    "from": "0x123...",
    "to": "0x456...",
    "value": "1000000000000000000",
    "gas": "21000",
    "gasPrice": "20000000000"
}
```

## Integration with CI/CD

Add to your CI/CD pipeline:

```yaml
- name: Run Stress Test
  run: |
    python scripts/stress_test.py \
      --duration 10 \
      --tx-rate 5 \
      --output-dir test_results
    
- name: Check Results
  run: |
    if grep -q "Success Rate: 95" test_results/*.txt; then
      echo "Stress test passed"
    else
      echo "Stress test failed"
      exit 1
    fi
```

## Contributing

To extend the stress test for your specific blockchain:

1. Modify `NodeConfig` for your API structure
2. Update `send_test_transaction` for your endpoints
3. Customize `get_blockchain_metrics` for your metrics
4. Add blockchain-specific analysis in `generate_report`

## License

This stress test suite is part of the IoT DPoS Blockchain project and follows the same license terms.
