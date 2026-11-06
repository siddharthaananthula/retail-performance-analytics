"""Offline checks for CI fixture identity, cleanup and diagnostic boundaries."""

import contextlib
import io
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.integration import run_fixture as fixture


class FixtureCiTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("docker"), "Docker Compose CLI is unavailable")
    def test_dynamic_compose_manifest_without_starting_database(self):
        with tempfile.TemporaryDirectory() as temp:
            credential = Path(temp) / ".env"
            password = secrets.token_urlsafe(24)
            credential.write_text(
                "FIXTURE_POSTGRES_PASSWORD=" + password + "\n"
                "FIXTURE_PROJECT=retail_ci_12345a2\n"
                "FIXTURE_CONTAINER=retail_ci_12345a2_postgres\n"
                "FIXTURE_DATABASE=retail_fixture_12345a2\n"
                "FIXTURE_PORT=55439\n"
                "FIXTURE_VOLUME=retail_ci_12345a2_pgdata\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                ["docker", "compose", "--env-file", str(credential),
                 "-f", str(fixture.HERE / "compose.yaml"), "-p", "retail_ci_12345a2",
                 "config", "--format", "json"],
                capture_output=True, text=True, check=True,
            )
            config = json.loads(result.stdout)
            service = config["services"]["postgres"]
            self.assertEqual(config["name"], "retail_ci_12345a2")
            self.assertEqual(service["container_name"], "retail_ci_12345a2_postgres")
            self.assertEqual(service["environment"]["POSTGRES_DB"], "retail_fixture_12345a2")
            self.assertEqual(config["volumes"]["fixture_pgdata"]["name"], "retail_ci_12345a2_pgdata")
            self.assertEqual(str(service["ports"][0]["published"]), "55439")
            self.assertEqual(service["environment"]["POSTGRES_PASSWORD"], password)

    def test_ci_run_id_creates_distinct_resource_names(self):
        env = dict(os.environ, RETAIL_FIXTURE_ID="12345a2")
        result = subprocess.run(
            [sys.executable, "-c", "from tests.integration import run_fixture as f; "
             "print(f.PROJECT, f.CONTAINER, f.DATABASE, f.VOLUME)"],
            env=env, capture_output=True, text=True, check=True,
        )
        self.assertEqual(
            result.stdout.strip(),
            "retail_ci_12345a2 retail_ci_12345a2_postgres "
            "retail_fixture_12345a2 retail_ci_12345a2_pgdata",
        )

    def test_invalid_ci_id_is_rejected_before_docker(self):
        env = dict(os.environ, RETAIL_FIXTURE_ID="../retail_postgres")
        result = subprocess.run(
            [sys.executable, "-c", "from tests.integration import run_fixture"],
            env=env, capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid CI fixture ID", result.stderr)

    def test_cleanup_checks_ownership_without_database_health(self):
        with tempfile.TemporaryDirectory() as temp:
            credential = Path(temp) / ".env"
            credential.write_text("FIXTURE_POSTGRES_PASSWORD=" + secrets.token_urlsafe(24) + "\n", encoding="utf-8")
            with patch.object(fixture, "ENV_FILE", credential), \
                 patch.object(fixture, "CI_FIXTURE_ID", "12345a2"), \
                 patch.object(fixture, "validated_manifest"), \
                 patch.object(fixture, "project_resources", side_effect=[(["owned"], ["owned"], []), ([], [], [])]) as resources, \
                 patch.object(fixture, "command", return_value="") as command:
                fixture.cleanup()
                self.assertEqual(resources.call_count, 2)
                command.assert_called_once_with(*fixture.compose_args(), "down", "-v")
            self.assertFalse(credential.exists())

    def test_cleanup_refuses_unverified_resources(self):
        with tempfile.TemporaryDirectory() as temp:
            credential = Path(temp) / ".env"
            credential.write_text("FIXTURE_POSTGRES_PASSWORD=" + secrets.token_urlsafe(24) + "\n", encoding="utf-8")
            with patch.object(fixture, "ENV_FILE", credential), \
                 patch.object(fixture, "validated_manifest"), \
                 patch.object(fixture, "project_resources", side_effect=RuntimeError("wrong owner")), \
                 patch.object(fixture, "command") as command:
                with self.assertRaisesRegex(RuntimeError, "wrong owner"):
                    fixture.cleanup()
                command.assert_not_called()
            self.assertTrue(credential.exists())

    def test_diagnostics_redact_fixture_password(self):
        output = io.StringIO()
        password = secrets.token_urlsafe(24)
        completed = subprocess.CompletedProcess([], 0, "", password + " appeared in a synthetic log")
        with patch.object(fixture, "ENV_FILE") as credential, \
             patch.object(fixture, "validated_manifest"), \
             patch.object(fixture, "project_resources", return_value=([fixture.CONTAINER], [], [])), \
             patch.object(fixture, "inspect", return_value={"State": {"Status": "exited", "ExitCode": 2}}), \
             patch.object(fixture, "fixture_password", return_value=password), \
             patch.object(fixture.subprocess, "run", return_value=completed), \
             contextlib.redirect_stdout(output):
            credential.exists.return_value = True
            fixture.diagnostics()
        self.assertIn("[REDACTED]", output.getvalue())
        self.assertNotIn(password, output.getvalue())


if __name__ == "__main__":
    unittest.main()
