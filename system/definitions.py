from __future__ import annotations

LOGIC_DEFINITIONS = [
    {
        "name": "sales_summary",
        "domain": "sales",
        "description": "Summarize total sales and order count from the sales table.",
        "function_name": "get_sales_summary",
        "business_terms": ["sales", "summary", "revenue"],
        "used_tables": ["sales", "orders", "transactions"],
        "used_apis": ["database.sql_executor.execute_sql"],
        "routing_metadata": {"intent": ["summary"], "priority": 1},
    },
    {
        "name": "sales_ranking",
        "domain": "sales",
        "description": "Return the top customers by sales amount.",
        "function_name": "get_top_customers",
        "business_terms": ["sales", "ranking", "top customers"],
        "used_tables": ["sales", "orders", "transactions"],
        "used_apis": ["database.sql_executor.execute_sql"],
        "routing_metadata": {"intent": ["ranking"], "priority": 2},
    },
    {
        "name": "product_search",
        "domain": "product",
        "description": "Search products using a keyword over product name columns.",
        "function_name": "search_products",
        "business_terms": ["product", "search", "keyword"],
        "used_tables": ["products"],
        "used_apis": ["database.sql_executor.execute_sql"],
        "routing_metadata": {"intent": ["search"], "priority": 3},
    },
    {
        "name": "customer_detail",
        "domain": "customer",
        "description": "Retrieve customer rows or a single customer record.",
        "function_name": "get_customers",
        "business_terms": ["customer", "detail", "profile"],
        "used_tables": ["customers"],
        "used_apis": ["database.sql_executor.execute_sql"],
        "routing_metadata": {"intent": ["detail"], "priority": 4},
    },
]
