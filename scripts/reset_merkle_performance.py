#!/usr/bin/env python3
"""
Reset Merkle Tree Performance Monitor
This script resets all performance data stored in the Merkle performance monitor.
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def reset_merkle_performance():
    """Reset the Merkle tree performance monitor."""
    try:
        from utils.merkle_performance import merkle_performance_monitor
        
        print("🌳 Resetting Merkle tree performance monitor...")
        
        # Reset all performance data
        merkle_performance_monitor.reset_metrics()
        
        print("✅ Merkle performance data reset successfully!")
        
        # Show current state
        stats = merkle_performance_monitor.get_performance_stats()
        print(f"📊 Current stats: {len(stats)} operation types recorded")
        
        return True
        
    except ImportError as e:
        print(f"❌ Error importing Merkle performance monitor: {e}")
        return False
    except Exception as e:
        print(f"❌ Error resetting performance data: {e}")
        return False

def main():
    """Main function."""
    print("🧹 Merkle Tree Performance Reset Tool")
    print("=" * 40)
    
    success = reset_merkle_performance()
    
    if success:
        print("\n✅ Reset completed successfully!")
        print("🔄 Restart your blockchain node to see fresh performance data.")
    else:
        print("\n❌ Reset failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
