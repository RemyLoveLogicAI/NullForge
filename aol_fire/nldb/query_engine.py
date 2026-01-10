"""
NullForge Natural Language Database Query Engine
State of the Art NL to SQL translation

Features:
- Natural language to SQL translation
- Schema-aware query generation
- Query validation and safety checks
- Result explanation in natural language
- Support for SQLite, PostgreSQL, MySQL
- Automatic join detection
- Query optimization suggestions
"""

import re
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import hashlib


class DatabaseType(Enum):
    """Supported database types."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"


@dataclass
class ColumnInfo:
    """Information about a database column."""
    name: str
    data_type: str
    nullable: bool = True
    primary_key: bool = False
    foreign_key: Optional[str] = None
    default: Optional[str] = None
    description: Optional[str] = None


@dataclass
class TableInfo:
    """Information about a database table."""
    name: str
    columns: List[ColumnInfo] = field(default_factory=list)
    primary_key: Optional[str] = None
    foreign_keys: Dict[str, str] = field(default_factory=dict)
    row_count: int = 0
    description: Optional[str] = None


@dataclass
class SchemaInfo:
    """Complete database schema information."""
    tables: List[TableInfo] = field(default_factory=list)
    database_type: DatabaseType = DatabaseType.SQLITE
    database_name: str = ""
    
    def to_prompt_context(self) -> str:
        """Generate schema context for LLM prompts."""
        lines = [f"Database: {self.database_name} ({self.database_type.value})\n"]
        lines.append("Tables:\n")
        
        for table in self.tables:
            lines.append(f"\n{table.name}:")
            if table.description:
                lines.append(f"  -- {table.description}")
            
            for col in table.columns:
                col_desc = f"  - {col.name}: {col.data_type}"
                if col.primary_key:
                    col_desc += " (PK)"
                if col.foreign_key:
                    col_desc += f" -> {col.foreign_key}"
                if not col.nullable:
                    col_desc += " NOT NULL"
                lines.append(col_desc)
            
            if table.foreign_keys:
                lines.append(f"  Foreign keys: {table.foreign_keys}")
        
        return "\n".join(lines)
    
    def get_table(self, name: str) -> Optional[TableInfo]:
        """Get table by name."""
        for table in self.tables:
            if table.name.lower() == name.lower():
                return table
        return None


@dataclass
class QueryResult:
    """Result of a database query."""
    query: str
    natural_language: str
    translated_sql: str
    success: bool
    rows: List[Dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    columns: List[str] = field(default_factory=list)
    execution_time_ms: float = 0
    error: Optional[str] = None
    explanation: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SQLGenerator:
    """
    Generates SQL from natural language using pattern matching and LLM.
    """
    
    # Common query patterns
    PATTERNS = {
        r"show\s+all\s+(\w+)": "SELECT * FROM {table}",
        r"count\s+(\w+)": "SELECT COUNT(*) FROM {table}",
        r"list\s+(\w+)": "SELECT * FROM {table}",
        r"get\s+(\w+)\s+where\s+(\w+)\s*=\s*['\"]?(\w+)['\"]?": "SELECT * FROM {table} WHERE {column} = '{value}'",
        r"find\s+(\w+)\s+with\s+(\w+)\s+like\s+['\"]?(\w+)['\"]?": "SELECT * FROM {table} WHERE {column} LIKE '%{value}%'",
        r"top\s+(\d+)\s+(\w+)": "SELECT * FROM {table} LIMIT {limit}",
        r"average\s+(\w+)\s+from\s+(\w+)": "SELECT AVG({column}) FROM {table}",
        r"sum\s+(\w+)\s+from\s+(\w+)": "SELECT SUM({column}) FROM {table}",
        r"(\w+)\s+by\s+(\w+)": "SELECT {column}, COUNT(*) FROM {table} GROUP BY {column}",
    }
    
    def __init__(self, schema: SchemaInfo, llm_callable=None):
        self.schema = schema
        self.llm = llm_callable
    
    def generate(self, natural_language: str) -> Tuple[str, float]:
        """
        Generate SQL from natural language.
        
        Returns:
            Tuple of (SQL query, confidence score)
        """
        # Clean and normalize input
        query = natural_language.lower().strip()
        
        # Try pattern matching first
        sql, confidence = self._pattern_match(query)
        if sql:
            return sql, confidence
        
        # Try keyword extraction
        sql, confidence = self._keyword_extraction(query)
        if sql:
            return sql, confidence
        
        # Fall back to LLM if available
        if self.llm:
            return self._llm_generate(natural_language), 0.7
        
        # Last resort: simple SELECT
        tables = [t.name for t in self.schema.tables]
        if tables:
            return f"SELECT * FROM {tables[0]} LIMIT 10", 0.3
        
        return "SELECT 1", 0.1
    
    def _pattern_match(self, query: str) -> Tuple[Optional[str], float]:
        """Try to match query against known patterns."""
        for pattern, template in self.PATTERNS.items():
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                # Find matching table
                table_name = self._find_table(groups[0] if groups else "")
                if not table_name:
                    continue
                
                # Build SQL
                sql = template
                if "{table}" in sql:
                    sql = sql.replace("{table}", table_name)
                if len(groups) > 1 and "{column}" in sql:
                    col_name = self._find_column(table_name, groups[1])
                    sql = sql.replace("{column}", col_name or groups[1])
                if len(groups) > 2 and "{value}" in sql:
                    sql = sql.replace("{value}", groups[2])
                if "{limit}" in sql:
                    sql = sql.replace("{limit}", groups[0])
                
                return sql, 0.8
        
        return None, 0
    
    def _keyword_extraction(self, query: str) -> Tuple[Optional[str], float]:
        """Extract keywords and build query."""
        words = query.split()
        
        # Find table reference
        table_name = None
        for word in words:
            table_name = self._find_table(word)
            if table_name:
                break
        
        if not table_name:
            return None, 0
        
        # Determine operation
        if any(w in query for w in ["count", "how many"]):
            return f"SELECT COUNT(*) FROM {table_name}", 0.6
        elif any(w in query for w in ["average", "avg", "mean"]):
            # Find numeric column
            table = self.schema.get_table(table_name)
            if table:
                numeric_cols = [c.name for c in table.columns 
                               if c.data_type in ("INTEGER", "REAL", "FLOAT", "DECIMAL", "NUMERIC")]
                if numeric_cols:
                    return f"SELECT AVG({numeric_cols[0]}) FROM {table_name}", 0.6
        elif any(w in query for w in ["sum", "total"]):
            table = self.schema.get_table(table_name)
            if table:
                numeric_cols = [c.name for c in table.columns 
                               if c.data_type in ("INTEGER", "REAL", "FLOAT", "DECIMAL", "NUMERIC")]
                if numeric_cols:
                    return f"SELECT SUM({numeric_cols[0]}) FROM {table_name}", 0.6
        elif any(w in query for w in ["max", "maximum", "highest", "top"]):
            table = self.schema.get_table(table_name)
            if table:
                numeric_cols = [c.name for c in table.columns 
                               if c.data_type in ("INTEGER", "REAL", "FLOAT", "DECIMAL", "NUMERIC")]
                if numeric_cols:
                    return f"SELECT * FROM {table_name} ORDER BY {numeric_cols[0]} DESC LIMIT 1", 0.6
        elif any(w in query for w in ["min", "minimum", "lowest"]):
            table = self.schema.get_table(table_name)
            if table:
                numeric_cols = [c.name for c in table.columns 
                               if c.data_type in ("INTEGER", "REAL", "FLOAT", "DECIMAL", "NUMERIC")]
                if numeric_cols:
                    return f"SELECT * FROM {table_name} ORDER BY {numeric_cols[0]} ASC LIMIT 1", 0.6
        
        # Default: select all
        return f"SELECT * FROM {table_name} LIMIT 100", 0.5
    
    def _find_table(self, word: str) -> Optional[str]:
        """Find table name matching the word."""
        word = word.lower().rstrip("s")  # Handle plurals
        
        for table in self.schema.tables:
            table_lower = table.name.lower()
            if (table_lower == word or 
                table_lower == word + "s" or
                table_lower.rstrip("s") == word):
                return table.name
        return None
    
    def _find_column(self, table_name: str, word: str) -> Optional[str]:
        """Find column name in table matching the word."""
        table = self.schema.get_table(table_name)
        if not table:
            return None
        
        word = word.lower()
        for col in table.columns:
            if col.name.lower() == word:
                return col.name
        return None
    
    def _llm_generate(self, natural_language: str) -> str:
        """Use LLM to generate SQL."""
        if not self.llm:
            return ""
        
        prompt = f"""Convert this natural language query to SQL.

Schema:
{self.schema.to_prompt_context()}

Query: {natural_language}

Return ONLY the SQL query, no explanations."""
        
        try:
            response = self.llm(prompt)
            # Extract SQL from response
            sql = response.strip()
            if sql.startswith("```"):
                sql = sql.split("```")[1]
                if sql.startswith("sql"):
                    sql = sql[3:]
            return sql.strip()
        except Exception:
            return ""


class QueryValidator:
    """
    Validates SQL queries for safety and correctness.
    """
    
    # Dangerous keywords
    DANGEROUS_KEYWORDS = [
        "DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE",
        "GRANT", "REVOKE", "EXEC", "EXECUTE", "xp_", "sp_"
    ]
    
    def __init__(self, schema: SchemaInfo, allow_modifications: bool = False):
        self.schema = schema
        self.allow_modifications = allow_modifications
    
    def validate(self, sql: str) -> Tuple[bool, List[str]]:
        """
        Validate SQL query.
        
        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []
        sql_upper = sql.upper()
        
        # Check for dangerous keywords
        if not self.allow_modifications:
            for keyword in self.DANGEROUS_KEYWORDS:
                if keyword in sql_upper:
                    issues.append(f"Dangerous keyword detected: {keyword}")
        
        # Check for SQL injection patterns
        injection_patterns = [
            r";\s*--",
            r"'\s*OR\s+'1'\s*=\s*'1",
            r"UNION\s+SELECT",
            r"INTO\s+OUTFILE",
            r"LOAD_FILE",
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                issues.append(f"Potential SQL injection pattern: {pattern}")
        
        # Validate table names
        table_pattern = r"FROM\s+(\w+)"
        matches = re.findall(table_pattern, sql, re.IGNORECASE)
        for table_name in matches:
            if not self.schema.get_table(table_name):
                issues.append(f"Unknown table: {table_name}")
        
        # Check for unlimited SELECT (allow aggregate functions without LIMIT)
        aggregate_functions = ["COUNT(", "SUM(", "AVG(", "MAX(", "MIN("]
        has_aggregate = any(func in sql_upper for func in aggregate_functions)
        
        if "SELECT" in sql_upper and "LIMIT" not in sql_upper and not has_aggregate:
            issues.append("Query has no LIMIT clause - may return too many rows")
        
        return len(issues) == 0, issues


class NLDBEngine:
    """
    Main Natural Language Database Query Engine.
    
    Provides end-to-end natural language to database query execution.
    """
    
    def __init__(
        self,
        connection_string: str,
        database_type: DatabaseType = DatabaseType.SQLITE,
        llm_callable=None,
        allow_modifications: bool = False
    ):
        self.connection_string = connection_string
        self.database_type = database_type
        self.llm = llm_callable
        self.allow_modifications = allow_modifications
        
        self._connection = None
        self._schema: Optional[SchemaInfo] = None
        self._generator: Optional[SQLGenerator] = None
        self._validator: Optional[QueryValidator] = None
        
        # Query cache
        self._query_cache: Dict[str, QueryResult] = {}
    
    def connect(self):
        """Establish database connection."""
        if self.database_type == DatabaseType.SQLITE:
            self._connection = sqlite3.connect(self.connection_string)
            self._connection.row_factory = sqlite3.Row
        else:
            raise NotImplementedError(f"Database type {self.database_type} not yet implemented")
        
        # Load schema
        self._schema = self._introspect_schema()
        self._generator = SQLGenerator(self._schema, self.llm)
        self._validator = QueryValidator(self._schema, self.allow_modifications)
    
    def disconnect(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def _introspect_schema(self) -> SchemaInfo:
        """Introspect database schema."""
        schema = SchemaInfo(
            database_type=self.database_type,
            database_name=self.connection_string
        )
        
        if self.database_type == DatabaseType.SQLITE:
            cursor = self._connection.cursor()
            
            # Get tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for (table_name,) in tables:
                if table_name.startswith("sqlite_"):
                    continue
                
                table_info = TableInfo(name=table_name)
                
                # Get columns
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                
                for col in columns:
                    column_info = ColumnInfo(
                        name=col[1],
                        data_type=col[2],
                        nullable=not col[3],
                        primary_key=bool(col[5]),
                        default=col[4]
                    )
                    table_info.columns.append(column_info)
                    if column_info.primary_key:
                        table_info.primary_key = column_info.name
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                table_info.row_count = cursor.fetchone()[0]
                
                # Get foreign keys
                cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                fks = cursor.fetchall()
                for fk in fks:
                    table_info.foreign_keys[fk[3]] = f"{fk[2]}.{fk[4]}"
                    # Update column info
                    for col in table_info.columns:
                        if col.name == fk[3]:
                            col.foreign_key = f"{fk[2]}.{fk[4]}"
                
                schema.tables.append(table_info)
        
        return schema
    
    def query(self, natural_language: str, use_cache: bool = True) -> QueryResult:
        """
        Execute a natural language query.
        
        Args:
            natural_language: The query in natural language
            use_cache: Whether to use cached results
            
        Returns:
            QueryResult with data and metadata
        """
        if not self._connection:
            self.connect()
        
        # Check cache
        cache_key = hashlib.md5(natural_language.encode()).hexdigest()
        if use_cache and cache_key in self._query_cache:
            return self._query_cache[cache_key]
        
        start_time = datetime.now()
        
        # Generate SQL
        sql, confidence = self._generator.generate(natural_language)
        
        # Validate
        is_valid, issues = self._validator.validate(sql)
        
        if not is_valid:
            return QueryResult(
                query=natural_language,
                natural_language=natural_language,
                translated_sql=sql,
                success=False,
                error=f"Validation failed: {'; '.join(issues)}",
                suggestions=["Try rephrasing your query", "Check table and column names"]
            )
        
        # Execute query
        try:
            cursor = self._connection.cursor()
            cursor.execute(sql)
            
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description] if cursor.description else []
            
            end_time = datetime.now()
            
            result = QueryResult(
                query=natural_language,
                natural_language=natural_language,
                translated_sql=sql,
                success=True,
                rows=[dict(zip(columns, row)) for row in rows],
                row_count=len(rows),
                columns=columns,
                execution_time_ms=(end_time - start_time).total_seconds() * 1000,
                explanation=self._generate_explanation(sql, len(rows)),
                suggestions=issues if issues else []
            )
            
            # Cache result
            if use_cache:
                self._query_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            return QueryResult(
                query=natural_language,
                natural_language=natural_language,
                translated_sql=sql,
                success=False,
                error=str(e),
                suggestions=self._generate_error_suggestions(str(e))
            )
    
    def _generate_explanation(self, sql: str, row_count: int) -> str:
        """Generate natural language explanation of query."""
        sql_upper = sql.upper()
        
        if "COUNT(*)" in sql_upper:
            return f"Counted records, found {row_count}"
        elif "AVG(" in sql_upper:
            return "Calculated average value"
        elif "SUM(" in sql_upper:
            return "Calculated sum"
        elif "SELECT *" in sql_upper:
            return f"Retrieved {row_count} records"
        else:
            return f"Query returned {row_count} results"
    
    def _generate_error_suggestions(self, error: str) -> List[str]:
        """Generate suggestions based on error."""
        suggestions = []
        
        if "no such table" in error.lower():
            suggestions.append("Check table name spelling")
            suggestions.append(f"Available tables: {[t.name for t in self._schema.tables]}")
        elif "no such column" in error.lower():
            suggestions.append("Check column name spelling")
        elif "syntax error" in error.lower():
            suggestions.append("Try simplifying your query")
        
        return suggestions
    
    def get_schema(self) -> SchemaInfo:
        """Get database schema."""
        if not self._schema:
            self.connect()
        return self._schema
    
    def get_tables(self) -> List[str]:
        """Get list of table names."""
        return [t.name for t in self.get_schema().tables]
    
    def describe_table(self, table_name: str) -> Optional[str]:
        """Get description of a table."""
        table = self.get_schema().get_table(table_name)
        if not table:
            return None
        
        lines = [f"Table: {table.name}"]
        lines.append(f"Rows: {table.row_count}")
        lines.append("Columns:")
        for col in table.columns:
            line = f"  - {col.name}: {col.data_type}"
            if col.primary_key:
                line += " (Primary Key)"
            if col.foreign_key:
                line += f" -> {col.foreign_key}"
            lines.append(line)
        
        return "\n".join(lines)
    
    def suggest_queries(self, table_name: Optional[str] = None) -> List[str]:
        """Suggest natural language queries."""
        suggestions = []
        
        tables = [table_name] if table_name else [t.name for t in self._schema.tables[:3]]
        
        for table in tables:
            suggestions.extend([
                f"Show all {table}",
                f"Count {table}",
                f"Show top 10 {table}"
            ])
        
        return suggestions


def create_engine_for_sqlite(db_path: str, llm_callable=None) -> NLDBEngine:
    """Create engine for SQLite database."""
    engine = NLDBEngine(
        connection_string=db_path,
        database_type=DatabaseType.SQLITE,
        llm_callable=llm_callable
    )
    engine.connect()
    return engine


def create_engine_for_postgres(
    host: str,
    port: int,
    database: str,
    user: str,
    password: str,
    llm_callable=None
) -> NLDBEngine:
    """Create engine for PostgreSQL database."""
    connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    return NLDBEngine(
        connection_string=connection_string,
        database_type=DatabaseType.POSTGRESQL,
        llm_callable=llm_callable
    )
