"""Offline tests for the ingestion preflight and replacement guardrails."""

import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts import ingest


def catalog_rows(*names):
    return [
        (name, "r", column.lower(), kind)
        for name in names
        for column, kind in ingest.TABLES[name]
    ]


class IngestTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.data_dir = Path(temporary.name)
        for name, columns in ingest.TABLES.items():
            self.write_csv(name, [column for column, _ in columns], [self.example_row(columns)])

    def write_csv(self, name, header, rows):
        with (self.data_dir / f"{name}.csv").open("w", encoding="utf-8", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(header)
            writer.writerows(rows)

    @staticmethod
    def example_row(columns):
        return ["sample" if kind == "text" else "1" for _, kind in columns]

    def db_mock(self, *, populated=False):
        connection = MagicMock()
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = catalog_rows(*ingest.TABLES)
        cursor.fetchone.side_effect = ([(populated,)] if populated else [(False,)] * 8 + [(1,)] * 8)
        return connection, cursor

    def run_with_mock_db(self, connection, *, replace_existing=False):
        with patch.dict(os.environ, {"POSTGRES_PASSWORD": "synthetic-test-password"}, clear=True):
            with patch.object(ingest.psycopg2, "connect", return_value=connection):
                with patch("builtins.print"):
                    ingest.load(self.data_dir, replace_existing=replace_existing)

    def test_preflight_accepts_all_eight_synthetic_files(self):
        result = ingest.preflight(self.data_dir)
        self.assertEqual(set(result), set(ingest.TABLES))
        self.assertTrue(all(item.rows == 1 for item in result.values()))

    def test_preflight_only_cli_never_connects(self):
        with patch.object(ingest.psycopg2, "connect") as connect:
            with patch("builtins.print"):
                ingest.main(["--data-dir", str(self.data_dir), "--preflight-only"])
            connect.assert_not_called()

    def test_missing_csv_fails_before_database_connection(self):
        (self.data_dir / "coupon.csv").unlink()
        with patch.dict(os.environ, {"POSTGRES_PASSWORD": "synthetic-test-password"}, clear=True):
            with patch.object(ingest.psycopg2, "connect") as connect:
                with self.assertRaisesRegex(ValueError, "Missing required CSV files: coupon.csv"):
                    ingest.load(self.data_dir)
                connect.assert_not_called()

    def test_missing_required_column_fails_before_database_connection(self):
        columns = ingest.TABLES["coupon"]
        self.write_csv("coupon", [column for column, _ in columns][:-1], [["1", "1"]])
        with patch.dict(os.environ, {"POSTGRES_PASSWORD": "synthetic-test-password"}, clear=True):
            with patch.object(ingest.psycopg2, "connect") as connect:
                with self.assertRaisesRegex(ValueError, "missing required columns: CAMPAIGN"):
                    ingest.load(self.data_dir)
                connect.assert_not_called()

    def test_duplicate_header_fails_before_database_connection(self):
        columns = ingest.TABLES["coupon"]
        header = [column for column, _ in columns] + ["product_id"]
        self.write_csv("coupon", header, [["1"] * len(header)])
        with patch.dict(os.environ, {"POSTGRES_PASSWORD": "synthetic-test-password"}, clear=True):
            with patch.object(ingest.psycopg2, "connect") as connect:
                with self.assertRaisesRegex(ValueError, "duplicate header columns"):
                    ingest.load(self.data_dir)
                connect.assert_not_called()

    def test_reordered_columns_are_rejected_instead_of_silently_remapped(self):
        columns = ingest.TABLES["coupon"]
        header = [column for column, _ in columns]
        self.write_csv("coupon", header[::-1], [["1"] * len(header)])
        with self.assertRaisesRegex(ValueError, "declared order"):
            ingest.preflight(self.data_dir)

    def test_malformed_row_fails_before_database_connection(self):
        columns = ingest.TABLES["coupon"]
        self.write_csv("coupon", [column for column, _ in columns], [["1", "1"]])
        with patch.dict(os.environ, {"POSTGRES_PASSWORD": "synthetic-test-password"}, clear=True):
            with patch.object(ingest.psycopg2, "connect") as connect:
                with self.assertRaisesRegex(ValueError, "expected 3 fields, found 2"):
                    ingest.load(self.data_dir)
                connect.assert_not_called()

    def test_invalid_numeric_does_not_echo_source_value(self):
        columns = ingest.TABLES["transaction_data"]
        row = self.example_row(columns)
        row[5] = "confidential-invalid-value"
        self.write_csv("transaction_data", [column for column, _ in columns], [row])
        with self.assertRaisesRegex(ValueError, "invalid numeric") as error:
            ingest.preflight(self.data_dir)
        self.assertNotIn("confidential-invalid-value", str(error.exception))

    def test_oversized_integer_does_not_echo_source_value(self):
        columns = ingest.TABLES["coupon"]
        value = "9" * 5000
        self.write_csv("coupon", [column for column, _ in columns], [[value, "1", "1"]])
        with self.assertRaisesRegex(ValueError, "bigint out of range") as error:
            ingest.preflight(self.data_dir)
        self.assertNotIn(value[:100], str(error.exception))

    def test_empty_source_file_is_rejected(self):
        columns = ingest.TABLES["coupon"]
        self.write_csv("coupon", [column for column, _ in columns], [])
        with self.assertRaisesRegex(ValueError, "no data rows"):
            ingest.preflight(self.data_dir)

    def test_malformed_quoted_csv_is_rejected(self):
        (self.data_dir / "coupon.csv").write_text('COUPON_UPC,PRODUCT_ID,CAMPAIGN\n"1,1,1\n', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "malformed CSV near line"):
            ingest.preflight(self.data_dir)

    def test_invalid_configuration_fails_without_connecting(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(ingest.psycopg2, "connect") as connect:
                with self.assertRaisesRegex(ValueError, "password is required"):
                    ingest.load(self.data_dir)
                connect.assert_not_called()
        with patch.dict(os.environ, {"POSTGRES_PASSWORD": "synthetic-test-password", "POSTGRES_PORT": "0"}, clear=True):
            with self.assertRaisesRegex(ValueError, "POSTGRES_PORT"):
                ingest.load(self.data_dir)

    def test_populated_tables_are_protected_by_default(self):
        connection, cursor = self.db_mock(populated=True)
        with self.assertRaisesRegex(ValueError, "use --replace-existing"):
            self.run_with_mock_db(connection)
        sql = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertTrue(any(text.startswith("LOCK TABLE") and "IN SHARE MODE" in text for text in sql))
        self.assertFalse(any(text.startswith(("CREATE", "TRUNCATE", "COPY")) for text in sql))
        cursor.copy_expert.assert_not_called()
        connection.close.assert_called_once()

    def test_incompatible_destination_schema_is_rejected_before_writes(self):
        connection, cursor = self.db_mock()
        cursor.fetchall.return_value = [("coupon", "r", "coupon_upc", "text")]
        with self.assertRaisesRegex(ValueError, "destination columns or types differ"):
            self.run_with_mock_db(connection)
        sql = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertFalse(any(text.startswith(("CREATE", "TRUNCATE")) for text in sql))
        cursor.copy_expert.assert_not_called()

    def test_explicit_column_mapping_without_replacement(self):
        connection, cursor = self.db_mock()
        self.run_with_mock_db(connection)
        self.assertEqual(cursor.copy_expert.call_count, 8)
        statements = [call.args[0] for call in cursor.copy_expert.call_args_list]
        expected = ', '.join('"' + column.lower() + '"' for column, _ in ingest.TABLES["transaction_data"])
        self.assertIn(f'COPY "raw"."transaction_data" ({expected}) FROM STDIN', statements[-1])
        self.assertFalse(any(call.args[0].startswith("TRUNCATE") for call in cursor.execute.call_args_list))
        connection.close.assert_called_once()

    def test_empty_destination_creates_all_eight_tables_without_truncating(self):
        connection, cursor = self.db_mock()
        cursor.fetchall.side_effect = [[], catalog_rows(*ingest.TABLES)]
        cursor.fetchone.side_effect = [(1,)] * 8
        self.run_with_mock_db(connection)
        statements = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertEqual(sum(statement.startswith("CREATE TABLE") for statement in statements), 8)
        self.assertFalse(any(statement.startswith("TRUNCATE") for statement in statements))
        self.assertEqual(cursor.copy_expert.call_count, 8)

    def test_replacement_requires_explicit_opt_in(self):
        connection, cursor = self.db_mock(populated=True)
        cursor.fetchone.side_effect = [(1,)] * 8
        self.run_with_mock_db(connection, replace_existing=True)
        statements = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertTrue(any(
            text.startswith("LOCK TABLE") and "IN ACCESS EXCLUSIVE MODE" in text
            for text in statements
        ))
        self.assertEqual(sum(statement.startswith("TRUNCATE") for statement in statements), 1)
        self.assertEqual(cursor.copy_expert.call_count, 8)

    def test_count_mismatch_aborts_transaction(self):
        connection, cursor = self.db_mock(populated=True)
        cursor.fetchone.side_effect = [(0,)]
        with self.assertRaisesRegex(ValueError, "loaded row count differs"):
            self.run_with_mock_db(connection, replace_existing=True)
        self.assertIs(connection.__exit__.call_args.args[0], ValueError)
        connection.close.assert_called_once()

    def test_copy_failure_propagates_through_transaction_context(self):
        connection, cursor = self.db_mock(populated=True)
        cursor.copy_expert.side_effect = RuntimeError("synthetic COPY error")
        with self.assertRaisesRegex(RuntimeError, "synthetic COPY error"):
            self.run_with_mock_db(connection, replace_existing=True)
        self.assertIs(connection.__exit__.call_args.args[0], RuntimeError)
        connection.close.assert_called_once()

    def test_postgres_copy_error_withholds_source_value(self):
        connection, cursor = self.db_mock(populated=True)
        cursor.copy_expert.side_effect = ingest.psycopg2.DataError("confidential-source-value")
        with self.assertRaisesRegex(RuntimeError, "Row details are withheld") as error:
            self.run_with_mock_db(connection, replace_existing=True)
        self.assertNotIn("confidential-source-value", str(error.exception))
        connection.close.assert_called_once()

    def test_invalid_replace_argument_is_rejected(self):
        with patch.object(ingest.psycopg2, "connect") as connect:
            with self.assertRaisesRegex(ValueError, "must be a boolean"):
                ingest.load(self.data_dir, replace_existing="false")
            connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
