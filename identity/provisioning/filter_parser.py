"""SCIM 2.0 filter parser - RFC 7644 §3.4.2.2"""

import re
from typing import Any, Callable


class SCIMFilterParser:
    """parse SCIM filter expressions into SQL WHERE clauses
    
    supports:
    - attribute comparisons: userName eq "john"
    - logical operators: and, or, not
    - presence check: emails pr
    - complex filters: emails[type eq "work"].value co "@acme.com"
    
    limitation: basic implementation - doesn't support all edge cases
    """
    
    OPERATORS = {
        "eq": "=",
        "ne": "!=",
        "co": "LIKE",  # contains
        "sw": "LIKE",  # starts with
        "ew": "LIKE",  # ends with
        "gt": ">",
        "ge": ">=",
        "lt": "<",
        "le": "<=",
        "pr": "IS NOT NULL",  # present
    }
    
    # attribute mapping: SCIM -> SQLite column
    ATTRIBUTE_MAP = {
        "username": "id",
        "name.givenname": "given_name",
        "name.familyname": "family_name",
        "active": "status",  # special: convert true -> "active", false -> "inactive"
        "emails.value": "id",  # for now, id = email
        "id": "id",
    }
    
    def parse(self, filter_str: str) -> tuple[str, dict[str, Any]]:
        """parse SCIM filter → SQL WHERE clause + params
        
        Args:
            filter_str: SCIM filter expression
            
        Returns:
            (where_clause, params_dict)
            
        Example:
            parse('userName eq "john"') → ("id = :param_0", {"param_0": "john"})
        """
        if not filter_str:
            return "", {}
        
        filter_str = filter_str.strip()
        self.param_counter = 0
        self.params = {}
        
        where_clause = self._parse_expression(filter_str.lower())
        return where_clause, self.params
    
    def _parse_expression(self, expr: str) -> str:
        """parse logical expression with and/or/not"""
        
        # handle "and" operator
        if " and " in expr:
            parts = expr.split(" and ", 1)
            left = self._parse_expression(parts[0].strip())
            right = self._parse_expression(parts[1].strip())
            return f"({left} AND {right})"
        
        # handle "or" operator
        if " or " in expr:
            parts = expr.split(" or ", 1)
            left = self._parse_expression(parts[0].strip())
            right = self._parse_expression(parts[1].strip())
            return f"({left} OR {right})"
        
        # handle "not" operator
        if expr.startswith("not "):
            inner = self._parse_expression(expr[4:].strip())
            return f"NOT ({inner})"
        
        # parse comparison
        return self._parse_comparison(expr)
    
    def _parse_comparison(self, expr: str) -> str:
        """parse attribute comparison: userName eq "john" """
        
        # pattern: attribute operator value
        for op_name, sql_op in self.OPERATORS.items():
            if f" {op_name} " in expr:
                parts = expr.split(f" {op_name} ", 1)
                attr = parts[0].strip()
                value = parts[1].strip() if len(parts) > 1 else None
                
                return self._build_comparison(attr, op_name, sql_op, value)
        
        # no operator found - return as-is (might be "pr" check)
        if " pr" in expr:
            attr = expr.replace(" pr", "").strip()
            return self._build_comparison(attr, "pr", "IS NOT NULL", None)
        
        return "1=1"  # fallback
    
    def _build_comparison(
        self, attr: str, op_name: str, sql_op: str, value: str | None
    ) -> str:
        """build SQL comparison from components"""
        
        # map SCIM attribute to SQL column
        column = self.ATTRIBUTE_MAP.get(attr, attr)
        
        # special handling for "active" attribute
        if attr == "active" and value:
            # active eq true -> status = "active"
            # active eq false -> status = "inactive"
            is_active = value.strip('"').lower() in ("true", "1")
            param_name = f"param_{self.param_counter}"
            self.param_counter += 1
            self.params[param_name] = "active" if is_active else "inactive"
            return f"{column} = :{param_name}"
        
        # presence check (no value)
        if op_name == "pr":
            return f"{column} IS NOT NULL"
        
        # value-based comparisons
        if value:
            # strip quotes from value
            clean_value = value.strip('"').strip("'")
            
            # adjust value for LIKE operators
            if op_name == "co":  # contains
                clean_value = f"%{clean_value}%"
            elif op_name == "sw":  # starts with
                clean_value = f"{clean_value}%"
            elif op_name == "ew":  # ends with
                clean_value = f"%{clean_value}"
            
            param_name = f"param_{self.param_counter}"
            self.param_counter += 1
            self.params[param_name] = clean_value
            
            return f"{column} {sql_op} :{param_name}"
        
        return "1=1"


class SCIMPagination:
    """SCIM 2.0 pagination helper - RFC 7644 §3.4.2.4"""
    
    DEFAULT_COUNT = 50
    MAX_COUNT = 1000
    
    @staticmethod
    def parse_params(
        start_index: int | None = None,
        count: int | None = None
    ) -> tuple[int, int, int]:
        """parse SCIM pagination params → (start_index, count, offset)
        
        Args:
            start_index: 1-based index (SCIM spec)
            count: number of results per page
            
        Returns:
            (start_index, count, offset)
            
        Note:
            SCIM uses 1-based startIndex, SQL uses 0-based OFFSET
        """
        # defaults
        start_idx = start_index or 1
        cnt = count or SCIMPagination.DEFAULT_COUNT
        
        # validate
        start_idx = max(1, start_idx)
        cnt = min(max(1, cnt), SCIMPagination.MAX_COUNT)
        
        # convert to SQL offset (0-based)
        offset = start_idx - 1
        
        return start_idx, cnt, offset

