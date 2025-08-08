import sqlite3
from typing import Any, Dict, List, Optional
import json
import os

# Assuming Block class is available in the consensus module
from consensus.block import Block

class SQLiteStorage:
    def __init__(self, db_path: str = "blockchain.db"):
        """Initialize SQLite storage with proper error handling."""
        try:
            # Ensure the database path is absolute
            self.db_path = os.path.abspath(db_path)
            
            # Create directory if it doesn't exist
            db_dir = os.path.dirname(self.db_path)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                print(f"[STORAGE] Created database directory: {db_dir}")
            
            # Initialize database and ensure tables exist
            self._ensure_database()
            
        except Exception as e:
            print(f"[STORAGE] Error initializing storage: {e}")
            raise

    def _ensure_database(self):
        """Ensure database and tables exist."""
        try:
            # Connect to database (creates it if it doesn't exist)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create blocks table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS blocks (
                    block_index INTEGER PRIMARY KEY,
                    timestamp REAL,
                    validator TEXT,
                    previous_hash TEXT,
                    hash TEXT,
                    transactions TEXT,
                    energy_metrics TEXT,
                    merkle_root TEXT
                )
            ''')
            
            # Per-block analytics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS block_metrics (
                    block_index INTEGER PRIMARY KEY,
                    created_timestamp REAL,
                    block_interval REAL,
                    consensus_time REAL,
                    power_usage REAL,
                    FOREIGN KEY(block_index) REFERENCES blocks(block_index) ON DELETE CASCADE
                )
            ''')

            # Create transactions table for better querying
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    tx_hash TEXT PRIMARY KEY,
                    block_index INTEGER,
                    tx_type TEXT,
                    sender TEXT,
                    recipient TEXT,
                    amount REAL,
                    timestamp REAL,
                    tx_data TEXT,  -- JSON string for additional transaction data
                    FOREIGN KEY(block_index) REFERENCES blocks(block_index) ON DELETE CASCADE
                )
            ''')

            # Transaction lifecycle table to capture received and inclusion times
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transaction_lifecycle (
                    tx_hash TEXT PRIMARY KEY,
                    received_timestamp REAL,
                    included_timestamp REAL,
                    block_index INTEGER,
                    FOREIGN KEY(block_index) REFERENCES blocks(block_index) ON DELETE SET NULL
                )
            ''')
            
            # Create indexes for better query performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_sender ON transactions(sender)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_recipient ON transactions(recipient)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_block ON transactions(block_index)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_block_metrics_created ON block_metrics(created_timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tx_lifecycle_block ON transaction_lifecycle(block_index)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tx_lifecycle_received ON transaction_lifecycle(received_timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tx_lifecycle_included ON transaction_lifecycle(included_timestamp)')
            
            conn.commit()
            conn.close()
            print(f"[STORAGE] Database and tables verified at {self.db_path}")
        except Exception as e:
            print(f"[STORAGE] Error ensuring database: {e}")
            raise

    def _get_connection(self):
        """Get a database connection with proper error handling."""
        try:
            conn = sqlite3.connect(self.db_path)
            return conn
        except Exception as e:
            print(f"[STORAGE] Error connecting to database: {e}")
            # Try to recreate database if connection fails
            self._ensure_database()
            return sqlite3.connect(self.db_path)

    def save_block(self, block: Block):
        """Save a block to the database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Convert transactions and energy_metrics to JSON strings
            transactions_json = json.dumps(block.transactions)
            energy_metrics_json = json.dumps(block.energy_metrics)
            
            cursor.execute('''
                INSERT OR REPLACE INTO blocks 
                (block_index, timestamp, validator, previous_hash, hash, transactions, energy_metrics, merkle_root)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                block.block_index,
                block.timestamp,
                block.validator,
                block.previous_hash,
                block.hash,
                transactions_json,
                energy_metrics_json,
                block.merkle_root
            ))
            
            # Save individual transactions to the transactions table
            self._save_transactions(cursor, block.block_index, block.transactions, block.timestamp)
            
            conn.commit()
            conn.close()
            print(f"[STORAGE] Block {block.block_index} saved to database")
        except Exception as e:
            print(f"[STORAGE] Error saving block: {e}")
            raise

    def _save_transactions(self, cursor, block_index: int, transactions: List[Dict[str, Any]], block_timestamp: float):
        """Save individual transactions to the transactions table."""
        import hashlib
        
        for tx in transactions:
            # Generate transaction hash
            tx_string = json.dumps(tx, sort_keys=True)
            tx_hash = hashlib.sha256(tx_string.encode()).hexdigest()
            
            # Extract transaction fields based on type
            tx_type = tx.get('type', 'transfer')
            sender = tx.get('sender', '')
            recipient = tx.get('recipient', '')
            amount = tx.get('amount', 0.0)
            timestamp = tx.get('timestamp', block_timestamp)
            
            # Store additional transaction data as JSON
            tx_data = json.dumps(tx)
            
            cursor.execute('''
                INSERT OR REPLACE INTO transactions 
                (tx_hash, block_index, tx_type, sender, recipient, amount, timestamp, tx_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (tx_hash, block_index, tx_type, sender, recipient, amount, timestamp, tx_data))

            # Mark lifecycle inclusion and ensure received_timestamp is populated
            cursor.execute('''
                INSERT INTO transaction_lifecycle (tx_hash, received_timestamp, included_timestamp, block_index)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(tx_hash) DO UPDATE SET 
                    included_timestamp=excluded.included_timestamp,
                    block_index=excluded.block_index,
                    received_timestamp=COALESCE(transaction_lifecycle.received_timestamp, excluded.received_timestamp, excluded.included_timestamp)
            ''', (tx_hash, timestamp, block_timestamp, block_index))

    def save_block_metrics(self, block_index: int, created_timestamp: float, block_interval: float, consensus_time: float, power_usage: float) -> None:
        """Persist per-block analytics to the block_metrics table."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO block_metrics (block_index, created_timestamp, block_interval, consensus_time, power_usage)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(block_index) DO UPDATE SET
                    created_timestamp=excluded.created_timestamp,
                    block_interval=excluded.block_interval,
                    consensus_time=excluded.consensus_time,
                    power_usage=excluded.power_usage
            ''', (block_index, created_timestamp, block_interval, consensus_time, power_usage))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[STORAGE] Error saving block metrics: {e}")
            raise

    def record_tx_received(self, tx_hash: str, received_timestamp: float) -> None:
        """Record when a transaction was first seen by this node."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO transaction_lifecycle (tx_hash, received_timestamp)
                VALUES (?, ?)
                ON CONFLICT(tx_hash) DO UPDATE SET received_timestamp=MIN(COALESCE(transaction_lifecycle.received_timestamp, excluded.received_timestamp), excluded.received_timestamp)
            ''', (tx_hash, received_timestamp))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[STORAGE] Error recording tx received: {e}")
            raise

    def get_cumulative_energy_usage(self) -> float:
        """Return sum of power_usage over all blocks from block_metrics."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT COALESCE(SUM(power_usage), 0) FROM block_metrics')
            total = cursor.fetchone()[0] or 0.0
            conn.close()
            return float(total)
        except Exception as e:
            print(f"[STORAGE] Error computing cumulative energy: {e}")
            return 0.0

    def export_block_metrics(self) -> List[Dict[str, Any]]:
        """Fetch all block metrics for offline analysis."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT block_index, created_timestamp, block_interval, consensus_time, power_usage FROM block_metrics ORDER BY block_index ASC')
            rows = cursor.fetchall()
            conn.close()
            return [
                {
                    'block_index': r[0],
                    'created_timestamp': r[1],
                    'block_interval': r[2],
                    'consensus_time': r[3],
                    'power_usage': r[4],
                } for r in rows
            ]
        except Exception as e:
            print(f"[STORAGE] Error exporting block metrics: {e}")
            return []

    def export_transaction_lifecycle(self) -> List[Dict[str, Any]]:
        """Fetch transaction lifecycle data for offline analysis."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT tx_hash, received_timestamp, included_timestamp, block_index FROM transaction_lifecycle ORDER BY COALESCE(included_timestamp, received_timestamp) ASC')
            rows = cursor.fetchall()
            conn.close()
            return [
                {
                    'tx_hash': r[0],
                    'received_timestamp': r[1],
                    'included_timestamp': r[2],
                    'block_index': r[3]
                } for r in rows
            ]
        except Exception as e:
            print(f"[STORAGE] Error exporting transaction lifecycle: {e}")
            return []

    def get_block(self, block_index: int) -> Optional[Block]:
        """Retrieve a block by its block_index."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM blocks WHERE block_index = ?', (block_index,))
            row = cursor.fetchone()
            
            if row:
                # Convert JSON strings back to Python objects
                transactions = json.loads(row[5])
                energy_metrics = json.loads(row[6])
                
                block = Block(
                    block_index=row[0],
                    timestamp=row[1],
                    validator=row[2],
                    previous_hash=row[3],
                    transactions=transactions,
                    energy_metrics=energy_metrics,
                    merkle_root=row[7] if len(row) > 7 else None
                )
                conn.close()
                return block
            conn.close()
            return None
        except Exception as e:
            print(f"[STORAGE] Error retrieving block: {e}")
            raise

    def get_chain_length(self) -> int:
        """Get the current length of the blockchain."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM blocks')
            length = cursor.fetchone()[0]
            
            conn.close()
            return length
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                print("[STORAGE] Blocks table not found, creating...")
                self._ensure_database()
                return 0
            print(f"[STORAGE] Error getting chain length: {e}")
            return 0
        except Exception as e:
            print(f"[STORAGE] Error getting chain length: {e}")
            return 0

    def get_latest_block(self) -> Optional[Block]:
        """Get the latest block in the chain."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM blocks ORDER BY block_index DESC LIMIT 1')
            row = cursor.fetchone()
            
            if row:
                # Convert JSON strings back to Python objects
                transactions = json.loads(row[5])
                energy_metrics = json.loads(row[6])
                
                block = Block(
                    block_index=row[0],
                    timestamp=row[1],
                    validator=row[2],
                    previous_hash=row[3],
                    transactions=transactions,
                    energy_metrics=energy_metrics,
                    merkle_root=row[7] if len(row) > 7 else None
                )
                conn.close()
                return block
            conn.close()
            return None
        except Exception as e:
            print(f"[STORAGE] Error retrieving latest block: {e}")
            raise

    def get_blocks(self, start_index: int = 0, end_index: int = -1) -> List[Block]:
        """Retrieve a range of blocks from storage."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            if end_index == -1:
                cursor.execute('SELECT * FROM blocks WHERE block_index >= ? ORDER BY block_index ASC', (start_index,))
            else:
                cursor.execute('SELECT * FROM blocks WHERE block_index >= ? AND block_index <= ? ORDER BY block_index ASC', (start_index, end_index))
            rows = cursor.fetchall()
            blocks = []
            for row in rows:
                transactions = json.loads(row[5])
                energy_metrics = json.loads(row[6])
                block = Block(
                    block_index=row[0],
                    timestamp=row[1],
                    validator=row[2],
                    previous_hash=row[3],
                    transactions=transactions,
                    energy_metrics=energy_metrics,
                    merkle_root=row[7] if len(row) > 7 else None
                )
                blocks.append(block)
            conn.close()
            return blocks
        except Exception as e:
            print(f"[STORAGE] Error retrieving blocks: {e}")
            raise

    def save_state(self, key: str, value: Any):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('REPLACE INTO state (key, value) VALUES (?, ?)', (key, json.dumps(value)))
        conn.commit()
        conn.close()

    def get_state(self, key: str) -> Any:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT value FROM state WHERE key = ?', (key,))
        row = c.fetchone()
        conn.close()
        return json.loads(row[0]) if row else None

    def get_transactions_by_address(self, address: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all transactions involving a specific address (as sender or recipient)."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT tx_hash, block_index, tx_type, sender, recipient, amount, timestamp, tx_data
                FROM transactions 
                WHERE sender = ? OR recipient = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (address, address, limit))
            
            transactions = []
            for row in cursor.fetchall():
                transactions.append({
                    'tx_hash': row[0],
                    'block_index': row[1],
                    'tx_type': row[2],
                    'sender': row[3],
                    'recipient': row[4],
                    'amount': row[5],
                    'timestamp': row[6],
                    'tx_data': json.loads(row[7])
                })
            
            conn.close()
            return transactions
        except Exception as e:
            print(f"[STORAGE] Error retrieving transactions for address {address}: {e}")
            return []

    def get_transactions_by_block(self, block_index: int) -> List[Dict[str, Any]]:
        """Get all transactions in a specific block."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT tx_hash, block_index, tx_type, sender, recipient, amount, timestamp, tx_data
                FROM transactions 
                WHERE block_index = ?
                ORDER BY timestamp ASC
            ''', (block_index,))
            
            transactions = []
            for row in cursor.fetchall():
                transactions.append({
                    'tx_hash': row[0],
                    'block_index': row[1],
                    'tx_type': row[2],
                    'sender': row[3],
                    'recipient': row[4],
                    'amount': row[5],
                    'timestamp': row[6],
                    'tx_data': json.loads(row[7])
                })
            
            conn.close()
            return transactions
        except Exception as e:
            print(f"[STORAGE] Error retrieving transactions for block {block_index}: {e}")
            return []

    def get_transaction_by_hash(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get a specific transaction by its hash."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT tx_hash, block_index, tx_type, sender, recipient, amount, timestamp, tx_data
                FROM transactions 
                WHERE tx_hash = ?
            ''', (tx_hash,))
            
            row = cursor.fetchone()
            if row:
                transaction = {
                    'tx_hash': row[0],
                    'block_index': row[1],
                    'tx_type': row[2],
                    'sender': row[3],
                    'recipient': row[4],
                    'amount': row[5],
                    'timestamp': row[6],
                    'tx_data': json.loads(row[7])
                }
                conn.close()
                return transaction
            
            conn.close()
            return None
        except Exception as e:
            print(f"[STORAGE] Error retrieving transaction {tx_hash}: {e}")
            return None

    def get_transaction_stats(self) -> Dict[str, Any]:
        """Get transaction statistics."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Total transactions
            cursor.execute('SELECT COUNT(*) FROM transactions')
            total_transactions = cursor.fetchone()[0]
            
            # Total amount transferred
            cursor.execute('SELECT SUM(amount) FROM transactions WHERE tx_type = "transfer"')
            total_amount = cursor.fetchone()[0] or 0.0
            
            # Transactions by type
            cursor.execute('SELECT tx_type, COUNT(*) FROM transactions GROUP BY tx_type')
            transactions_by_type = dict(cursor.fetchall())
            
            # Unique addresses
            cursor.execute('''
                SELECT COUNT(DISTINCT address) FROM (
                    SELECT sender as address FROM transactions
                    UNION
                    SELECT recipient as address FROM transactions
                )
            ''')
            unique_addresses = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_transactions': total_transactions,
                'total_amount_transferred': total_amount,
                'transactions_by_type': transactions_by_type,
                'unique_addresses': unique_addresses
            }
        except Exception as e:
            print(f"[STORAGE] Error getting transaction stats: {e}")
            return {} 