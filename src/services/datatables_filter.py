# datatables.py

from typing import List, Dict, Any

from datatables import DataTables, ColumnDT
from sqlalchemy import (create_engine, Table, Column, Integer, String, MetaData)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


def process_inmemory_datatable(
        request_dict: Dict,
        columns: List[str],
        source_data: List[List[Any]]
) -> Dict:
    """
    Uses an in-memory SQLite database and a dynamic ORM model to robustly
    handle DataTables logic for in-memory data.
    """
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    table_name = "results"

    sql_columns = [Column("id", Integer, primary_key=True, autoincrement=True)]
    safe_column_names = []
    for name in columns:
        safe_name = ''.join(e for e in name if e.isalnum() or e == '_')
        if not safe_name or safe_name in safe_column_names or safe_name == 'id':
            safe_name = f"{safe_name}_{len(safe_column_names)}"
        safe_column_names.append(safe_name)
        sql_columns.append(Column(safe_name, String))

    results_table = Table(table_name, metadata, *sql_columns)
    metadata.create_all(engine)

    Base = declarative_base()

    class TmpModel(Base):
        __table__ = results_table

    if source_data:
        # We add a dummy ID (the row index) when inserting
        data_to_insert = [
            dict(zip(['id'] + safe_column_names, [i] + row))
            for i, row in enumerate(source_data)
        ]
        if data_to_insert:
            with engine.connect() as conn:
                conn.execute(results_table.insert(), data_to_insert)
                conn.commit()

    Session = sessionmaker(bind=engine)
    session = Session()

    query = session.query(TmpModel)

    # The library still needs to know about 'id' for sorting
    all_columns_for_library = ['id'] + safe_column_names
    dt_columns = [ColumnDT(getattr(TmpModel, col)) for col in all_columns_for_library]

    datatable = DataTables(
        request_dict,
        query,
        dt_columns
    )

    result = datatable.output_result()

    # --- THE FINAL FIX ---
    # We now format the output using ONLY the original safe_column_names,
    # hiding the 'id' column from the browser.
    formatted_data = []
    if result['data']:
        for row_obj in result['data']:
            model_instance = row_obj['0']
            # Build the row using only the columns you want to see
            new_row = [getattr(model_instance, col) for col in safe_column_names]
            formatted_data.append(new_row)

    result['data'] = formatted_data
    return result
