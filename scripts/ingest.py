"""Preflight and atomically load the eight Complete Journey CSVs into PostgreSQL."""

import argparse
import csv
import os
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

import psycopg2


# Each pair is the exact CSV header and the corresponding PostgreSQL type.
# The destination column name is the lower-case form of the header.
TABLES = {
    "campaign_desc": (
        ("DESCRIPTION", "text"), ("CAMPAIGN", "integer"),
        ("START_DAY", "integer"), ("END_DAY", "integer"),
    ),
    "campaign_table": (
        ("DESCRIPTION", "text"), ("household_key", "integer"), ("CAMPAIGN", "integer"),
    ),
    "causal_data": (
        ("PRODUCT_ID", "bigint"), ("STORE_ID", "integer"), ("WEEK_NO", "integer"),
        ("display", "text"), ("mailer", "text"),
    ),
    "coupon": (
        ("COUPON_UPC", "bigint"), ("PRODUCT_ID", "bigint"), ("CAMPAIGN", "integer"),
    ),
    "coupon_redempt": (
        ("household_key", "integer"), ("DAY", "integer"),
        ("COUPON_UPC", "bigint"), ("CAMPAIGN", "integer"),
    ),
    "hh_demographic": (
        ("AGE_DESC", "text"), ("MARITAL_STATUS_CODE", "text"),
        ("INCOME_DESC", "text"), ("HOMEOWNER_DESC", "text"),
        ("HH_COMP_DESC", "text"), ("HOUSEHOLD_SIZE_DESC", "text"),
        ("KID_CATEGORY_DESC", "text"), ("household_key", "integer"),
    ),
    "product": (
        ("PRODUCT_ID", "bigint"), ("MANUFACTURER", "integer"),
        ("DEPARTMENT", "text"), ("BRAND", "text"),
        ("COMMODITY_DESC", "text"), ("SUB_COMMODITY_DESC", "text"),
        ("CURR_SIZE_OF_PRODUCT", "text"),
    ),
    "transaction_data": (
        ("household_key", "integer"), ("BASKET_ID", "bigint"),
        ("DAY", "integer"), ("PRODUCT_ID", "bigint"),
        ("QUANTITY", "numeric"), ("SALES_VALUE", "numeric"),
        ("STORE_ID", "integer"), ("RETAIL_DISC", "numeric"),
        ("TRANS_TIME", "integer"), ("WEEK_NO", "integer"),
        ("COUPON_DISC", "numeric"), ("COUPON_MATCH_DISC", "numeric"),
    ),
}

INTEGER = re.compile(r"[+-]?[0-9]+\Z")
NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\Z")


@dataclass(frozen=True)
class CsvInput:
    path: Path
    rows: int


def _identifier(name: str) -> str:
    """Quote a fixed, checked identifier; never interpolate a CSV or CLI value."""
    if not IDENTIFIER.fullmatch(name):
        raise ValueError("Invalid internal SQL identifier")
    return '"' + name.lower() + '"'


def _table(name: str) -> str:
    if name not in TABLES:
        raise ValueError("Unknown raw table")
    return '"raw".' + _identifier(name)


def _validate_value(value: str, kind: str, filename: str, line: int, column: str) -> None:
    if "\x00" in value:
        raise ValueError(f"{filename} line {line}: NUL byte in {column}")
    if value == "" or kind == "text":
        return  # Empty CSV fields become PostgreSQL NULLs.
    value = value.strip()
    if kind in ("integer", "bigint"):
        if not INTEGER.fullmatch(value):
            raise ValueError(f"{filename} line {line}: invalid {kind} in {column}")
        sign = -1 if value.startswith("-") else 1
        digits = value.lstrip("+-").lstrip("0") or "0"
        if len(digits) > (10 if kind == "integer" else 19):
            raise ValueError(f"{filename} line {line}: {kind} out of range in {column}")
        number = sign * int(digits)
        limit = 2**31 if kind == "integer" else 2**63
        if not -limit <= number < limit:
            raise ValueError(f"{filename} line {line}: {kind} out of range in {column}")
    elif kind == "numeric":
        if not NUMBER.fullmatch(value):
            raise ValueError(f"{filename} line {line}: invalid numeric in {column}")
        try:
            Decimal(value)
        except InvalidOperation as error:
            raise ValueError(f"{filename} line {line}: invalid numeric in {column}") from error


def preflight(data_dir: Path) -> dict[str, CsvInput]:
    """Check every file and row without opening a database connection."""
    try:
        data_dir = Path(data_dir)
    except TypeError as error:
        raise ValueError("A CSV directory is required") from error
    paths = {name: data_dir / f"{name}.csv" for name in TABLES}
    missing = [path.name for path in paths.values() if not path.is_file()]
    if missing:
        raise ValueError("Missing required CSV files: " + ", ".join(missing))

    checked = {}
    for name, columns in TABLES.items():
        filename = paths[name].name
        expected = [column for column, _ in columns]
        try:
            with paths[name].open(encoding="utf-8-sig", newline="") as source:
                reader = csv.reader(source, strict=True)
                header = next(reader, None)
                if header is None:
                    raise ValueError(f"{filename}: missing header")
                seen = set()
                duplicates = set()
                for column in header:
                    key = column.casefold()
                    if key in seen:
                        duplicates.add(column)
                    seen.add(key)
                if duplicates:
                    raise ValueError(f"{filename}: duplicate header columns: {', '.join(sorted(duplicates))}")
                absent = [column for column in expected if column not in header]
                if absent:
                    raise ValueError(f"{filename}: missing required columns: {', '.join(absent)}")
                extra = [column for column in header if column not in expected]
                if extra:
                    raise ValueError(f"{filename}: unexpected columns: {', '.join(extra)}")
                if header != expected:
                    raise ValueError(f"{filename}: columns are not in the declared order")

                count = 0
                for row in reader:
                    count += 1
                    if len(row) != len(columns):
                        raise ValueError(
                            f"{filename} line {reader.line_num}: expected {len(columns)} fields, found {len(row)}"
                        )
                    for value, (column, kind) in zip(row, columns):
                        _validate_value(value, kind, filename, reader.line_num, column)
                if count == 0:
                    raise ValueError(f"{filename}: no data rows")
                checked[name] = CsvInput(paths[name], count)
        except csv.Error as error:
            raise ValueError(f"{filename}: malformed CSV near line {reader.line_num}") from error
        except (OSError, UnicodeError) as error:
            raise ValueError(f"{filename}: cannot read a valid UTF-8 CSV ({type(error).__name__})") from error
    return checked


def _connection_config() -> dict:
    values = {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "dbname": os.getenv("POSTGRES_DB", "retail_analytics"),
        "user": os.getenv("POSTGRES_USER", "retail_user"),
        "password": os.getenv("POSTGRES_PASSWORD"),
    }
    for key, value in values.items():
        if value is None or not value.strip():
            raise ValueError(f"Invalid PostgreSQL configuration: {key} is required")
    port = os.getenv("POSTGRES_PORT", "5432")
    if not port.isascii() or not port.isdecimal() or not 1 <= int(port) <= 65535:
        raise ValueError("Invalid PostgreSQL configuration: POSTGRES_PORT must be 1-65535")
    values["port"] = int(port)
    values["connect_timeout"] = 10
    return values


def _existing_tables(cursor) -> set[str]:
    """Reject existing views or tables whose columns, types or order differ."""
    cursor.execute(
        """SELECT c.relname, c.relkind, a.attname,
                  format_type(a.atttypid, a.atttypmod)
             FROM pg_catalog.pg_class AS c
             JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
             LEFT JOIN pg_catalog.pg_attribute AS a
               ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
            WHERE n.nspname = %s AND c.relname = ANY(%s)
            ORDER BY c.relname, a.attnum""",
        ("raw", list(TABLES)),
    )
    actual = {}
    for name, relation_kind, column, data_type in cursor.fetchall():
        if relation_kind != "r":
            raise ValueError(f"raw.{name}: expected an ordinary table")
        actual.setdefault(name, []).append((column, data_type))
    for name, columns in actual.items():
        expected = [(column.lower(), kind) for column, kind in TABLES[name]]
        if columns != expected:
            raise ValueError(f"raw.{name}: destination columns or types differ from the declared mapping")
    return set(actual)


def load(data_dir: Path, *, replace_existing: bool = False) -> None:
    """Load atomically; refuse populated tables unless replacement is explicit."""
    if type(replace_existing) is not bool:
        raise ValueError("replace_existing must be a boolean")
    config = _connection_config()
    inputs = preflight(data_dir)
    try:
        connection = psycopg2.connect(**config)
    except psycopg2.Error:
        raise RuntimeError("Could not connect to PostgreSQL; check the local connection configuration") from None
    counts = {}
    try:
        with connection:
            with connection.cursor() as cursor:
                existing = _existing_tables(cursor)
                if existing:
                    lock_mode = "ACCESS EXCLUSIVE" if replace_existing else "SHARE"
                    tables_to_lock = ", ".join(_table(name) for name in TABLES if name in existing)
                    cursor.execute(f"LOCK TABLE {tables_to_lock} IN {lock_mode} MODE")
                    existing = _existing_tables(cursor)  # Recheck after taking the locks.
                    if not replace_existing:
                        for name in TABLES:
                            if name in existing:
                                cursor.execute(f"SELECT EXISTS (SELECT 1 FROM {_table(name)})")
                                if cursor.fetchone()[0]:
                                    raise ValueError("Raw tables contain data; use --replace-existing to replace them")

                cursor.execute('CREATE SCHEMA IF NOT EXISTS "raw"')
                for name, columns in TABLES.items():
                    if name not in existing:
                        definitions = ", ".join(f"{_identifier(column)} {kind}" for column, kind in columns)
                        cursor.execute(f"CREATE TABLE IF NOT EXISTS {_table(name)} ({definitions})")
                if _existing_tables(cursor) != set(TABLES):
                    raise ValueError("The raw destination is missing a required table")

                if replace_existing:
                    cursor.execute("TRUNCATE " + ", ".join(_table(name) for name in TABLES))
                for name, columns in TABLES.items():
                    mapped = ", ".join(_identifier(column) for column, _ in columns)
                    statement = f"COPY {_table(name)} ({mapped}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE)"
                    with inputs[name].path.open(encoding="utf-8-sig", newline="") as source:
                        cursor.copy_expert(statement, source)
                    cursor.execute(f"SELECT COUNT(*) FROM {_table(name)}")
                    count = cursor.fetchone()[0]
                    if count != inputs[name].rows:
                        raise ValueError(f"{name}: loaded row count differs from CSV preflight")
                    counts[name] = count
    except psycopg2.Error:
        raise RuntimeError(
            "PostgreSQL rejected the load; the transaction was rolled back. Row details are withheld"
        ) from None
    finally:
        connection.close()
    for name, count in counts.items():
        print(f"{name}: {count:,} rows")
    print("Raw load committed")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data" / "raw")
    parser.add_argument("--preflight-only", action="store_true", help="Validate CSVs without connecting to PostgreSQL")
    parser.add_argument(
        "--replace-existing", action="store_true",
        help="Explicitly replace all eight raw tables in one transaction",
    )
    args = parser.parse_args(argv)
    if args.preflight_only and args.replace_existing:
        parser.error("--preflight-only cannot be combined with --replace-existing")
    if args.preflight_only:
        inputs = preflight(args.data_dir)
        for name, item in inputs.items():
            print(f"{name}: {item.rows:,} rows checked")
        print("CSV preflight passed; no database connection opened")
    else:
        load(args.data_dir, replace_existing=args.replace_existing)


if __name__ == "__main__":
    main()
