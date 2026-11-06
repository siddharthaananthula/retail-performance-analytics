"""Run isolated, synthetic PostgreSQL ingestion and dbt checks.

This deliberately refuses every connection except the dedicated fixture instance.
Run `init`, `start`, `run`, `dbt`, then `cleanup`.
"""

import argparse
import csv
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import psycopg2
import yaml

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import ingest  # noqa: E402

CI_FIXTURE_ID = os.getenv("RETAIL_FIXTURE_ID", "")
if CI_FIXTURE_ID and not re.fullmatch(r"[0-9]{1,20}a[0-9]{1,4}", CI_FIXTURE_ID):
    raise RuntimeError("Invalid CI fixture ID")
PROJECT = f"retail_ci_{CI_FIXTURE_ID}" if CI_FIXTURE_ID else "retail_p2b"
CONTAINER = f"{PROJECT}_postgres" if CI_FIXTURE_ID else "retail_p2b_postgres"
DATABASE = f"retail_fixture_{CI_FIXTURE_ID}" if CI_FIXTURE_ID else "retail_fixture_2b"
USER = "retail_fixture_user"
HOST = "127.0.0.1"
PORT = 55439
VOLUME = f"{PROJECT}_pgdata" if CI_FIXTURE_ID else "retail_p2b_pgdata"
MAIN_CONTAINER = "retail_postgres"
ENV_FILE = HERE / ".env"


def command(*args, env=None):
    return subprocess.run(args, check=True, capture_output=True, text=True, env=env).stdout.strip()


def fixture_password():
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    values = [line.split("=", 1)[1] for line in lines if line.startswith("FIXTURE_POSTGRES_PASSWORD=")]
    if len(values) != 1 or not values[0]:
        raise RuntimeError("Fixture password file is absent or invalid")
    password = values[0]
    main_env = ROOT / ".env"
    if CI_FIXTURE_ID and main_env.exists():
        raise RuntimeError("CI fixture refuses a root project .env file")
    if main_env.exists():
        for line in main_env.read_text(encoding="utf-8").splitlines():
            if line.startswith("POSTGRES_PASSWORD=") and line.split("=", 1)[1].strip('"\'') == password:
                raise RuntimeError("Fixture password matches the main database password")
    return password


def init():
    if ENV_FILE.exists():
        raise RuntimeError("Fixture password file already exists; review it before continuing")
    if CI_FIXTURE_ID and (ROOT / ".env").exists():
        raise RuntimeError("CI fixture refuses a root project .env file")
    values = {
        "FIXTURE_POSTGRES_PASSWORD": secrets.token_urlsafe(32),
        "FIXTURE_PROJECT": PROJECT,
        "FIXTURE_CONTAINER": CONTAINER,
        "FIXTURE_DATABASE": DATABASE,
        "FIXTURE_PORT": str(PORT),
        "FIXTURE_VOLUME": VOLUME,
    }
    ENV_FILE.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")
    if os.name != "nt":
        ENV_FILE.chmod(0o600)
    fixture_password()
    print("Dedicated, ignored fixture credential created; value withheld")


def inspect(name):
    return json.loads(command("docker", "inspect", name))[0]


def main_metadata():
    names = command("docker", "ps", "-a", "--filter", f"name=^{MAIN_CONTAINER}$", "--format", "{{.Names}}")
    if not names:
        return None
    if names != MAIN_CONTAINER:
        raise RuntimeError("Unexpected main-container name match")
    main = inspect(MAIN_CONTAINER)
    mounts = {m.get("Name") for m in main["Mounts"] if m["Type"] == "volume"}
    ports = main["NetworkSettings"]["Ports"].get("5432/tcp") or []
    if VOLUME in mounts or any(p.get("HostPort") == str(PORT) for p in ports):
        raise RuntimeError("Fixture volume or port collides with the main container")
    return main


def compose_args():
    return ("docker", "compose", "--env-file", str(ENV_FILE), "-f", str(HERE / "compose.yaml"), "-p", PROJECT)


def validated_manifest():
    """Resolve all substitutions before any Compose operation; never print its password."""
    password = fixture_password()
    config = json.loads(command(*compose_args(), "config", "--format", "json"))
    service = config["services"]["postgres"]
    port = service["ports"]
    mounts = service["volumes"]
    environment = service["environment"]
    expected = (
        config["name"] == PROJECT
        and service["container_name"] == CONTAINER
        and service["image"] == "postgres:17"
        and environment["POSTGRES_DB"] == DATABASE
        and environment["POSTGRES_USER"] == USER
        and environment["POSTGRES_PASSWORD"] == password
        and len(port) == 1
        and str(port[0]["published"]) == str(PORT)
        and port[0]["target"] == 5432
        and port[0].get("host_ip") == HOST
        and len(mounts) == 1
        and mounts[0]["source"] == "fixture_pgdata"
        and mounts[0]["target"] == "/var/lib/postgresql/data"
        and config["volumes"]["fixture_pgdata"]["name"] == VOLUME
        and service["healthcheck"]["test"] == ["CMD-SHELL", f"pg_isready -U {USER} -d {DATABASE}"]
    )
    if not expected:
        raise RuntimeError("Compose fixture configuration differs from the isolated manifest")
    return config


def prestart():
    validated_manifest()
    main = main_metadata()
    if main is not None and main["Name"].lstrip("/") == CONTAINER:
        raise RuntimeError("Fixture container name collides with the main container")
    existing = command("docker", "ps", "-a", "--filter", f"name=^{CONTAINER}$", "--format", "{{.Names}}")
    if existing:
        raise RuntimeError("Fixture container already exists; inspect it before starting")
    existing_volume = command("docker", "volume", "ls", "--filter", f"name=^{VOLUME}$", "--format", "{{.Name}}")
    if existing_volume:
        raise RuntimeError("Fixture volume already exists; inspect it before starting")
    with socket.socket() as probe:
        probe.bind((HOST, PORT))
    print(f"Prestart isolation passed: project {PROJECT}, container {CONTAINER}, {HOST}:{PORT}, database {DATABASE}, volume {VOLUME}")
    print("Main container is separate or absent; no database connection or write attempted")


def start():
    prestart()
    command(*compose_args(), "up", "-d", "--wait", "postgres")
    verify()


def expected_config(password):
    return dict(host=HOST, port=PORT, dbname=DATABASE, user=USER, password=password, connect_timeout=10)


def assert_config(config, password):
    if config != expected_config(password):
        raise RuntimeError("Connection configuration is outside the fixture boundary")


def verify():
    validated_manifest()
    password = fixture_password()
    main = main_metadata()
    fixture = inspect(CONTAINER)
    if main is not None and fixture["Id"] == main["Id"]:
        raise RuntimeError("Fixture and main container identities match")
    labels = fixture["Config"].get("Labels") or {}
    if labels.get("com.docker.compose.project") != PROJECT or labels.get("com.docker.compose.service") != "postgres":
        raise RuntimeError("Fixture container lacks expected Compose identity")
    mounts = [m for m in fixture["Mounts"] if m["Type"] == "volume"]
    ports = fixture["NetworkSettings"]["Ports"].get("5432/tcp") or []
    if len(mounts) != 1 or mounts[0]["Name"] != VOLUME or mounts[0]["Destination"] != "/var/lib/postgresql/data":
        raise RuntimeError("Fixture volume identity is wrong")
    if len(ports) != 1 or ports[0]["HostIp"] != HOST or ports[0]["HostPort"] != str(PORT):
        raise RuntimeError("Fixture port mapping is wrong")
    if fixture["State"]["Status"] != "running" or fixture["State"].get("Health", {}).get("Status") != "healthy":
        raise RuntimeError("Fixture PostgreSQL is not healthy")
    config = expected_config(password)
    assert_config(config, password)
    with psycopg2.connect(**config, options="-c default_transaction_read_only=on") as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user, system_identifier::text FROM pg_control_system()")
            db, user, system_id = cursor.fetchone()
    container_id = command(
        "docker", "exec", CONTAINER, "psql", "-U", USER, "-d", DATABASE,
        "-Atc", "SELECT system_identifier::text FROM pg_control_system()",
    )
    if (db, user) != (DATABASE, USER) or system_id != container_id:
        raise RuntimeError("Host connection does not resolve to the dedicated fixture PostgreSQL instance")
    print(f"Fixture verified: container {fixture['Id'][:12]}, database {db}, user {user}, host {HOST}:{PORT}, volume {VOLUME}")
    if main is not None:
        print(f"Main container {main['Id'][:12]} remains distinct; no main database connection opened")
    else:
        print("No main container is present; no main database connection opened")
    return config


def fixture_rows():
    return {
        "campaign_desc": [["Invented Fixture Campaign", 51, 1, 7]],
        "campaign_table": [["Invented Fixture Campaign", 101, 51]],
        "causal_data": [[7001, 31, 1, "0", "A"], [7001, 31, 1, "B", "0"]],
        "coupon": [[8001, 7001, 51]],
        "coupon_redempt": [[101, 1, 8001, 51]],
        "hh_demographic": [["Fixture age", "F", "Fixture income", "F", "F", "F", "F", 101]],
        "product": [[7001, 91, "FIXTURE", "National", "Synthetic", "Example A", "1 unit"],
                    [7002, 92, "FIXTURE", "Private", "Synthetic", "Example B", "1 unit"]],
        "transaction_data": [
            [101, 9001, 1, 7001, 1, "3.25", 31, 0, 1000, 1, 0, 0],
            [101, 9001, 1, 7002, 2, "4.50", 31, 0, 1000, 1, 0, 0],
            [101, 9002, 2, 7001, 1, "3.25", 31, 0, 1100, 1, 0, 0],
        ],
    }


def write_csvs(directory, rows):
    for name, columns in ingest.TABLES.items():
        with (directory / f"{name}.csv").open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([column for column, _ in columns])
            writer.writerows(rows[name])


def snapshot(config):
    result = {}
    with psycopg2.connect(**config, options="-c default_transaction_read_only=on") as connection:
        with connection.cursor() as cursor:
            for name, columns in ingest.TABLES.items():
                selected = ", ".join(ingest._identifier(column) for column, _ in columns)
                cursor.execute(f"SELECT {selected} FROM {ingest._table(name)}")
                rows = sorted(repr(row) for row in cursor.fetchall())
                digest = hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()
                result[name] = (len(rows), digest)
    return result


def guarded_load(directory, *, replace=False):
    config = verify()
    assert_config(ingest._connection_config(), config["password"])
    ingest.load(directory, replace_existing=replace)


def integration():
    config = verify()
    password = config["password"]
    with patch.dict(os.environ, {
        "POSTGRES_HOST": HOST, "POSTGRES_PORT": str(PORT), "POSTGRES_DB": DATABASE,
        "POSTGRES_USER": USER, "POSTGRES_PASSWORD": password,
    }):
        with tempfile.TemporaryDirectory(prefix="retail_p2b_csv_") as temp:
            directory = Path(temp)
            rows = fixture_rows()
            write_csvs(directory, rows)
            print("Test A: fresh eight-table load")
            guarded_load(directory)
            baseline = snapshot(config)
            expected_counts = {name: len(table_rows) for name, table_rows in rows.items()}
            assert {name: count for name, (count, _) in baseline.items()} == expected_counts
            with psycopg2.connect(**config, options="-c default_transaction_read_only=on") as connection:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT "product_id", "manufacturer", "brand" FROM "raw"."product" ORDER BY 1')
                    assert cursor.fetchall() == [(7001, 91, "National"), (7002, 92, "Private")]
                    cursor.execute('SELECT "basket_id", "product_id", "sales_value" FROM "raw"."transaction_data" ORDER BY 1, 2')
                    assert [(a, b, str(c)) for a, b, c in cursor.fetchall()] == [
                        (9001, 7001, "3.25"), (9001, 7002, "4.50"), (9002, 7001, "3.25")]
            print(f"PASS A: counts {expected_counts}; mapped values and committed rows verified")

            print("Test B: default replacement protection")
            try:
                guarded_load(directory)
                raise AssertionError("Default reload unexpectedly succeeded")
            except ValueError as error:
                assert "use --replace-existing" in str(error)
            assert snapshot(config) == baseline
            print("PASS B: reload rejected; eight table checksums unchanged")

            print("Test C: explicit replacement")
            guarded_load(directory, replace=True)
            assert snapshot(config) == baseline
            print("PASS C: explicit replacement committed; counts and checksums match fixture")

            print("Test D: forced late-table COPY failure and rollback")
            changed = {name: [row[:] for row in table_rows] for name, table_rows in rows.items()}
            changed["campaign_desc"][0][0] = "Changed before forced rollback"
            changed["product"][0][0] = 7999
            write_csvs(directory, changed)
            verify()
            with psycopg2.connect(**config) as connection:
                with connection.cursor() as cursor:
                    cursor.execute('ALTER TABLE "raw"."product" ADD CONSTRAINT fixture_forced_failure CHECK ("product_id" <> 7999)')
            try:
                try:
                    guarded_load(directory, replace=True)
                    raise AssertionError("Forced COPY failure unexpectedly succeeded")
                except RuntimeError as error:
                    assert "transaction was rolled back" in str(error)
                assert snapshot(config) == baseline
                print("PASS D: late-table failure rolled back all eight replacements; checksums unchanged")
            finally:
                verify()
                with psycopg2.connect(**config) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute('ALTER TABLE "raw"."product" DROP CONSTRAINT fixture_forced_failure')
            write_csvs(directory, rows)

            print("Test E: invalid configuration and destination schema")
            outside = dict(config, dbname="retail_analytics")
            with patch("psycopg2.connect") as connect:
                try:
                    assert_config(outside, password)
                    raise AssertionError("Outside configuration unexpectedly accepted")
                except RuntimeError as error:
                    assert "outside the fixture boundary" in str(error)
                connect.assert_not_called()
            verify()
            with psycopg2.connect(**config) as connection:
                with connection.cursor() as cursor:
                    cursor.execute('ALTER TABLE "raw"."coupon" ADD COLUMN fixture_schema_mismatch text')
            try:
                try:
                    guarded_load(directory, replace=True)
                    raise AssertionError("Schema mismatch unexpectedly accepted")
                except ValueError as error:
                    assert "destination columns or types differ" in str(error)
                assert snapshot(config) == baseline
            finally:
                verify()
                with psycopg2.connect(**config) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute('ALTER TABLE "raw"."coupon" DROP COLUMN fixture_schema_mismatch')
            assert snapshot(config) == baseline
            print("PASS E: outside configuration refused before connect; schema mismatch refused before replacement")
    print("Integration Tests A-E passed using invented synthetic records only")


def dbt_build():
    verify()
    password = fixture_password()
    profile = yaml.safe_load((HERE / "profiles.yml").read_text(encoding="utf-8"))
    output = profile["retail_analytics"]["outputs"]["fixture"]
    if (profile["retail_analytics"]["target"] != "fixture"
            or output["host"] != HOST
            or output["port"] != "{{ env_var('FIXTURE_PORT', '55439') | int }}"
            or output["dbname"] != "{{ env_var('FIXTURE_DATABASE', 'retail_fixture_2b') }}"
            or output["user"] != USER
            or output["schema"] != "fixture_analytics"
            or output["password"] != "{{ env_var('FIXTURE_POSTGRES_PASSWORD') }}"):
        raise RuntimeError("dbt profile is outside the fixture boundary")
    dbt = Path(os.environ.get("DBT_EXE") or shutil.which("dbt") or (Path(sys.executable).parent / "dbt.exe"))
    if not dbt.is_file():
        raise RuntimeError("Set DBT_EXE to your existing dbt executable or activate its environment")
    env = os.environ.copy()
    env["FIXTURE_POSTGRES_PASSWORD"] = password
    env["FIXTURE_PORT"] = str(PORT)
    env["FIXTURE_DATABASE"] = DATABASE
    with tempfile.TemporaryDirectory(prefix="retail_p2b_dbt_") as temp:
        profile_dir = Path(temp) / "profiles"
        profile_dir.mkdir()
        shutil.copyfile(HERE / "profiles.yml", profile_dir / "profiles.yml")
        args = [str(dbt), "build", "--project-dir", str(ROOT / "dbt"),
                "--profiles-dir", str(profile_dir), "--target", "fixture",
                "--target-path", str(Path(temp) / "target"), "--log-path", str(Path(temp) / "logs")]
        result = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True)
        artifact = Path(temp) / "target" / "run_results.json"
        by_type = None
        if artifact.exists():
            data = json.loads(artifact.read_text(encoding="utf-8"))
            by_type = {}
            for item in data["results"]:
                kind = item["unique_id"].split(".", 1)[0]
                by_type.setdefault(kind, {}).setdefault(item["status"], 0)
                by_type[kind][item["status"]] += 1
            print("dbt result counts:", json.dumps(by_type, sort_keys=True))
            failures = [(r["unique_id"], r["status"], r.get("message", "")) for r in data["results"]
                        if r["status"] not in ("success", "pass")]
            for unique_id, status, message in failures:
                print(f"{unique_id}: {status}: {message[:350].replace(password, '[REDACTED]')}")
        print("dbt exit code:", result.returncode)
        if result.returncode:
            tail = "\n".join((result.stdout + result.stderr).splitlines()[-35:])
            print("dbt diagnostic tail:\n", tail.replace(password, "[REDACTED]"))
            raise RuntimeError("Fixture dbt build failed")
        if by_type != {"model": {"success": 20}, "test": {"pass": 73}}:
            raise RuntimeError("Fixture dbt build did not produce exactly 20 successful models and 73 passing tests")
        logs = subprocess.run(["docker", "logs", CONTAINER], capture_output=True, text=True, check=True)
        if re.search(r"server process \(PID [0-9]+\) exited with exit code [1-9]", logs.stdout + logs.stderr):
            raise RuntimeError("Fixture PostgreSQL server process exited during validation; review diagnostics")


def project_resources():
    """Check resource ownership without needing a healthy database connection."""
    main = main_metadata()
    containers = command("docker", "ps", "-a", "--filter", f"label=com.docker.compose.project={PROJECT}",
                         "--format", "{{.Names}}").splitlines()
    volumes = command("docker", "volume", "ls", "--filter", f"label=com.docker.compose.project={PROJECT}",
                      "--format", "{{.Name}}").splitlines()
    networks = command("docker", "network", "ls", "--filter", f"label=com.docker.compose.project={PROJECT}",
                       "--format", "{{.Name}}").splitlines()
    if set(containers) - {CONTAINER} or set(volumes) - {VOLUME} or set(networks) - {f"{PROJECT}_default"}:
        raise RuntimeError("Unexpected resource belongs to fixture Compose project")
    named_container = command("docker", "ps", "-a", "--filter", f"name=^{CONTAINER}$", "--format", "{{.Names}}")
    named_volume = command("docker", "volume", "ls", "--filter", f"name=^{VOLUME}$", "--format", "{{.Name}}")
    if bool(named_container) != (CONTAINER in containers) or bool(named_volume) != (VOLUME in volumes):
        raise RuntimeError("Fixture resource name exists without expected Compose ownership")
    if CONTAINER in containers:
        fixture = inspect(CONTAINER)
        labels = fixture["Config"].get("Labels") or {}
        mounts = [m for m in fixture["Mounts"] if m["Type"] == "volume"]
        ports = (fixture.get("NetworkSettings", {}).get("Ports") or {}).get("5432/tcp") or []
        if (labels.get("com.docker.compose.project") != PROJECT
                or labels.get("com.docker.compose.service") != "postgres"
                or (main is not None and fixture["Id"] == main["Id"])
                or len(mounts) != 1 or mounts[0]["Name"] != VOLUME
                or mounts[0]["Destination"] != "/var/lib/postgresql/data"
                or (ports and (len(ports) != 1 or ports[0]["HostIp"] != HOST
                               or ports[0]["HostPort"] != str(PORT)))):
            raise RuntimeError("Fixture container identity is not safe for cleanup")
    if VOLUME in volumes:
        volume = json.loads(command("docker", "volume", "inspect", VOLUME))[0]
        labels = volume.get("Labels") or {}
        if volume["Name"] != VOLUME or labels.get("com.docker.compose.project") != PROJECT:
            raise RuntimeError("Fixture volume identity is not safe for cleanup")
    return containers, volumes, networks


def diagnostics():
    """Show bounded fixture-only logs on failure, with the generated password redacted."""
    if not ENV_FILE.exists():
        print("No fixture credential file; no fixture diagnostics available")
        return
    validated_manifest()
    containers, _, _ = project_resources()
    if CONTAINER not in containers:
        print("Fixture container was not created; no PostgreSQL logs available")
        return
    state = inspect(CONTAINER)["State"]
    print(f"Fixture status={state['Status']} health={state.get('Health', {}).get('Status', 'unknown')} "
          f"oom_killed={state.get('OOMKilled', False)} exit_code={state.get('ExitCode', 'unknown')}")
    result = subprocess.run(["docker", "logs", "--tail", "150", CONTAINER],
                            capture_output=True, text=True, check=False)
    logs = (result.stdout + result.stderr).replace(fixture_password(), "[REDACTED]")
    print("Fixture PostgreSQL log tail:\n" + logs)


def cleanup():
    """Remove only resources with verified fixture Compose ownership, even if PostgreSQL failed."""
    if not ENV_FILE.exists():
        containers, volumes, networks = project_resources()
        if containers or volumes or networks:
            raise RuntimeError("Fixture resources exist but credential file is missing; refusing cleanup")
        print("No fixture resources to clean up")
        return
    validated_manifest()
    project_resources()
    command(*compose_args(), "down", "-v")
    if any(project_resources()):
        raise RuntimeError("Fixture resources remain after cleanup")
    if CI_FIXTURE_ID:
        ENV_FILE.unlink()
    print(f"Removed only fixture project {PROJECT} and volume {VOLUME}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init", "prestart", "start", "verify", "run", "dbt", "diagnostics", "cleanup"])
    action = parser.parse_args().action
    {"init": init, "prestart": prestart, "start": start, "verify": verify,
     "run": integration, "dbt": dbt_build, "diagnostics": diagnostics,
     "cleanup": cleanup}[action]()


if __name__ == "__main__":
    main()
