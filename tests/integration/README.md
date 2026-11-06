# Isolated PostgreSQL fixture check

This harness uses invented CSV rows and a dedicated Docker Compose project. It does not load the original dataset. The `run` action tests fresh loading, default replacement protection, explicit replacement, transaction rollback, and invalid destination/configuration handling. The `dbt` action builds the existing models and runs their tests against this small fixture; it does not establish full-dataset performance or business totals.

From the repository root in PowerShell, with Docker Desktop running and the existing project dbt environment activated (`python` and `dbt` on `PATH`):

```powershell
python tests/integration/run_fixture.py init
python tests/integration/run_fixture.py start
python tests/integration/run_fixture.py run
python tests/integration/run_fixture.py dbt
python tests/integration/run_fixture.py cleanup
```

The ignored `tests/integration/.env` contains a generated fixture-only password and fixture identifiers; never print or commit it. `start` runs `prestart` before Compose can create resources, then runs `verify` after PostgreSQL is healthy. `prestart` validates the resolved Compose manifest, checks the main container if one exists through Docker metadata without connecting to its database, and checks the fixture port and volume are unused. `verify` checks the running container's Compose labels, host port and volume, then compares the PostgreSQL system ID obtained through the host connection with the ID obtained inside the fixture container. Every loader call and the dbt call invoke that check first. A mismatch stops the harness before it writes.

The local fixture uses project `retail_p2b`, container `retail_p2b_postgres`, database `retail_fixture_2b`, loopback port `55439` and volume `retail_p2b_pgdata`. The `cleanup` action checks Compose ownership before running `down -v` for this project only; it does not require a healthy database. The ignored password file remains after local cleanup; remove that one local file if it is no longer needed. To repeat the check, remove the old fixture password file, run `init`, and proceed from `start`.

If `dbt` is not on `PATH`, set `DBT_EXE` to the existing environment's dbt executable before the `dbt` action. No dependency installation is performed by this harness.

The fresh database must be empty when `run` starts. The eight fixture CSVs are generated under a temporary directory and discarded after the checks. The harness reads only the main container's Docker metadata and local password file to rule out reuse; it never opens a main-database connection. A different local environment requires updating the fixed fixture identifiers and reviewing the isolation checks before use.

## GitHub Actions

The [synthetic pipeline workflow](../../.github/workflows/dbt-quality.yml) runs on pushes, pull requests and manual dispatch. On each job attempt, `RETAIL_FIXTURE_ID` uses GitHub's run ID and attempt number. The runner derives a distinct Compose project, container, database and volume from that ID. It generates a new password in an ignored local file; the workflow has no database secret or original CSV dependency. It runs the 21 loader unit tests, then `init`, `start`, Tests A–E and `dbt build`. The dbt action requires exactly 20 successful models and 73 passing tests. Repository token access is limited to reading contents.

On failure, the workflow prints a bounded tail of **fixture-only** PostgreSQL logs with the generated password redacted. An `always()` cleanup step checks Compose ownership and removes only fixture resources, even if PostgreSQL is unhealthy; it refuses to remove resources whose identity cannot be verified. The CI password file is removed after successful cleanup. The workflow does not use the project's root `.env`, main Compose file, raw CSVs or populated database.

The Phase 2B local fixture build passed 20 models and 73 tests, but one intermediate attempt saw a PostgreSQL server process exit and four tests error during recovery. A single later retry passed. The cause was not established. CI runs the build once, checks the fixture PostgreSQL log for a server-process exit even when dbt passes, and reports any failure; it has no automatic retry loop. **GitHub-hosted execution of this workflow has not yet been observed.**
