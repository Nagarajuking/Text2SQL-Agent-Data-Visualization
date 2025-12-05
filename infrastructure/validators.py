# infrastructure/validators.py
"""
Input and output validation for Text-to-SQL system.

This module provides:
- User input sanitization and validation
- SQL query result validation
- Security checks for prompt injection
- Data type validation

Production-grade features:
- Comprehensive input validation
- Clear error messages
- Logging of suspicious inputs
- Configurable limits
"""

import re
from typing import Tuple, List, Dict, Any

class InputValidator:
    """Validates and sanitizes user input."""
    
    MAX_QUESTION_LENGTH = 500
    MIN_QUESTION_LENGTH = 3
    
    # Patterns that might indicate prompt injection
    SUSPICIOUS_PATTERNS = [
        r"ignore\s+(previous|above|all)",
        r"system\s*:",
        r"assistant\s*:",
        r"<\|.*?\|>",  # Special tokens
        r"###\s*instruction",
        r"forget\s+everything",
        r"disregard",
    ]
    
    def validate_question(self, question: str) -> Tuple[bool, str, str]:
        """
        Validate and sanitize user question.
        
        Args:
            question: User's natural language question
        
        Returns:
            Tuple of (is_valid, sanitized_question, error_message)
            - is_valid: True if question passes validation
            - sanitized_question: Cleaned version of question
            - error_message: Error description if validation fails
        """
        # Check if empty
        if not question or not question.strip():
            return False, "", "Question cannot be empty"
        
        # Sanitize
        sanitized = question.strip()
        
        # Check length
        if len(sanitized) < self.MIN_QUESTION_LENGTH:
            return False, "", f"Question too short (minimum {self.MIN_QUESTION_LENGTH} characters)"
        
        if len(sanitized) > self.MAX_QUESTION_LENGTH:
            return False, "", f"Question too long (maximum {self.MAX_QUESTION_LENGTH} characters)"
        
        # Check for suspicious patterns (prompt injection attempts)
        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, sanitized, re.IGNORECASE):
                return False, "", "Question contains invalid patterns. Please rephrase your question."
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        return True, sanitized, ""


class QueryResultValidator:
    """Validates SQL query results before visualization."""
    
    MAX_ROWS = 1000
    MAX_COLUMNS = 50
    
    def validate_results(self, results: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Validate query results before visualization.
        
        Args:
            results: List of result rows (each row is a dict)
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not results:
            return True, ""
        
        # Check row count
        if len(results) > self.MAX_ROWS:
            return False, f"Result set too large: {len(results)} rows (maximum {self.MAX_ROWS})"
        
        # Check column count
        first_row = results[0]
        if len(first_row) > self.MAX_COLUMNS:
            return False, f"Too many columns: {len(first_row)} (maximum {self.MAX_COLUMNS})"
        
        # Validate data types (sample first 10 rows)
        for i, row in enumerate(results[:10]):
            for key, value in row.items():
                if not isinstance(value, (str, int, float, bool, type(None))):
                    return False, f"Invalid data type in column '{key}': {type(value).__name__}"
        
        return True, ""
