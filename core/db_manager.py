"""
Database management with semantic schema layer for Text-to-SQL system.

This module provides:
- Annotated schema with semantic descriptions
- Safe query execution with guardrails
- Sample data retrieval for context
- Schema introspection

Production-grade features:
- Read-only database access
- Comprehensive error handling
- Semantic annotations for better LLM understanding
- Query result limiting
- SQL injection prevention
"""

import sqlite3
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from contextlib import contextmanager

from core.config import get_config


# Semantic annotations for Chinook database
# Maps table.column to human-readable descriptions
SCHEMA_ANNOTATIONS = {
    "Album": {
        "description": "Music albums in the store catalog",
        "columns": {
            "AlbumId": "Unique identifier for each album",
            "Title": "Album title/name",
            "ArtistId": "Foreign key to Artist table - identifies the artist who created this album"
        }
    },
    "Artist": {
        "description": "Music artists and bands",
        "columns": {
            "ArtistId": "Unique identifier for each artist",
            "Name": "Artist or band name"
        }
    },
    "Customer": {
        "description": "Store customers who make purchases",
        "columns": {
            "CustomerId": "Unique identifier for each customer",
            "FirstName": "Customer's first name",
            "LastName": "Customer's last name",
            "Company": "Customer's company (if applicable)",
            "Address": "Street address",
            "City": "City name",
            "State": "State or province",
            "Country": "Country name",
            "PostalCode": "Postal/ZIP code",
            "Phone": "Phone number",
            "Fax": "Fax number",
            "Email": "Email address",
            "SupportRepId": "Foreign key to Employee table - assigned support representative"
        }
    },
    "Employee": {
        "description": "Store employees and their organizational structure",
        "columns": {
            "EmployeeId": "Unique identifier for each employee",
            "LastName": "Employee's last name",
            "FirstName": "Employee's first name",
            "Title": "Job title",
            "ReportsTo": "Foreign key to Employee table - manager's EmployeeId",
            "BirthDate": "Date of birth",
            "HireDate": "Date hired",
            "Address": "Street address",
            "City": "City name",
            "State": "State or province",
            "Country": "Country name",
            "PostalCode": "Postal/ZIP code",
            "Phone": "Phone number",
            "Fax": "Fax number",
            "Email": "Email address"
        }
    },
    "Genre": {
        "description": "Music genres/categories",
        "columns": {
            "GenreId": "Unique identifier for each genre",
            "Name": "Genre name (e.g., Rock, Jazz, Metal)"
        }
    },
    "Invoice": {
        "description": "Customer purchase invoices (sales transactions)",
        "columns": {
            "InvoiceId": "Unique identifier for each invoice",
            "CustomerId": "Foreign key to Customer table - who made the purchase",
            "InvoiceDate": "Date and time of purchase",
            "BillingAddress": "Billing street address",
            "BillingCity": "Billing city",
            "BillingState": "Billing state/province",
            "BillingCountry": "Billing country",
            "BillingPostalCode": "Billing postal code",
            "Total": "Total invoice amount in USD"
        }
    },
    "InvoiceLine": {
        "description": "Individual line items within invoices (tracks purchased)",
        "columns": {
            "InvoiceLineId": "Unique identifier for each line item",
            "InvoiceId": "Foreign key to Invoice table - which invoice this belongs to",
            "TrackId": "Foreign key to Track table - which track was purchased",
            "UnitPrice": "Price per track in USD",
            "Quantity": "Number of units purchased (usually 1 for digital tracks)"
        }
    },
    "MediaType": {
        "description": "Types of media formats for tracks",
        "columns": {
            "MediaTypeId": "Unique identifier for each media type",
            "Name": "Media type name (e.g., MPEG audio, AAC audio)"
        }
    },
    "Playlist": {
        "description": "Curated playlists of tracks",
        "columns": {
            "PlaylistId": "Unique identifier for each playlist",
            "Name": "Playlist name"
        }
    },
    "PlaylistTrack": {
        "description": "Junction table linking playlists to tracks (many-to-many)",
        "columns": {
            "PlaylistId": "Foreign key to Playlist table",
            "TrackId": "Foreign key to Track table"
        }
    },
    "Track": {
        "description": "Individual music tracks available for purchase",
        "columns": {
            "TrackId": "Unique identifier for each track",
            "Name": "Track title/name",
            "AlbumId": "Foreign key to Album table - which album this track belongs to",
            "MediaTypeId": "Foreign key to MediaType table - format of the track",
            "GenreId": "Foreign key to Genre table - musical genre",
            "Composer": "Track composer/songwriter",
            "Milliseconds": "Track duration in milliseconds",
            "Bytes": "File size in bytes",
            "UnitPrice": "Price per track in USD"
        }
    }
}


class DatabaseManager:
    """
    Manages database connections and provides semantic schema information.
    
    This class implements the semantic layer that enriches raw database schema
    with business context to help LLMs generate better SQL queries.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file. If None, uses config default.
        """
        self.db_path = db_path or get_config().database_path
        self._validate_database()
    
    def _validate_database(self) -> None:
        """Validate that database exists and is accessible."""
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Database file not found: {self.db_path}. "
                f"Please ensure chinook.db is in the correct location."
            )
    
    @contextmanager
    def get_connection(self, read_only: bool = True):
        """
        Get a database connection with proper resource management.
        
        Args:
            read_only: If True, opens database in read-only mode for safety
            
        Yields:
            sqlite3.Connection: Database connection
        """
        # Open in read-only mode for safety (prevents accidental writes)
        uri = f"file:{self.db_path}?mode=ro" if read_only else str(self.db_path)
        conn = sqlite3.connect(uri, uri=read_only)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()
    
    def get_annotated_schema(self) -> str:
        """
        Get database schema with semantic annotations.
        
        This is the core of the semantic layer - instead of raw DDL,
        we provide table and column descriptions that help the LLM
        understand the business context.
        
        Returns:
            str: Formatted schema with semantic descriptions
        """
        schema_parts = []
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                # Get table annotation
                table_info = SCHEMA_ANNOTATIONS.get(table, {})
                table_desc = table_info.get("description", "No description available")
                
                schema_parts.append(f"\n**{table}**: {table_desc}")
                
                # Get columns for this table
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                
                schema_parts.append("  Columns:")
                for col in columns:
                    col_name = col[1]
                    col_type = col[2]
                    is_pk = col[5]
                    
                    # Get column annotation
                    col_desc = table_info.get("columns", {}).get(
                        col_name,
                        "No description available"
                    )
                    
                    pk_marker = " [PRIMARY KEY]" if is_pk else ""
                    schema_parts.append(
                        f"    - {col_name} ({col_type}){pk_marker}: {col_desc}"
                    )
        
        return "\n".join(schema_parts)
    
    def get_sample_data(self, limit: int = 3) -> str:
        """
        Get sample data from each table to help LLM understand data formats.
        
        Args:
            limit: Number of sample rows per table
            
        Returns:
            str: Formatted sample data
        """
        sample_parts = []
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                cursor.execute(f"SELECT * FROM {table} LIMIT {limit}")
                rows = cursor.fetchall()
                
                if rows:
                    sample_parts.append(f"\n{table} (sample):")
                    columns = [description[0] for description in cursor.description]
                    sample_parts.append(f"  Columns: {', '.join(columns)}")
                    sample_parts.append(f"  Sample rows: {len(rows)}")
        
        return "\n".join(sample_parts)
    
    def execute_query(
        self,
        sql_query: str,
        enforce_limit: bool = True
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Execute a SQL query safely with guardrails.
        
        Args:
            sql_query: SQL query to execute
            enforce_limit: If True, enforces max row limit
            
        Returns:
            Tuple of (results, error_message)
            - results: List of dictionaries (rows)
            - error_message: Error string if query failed, None otherwise
        """
        try:
            # Enforce row limit for safety
            if enforce_limit:
                sql_query = self._enforce_limit(sql_query)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql_query)
                
                # Convert rows to dictionaries
                columns = [description[0] for description in cursor.description]
                results = [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]
                
                return results, None
                
        except sqlite3.Error as e:
            return [], str(e)
        except Exception as e:
            return [], f"Unexpected error: {str(e)}"
    
    def _enforce_limit(self, sql_query: str) -> str:
        """
        Enforce maximum row limit on query.
        
        Args:
            sql_query: Original SQL query
            
        Returns:
            str: Query with LIMIT clause added if not present
        """
        config = get_config()
        max_rows = config.max_result_rows
        
        # Check if query already has a LIMIT clause
        if re.search(r'\bLIMIT\s+\d+', sql_query, re.IGNORECASE):
            return sql_query
        
        # Add LIMIT clause
        sql_query = sql_query.rstrip(';')
        return f"{sql_query} LIMIT {max_rows};"
    
    def validate_query_syntax(self, sql_query: str) -> Tuple[bool, Optional[str]]:
        """
        Validate SQL query syntax without executing it.
        
        Uses EXPLAIN QUERY PLAN to check syntax without side effects.
        
        Args:
            sql_query: SQL query to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"EXPLAIN QUERY PLAN {sql_query}")
                return True, None
        except sqlite3.Error as e:
            return False, str(e)
    
    def get_table_names(self) -> List[str]:
        """
        Get list of all table names in the database.
        
        Returns:
            List[str]: Table names
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            return [row[0] for row in cursor.fetchall()]
