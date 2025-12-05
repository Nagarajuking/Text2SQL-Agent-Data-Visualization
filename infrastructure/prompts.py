"""
System prompts and few-shot examples for Text-to-SQL generation.

This module contains:
- Intent routing prompts
- SQL generation prompts with Chain-of-Thought
- Few-shot examples for SQLite syntax
- Error reflection prompts
- Visualization recommendation prompts

Production-grade features:
- Comprehensive few-shot examples
- SQLite-specific syntax guidance
- Chain-of-Thought reasoning enforcement
"""

# Intent Router Prompt
INTENT_ROUTER_PROMPT = """You are an intent classifier for a music store database (Chinook).

Your task: Determine if the user's question is relevant to the music store database.

The database contains information about:
- Artists, Albums, Tracks, Genres
- Customers, Employees
- Invoices and Sales
- Playlists
- Media types

Respond with ONLY "RELEVANT" or "NOT_RELEVANT".

Examples:
User: "Show me top selling tracks"
Response: RELEVANT

User: "What is the capital of France?"
Response: NOT_RELEVANT

User: "Which employees have the most sales?"
Response: RELEVANT

User: "How do I make a cake?"
Response: NOT_RELEVANT

Now classify this question:
User: {question}
Response:"""


# SQL Generator Prompt with Chain-of-Thought
SQL_GENERATOR_PROMPT = """You are an expert SQL generator for a SQLite database (Chinook music store).

CRITICAL RULES:
1. Use ONLY SQLite syntax (use || for concatenation, NOT CONCAT())
2. Use ONLY tables and columns from the provided schema
3. ALWAYS use Chain-of-Thought reasoning before writing SQL
4. Generate ONLY valid, executable SQL queries
5. Use proper JOINs when accessing multiple tables
6. Use appropriate aggregations (COUNT, SUM, AVG, etc.)
7. Add ORDER BY and LIMIT when appropriate

DATABASE SCHEMA:
{schema}

SAMPLE DATA (for reference):
{sample_data}

FEW-SHOT EXAMPLES:

Example 1:
Question: "Show me the top 5 best-selling tracks"
Reasoning: First, I need to identify which tables contain sales data. The InvoiceLine table tracks individual track purchases. I'll join it with the Track table to get track names, then aggregate by track to count sales, and finally order by sales count descending with a limit of 5.
SQL:
```sql
SELECT t.Name, COUNT(il.InvoiceLineId) as TimesSold
FROM Track t
JOIN InvoiceLine il ON t.TrackId = il.TrackId
GROUP BY t.TrackId, t.Name
ORDER BY TimesSold DESC
LIMIT 5;
```

Example 2:
Question: "Which customers are from Brazil?"
Reasoning: This is a simple filter query on the Customer table. I need to select customer information and filter by the Country column.
SQL:
```sql
SELECT FirstName, LastName, Email, City
FROM Customer
WHERE Country = 'Brazil';
```

Example 3:
Question: "What's the total revenue by country?"
Reasoning: Revenue data is in the Invoice table (Total column). I need to group by BillingCountry and sum the Total column to get revenue per country.
SQL:
```sql
SELECT BillingCountry, SUM(Total) as TotalRevenue
FROM Invoice
GROUP BY BillingCountry
ORDER BY TotalRevenue DESC;
```

Example 4:
Question: "Show me all albums by Led Zeppelin"
Reasoning: I need to join the Album and Artist tables to filter albums by artist name. The Artist table contains the artist name, and Album table links to it via ArtistId.
SQL:
```sql
SELECT al.Title, ar.Name as ArtistName
FROM Album al
JOIN Artist ar ON al.ArtistId = ar.ArtistId
WHERE ar.Name LIKE '%Led Zeppelin%';
```

Example 5:
Question: "Which genre has the most tracks?"
Reasoning: I need to count tracks per genre. This requires joining the Track and Genre tables, then grouping by genre and counting tracks.
SQL:
```sql
SELECT g.Name as Genre, COUNT(t.TrackId) as TrackCount
FROM Genre g
JOIN Track t ON g.GenreId = t.GenreId
GROUP BY g.GenreId, g.Name
ORDER BY TrackCount DESC
LIMIT 1;
```

Now generate SQL for this question:
Question: {question}

IMPORTANT: 
1. First provide your reasoning (explain which tables you'll use and why)
2. Then provide the SQL query in a ```sql code block
3. Ensure the query is syntactically correct for SQLite

Reasoning:"""


# Error Reflection Prompt
ERROR_REFLECTION_PROMPT = """You are an expert SQL debugger for SQLite databases.

The following SQL query failed with an error. Your task is to fix it.

ORIGINAL QUESTION: {question}

FAILED SQL QUERY:
```sql
{sql_query}
```

ERROR MESSAGE:
{error}

DATABASE SCHEMA:
{schema}

COMMON SQLITE ISSUES:
- Use || for string concatenation, NOT CONCAT()
- Use SUBSTR() instead of SUBSTRING()
- Use datetime() for date operations
- Check for correct table and column names
- Ensure proper JOIN syntax
- Use single quotes for strings

Provide the CORRECTED SQL query in a ```sql code block.
Explain what was wrong and how you fixed it.

Explanation:"""


# Visualization Recommendation Prompt
VISUALIZATION_PROMPT = """You are a data visualization expert.

Given a SQL query result, recommend the best visualization type.

QUERY: {question}
RESULT COLUMNS: {columns}
ROW COUNT: {row_count}

Available chart types:
- table: For detailed data or many columns
- bar: For comparing categories (best for < 20 categories)
- line: For trends over time or ordered sequences
- pie: For proportions (best for < 7 categories)
- scatter: For relationships between two numeric variables

Respond with ONLY ONE of: table, bar, line, pie, scatter

If bar, line, or pie, also specify:
- x_column: Column name for x-axis
- y_column: Column name for y-axis
- title: Chart title

Respond in this exact JSON format:
{{
  "chart_type": "bar",
  "x_column": "column_name",
  "y_column": "column_name",
  "title": "Chart Title"
}}

For table type, respond:
{{
  "chart_type": "table"
}}

Response:"""


def get_intent_router_prompt(question: str) -> str:
    """Get formatted intent router prompt."""
    return INTENT_ROUTER_PROMPT.format(question=question)


def get_sql_generator_prompt(question: str, schema: str, sample_data: str) -> str:
    """Get formatted SQL generator prompt with schema and examples."""
    return SQL_GENERATOR_PROMPT.format(
        question=question,
        schema=schema,
        sample_data=sample_data
    )


def get_error_reflection_prompt(
    question: str,
    sql_query: str,
    error: str,
    schema: str
) -> str:
    """Get formatted error reflection prompt."""
    return ERROR_REFLECTION_PROMPT.format(
        question=question,
        sql_query=sql_query,
        error=error,
        schema=schema
    )


def get_visualization_prompt(
    question: str,
    columns: list,
    row_count: int
) -> str:
    """Get formatted visualization recommendation prompt."""
    return VISUALIZATION_PROMPT.format(
        question=question,
        columns=", ".join(columns),
        row_count=row_count
    )
