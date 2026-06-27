from pathlib import Path
import pandas as pd
from database.importer import import_latest_excel_to_sqlite
from business.customer import get_top_customers_by_sales
import tempfile
import os

with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    excel_dir = tmp_path / 'excel'
    excel_dir.mkdir(parents=True)
    db_path = tmp_path / 'sqlite' / 'logsys.db'
    os.makedirs(db_path.parent, exist_ok=True)
    workbook = excel_dir / 'sample.xlsx'
    with pd.ExcelWriter(workbook) as writer:
        pd.DataFrame({'customer_code': ['C001', 'C002', 'C003'], 'customer_name': ['Acme', 'Zenith', 'Orbit'], 'sales': [100.0, 150.0, 50.0]}).to_excel(writer, sheet_name='Customers', index=False)
    import_latest_excel_to_sqlite(excel_dir, db_path)
    result = get_top_customers_by_sales(db_path, limit=2)
    print(result)
