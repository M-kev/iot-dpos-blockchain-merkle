#!/bin/bash

echo "🧹 Starting blockchain cleanup..."

# Stop the blockchain service if running
echo "📦 Stopping blockchain service..."
sudo systemctl stop blockchain-node 2>/dev/null || true

# Clean up database
echo "🗄️  Cleaning database..."
if [ -f "data/blockchain.db" ]; then
    rm data/blockchain.db
    echo "✅ Database removed"
else
    echo "ℹ️  Database file not found"
fi

# Clean up any backup databases
echo "🗄️  Cleaning backup databases..."
rm -f data/blockchain.db.* 2>/dev/null || true

# Clean up blockchain data directory
echo "📁 Cleaning blockchain data..."
rm -rf blockchain_data/* 2>/dev/null || true

# Clean up logs
echo "📝 Cleaning logs..."
sudo journalctl --vacuum-time=1s --unit=blockchain-node 2>/dev/null || true

# Clean up Python cache
echo "🐍 Cleaning Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Clean up any temporary files
echo "🗑️  Cleaning temporary files..."
rm -f *.tmp 2>/dev/null || true
rm -f *.log 2>/dev/null || true

# Reset Merkle tree performance data (if service is running)
echo "🌳 Resetting Merkle tree performance data..."
if curl -s "http://localhost:8001/api/merkle-performance" >/dev/null 2>&1; then
    echo "ℹ️  Merkle performance data will be reset on next service start"
else
    echo "ℹ️  Service not running, performance data will be reset on startup"
fi

# Create fresh database directory
echo "📁 Creating fresh database directory..."
mkdir -p data
chmod 777 data

# Create empty database file
touch data/blockchain.db
chmod 666 data/blockchain.db

echo "✅ Cleanup complete!"
echo ""
echo "🔄 To restart the blockchain:"
echo "   sudo systemctl start blockchain-node"
echo ""
echo "📊 To verify cleanup:"
echo "   curl http://localhost:8001/api/chain_info"
echo "   # Should show chain_length: 0" 