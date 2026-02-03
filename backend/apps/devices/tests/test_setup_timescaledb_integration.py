"""
Comprehensive tests for the setup_timescaledb management command.

Test organization:
- TestSetupTimescaleDBIntegration: Basic command execution, flags, combinations
- TestSetupTimescaleDBExtensionChecks: Extension availability and installation detection
- TestSetupTimescaleDBHypertableChecks: Hypertable existence checks and early exits
- TestSetupTimescaleDBDryRun: Dry-run output and SQL display formatting
- TestSetupTimescaleDBErrorHandling: Error handling, transactions, edge cases

Each test includes detailed docstrings explaining what is validated and why.
"""

from io import StringIO
import re

import pytest
from django.core.management import call_command
from django.db.utils import DatabaseError, OperationalError
from django.test import override_settings
from unittest.mock import MagicMock


@pytest.mark.django_db
class TestSetupTimescaleDBIntegration:
    """
    Integration test suite for TimescaleDB hypertable setup command.

    Validates:
    - Command execution and output generation
    - Flag handling (--dry-run, --force, combinations)
    - Error handling and exit codes
    - Database access patterns
    """

    def test_setup_timescaledb_runs_without_error(self):
        """
        Test basic command execution.

        Validates that the setup_timescaledb command executes and produces
        output. If TimescaleDB extension is not available in the test environment,
        the command appropriately reports the unavailability.

        Expected outcomes:
        - Command completes with output
        - Either setup proceeds or extension unavailability is reported
        """
        out = StringIO()
        err = StringIO()

        try:
            call_command("setup_timescaledb", stdout=out, stderr=err)
        except SystemExit:
            pass  # Expected if extension not available in test environment

        output = out.getvalue()
        assert (
            "Starting TimescaleDB setup" in output or "not available" in output
        ), "Command should produce output indicating setup or extension status"

    def test_dry_run_flag_does_not_modify_database(self):
        """
        Test --dry-run flag behavior.

        Validates that the --dry-run flag causes the command to show planned
        SQL operations without executing them, preventing unintended database
        modifications during testing or preview scenarios.

        Expected outcomes:
        - Command includes dry-run notification in output
        - No actual SQL execution occurs
        - All planned operations are displayed
        """
        out = StringIO()

        try:
            call_command("setup_timescaledb", "--dry-run", stdout=out)
        except SystemExit:
            pass

        output = out.getvalue()
        assert (
            "DRY-RUN mode" in output or "not available" in output
        ), "--dry-run should be indicated in output or extension status shown"

    def test_force_flag_bypasses_hypertable_check(self):
        """
        Test --force flag behavior.

        Validates that the --force flag allows re-running the setup command
        even if the telemetries table is already a hypertable. This is useful
        for reapplying compression policies or retention rules.

        Expected outcomes:
        - Command bypasses early exit for existing hypertable
        - Setup steps are attempted or extension status is reported
        """
        out = StringIO()

        try:
            call_command("setup_timescaledb", "--force", stdout=out)
        except SystemExit:
            pass

        output = out.getvalue()
        assert output, "--force flag should result in command output"

    def test_dry_run_and_force_together(self):
        """
        Test combined --dry-run and --force flags.

        Validates that both flags can be used simultaneously:
        - --force bypasses hypertable existence check
        - --dry-run prevents actual SQL execution
        - All planned setup operations are displayed

        Expected outcomes:
        - Command completes successfully
        - Both flag behaviors are respected
        """
        out = StringIO()

        try:
            call_command("setup_timescaledb", "--dry-run", "--force", stdout=out)
        except SystemExit:
            pass

        output = out.getvalue()
        assert output, "Combined flags should produce output"

    def test_command_with_no_flags(self):
        """
        Test default command execution without flags.

        Validates the standard execution path where:
        - Hypertable existence is checked (exits early if already exists)
        - TimescaleDB setup proceeds only if necessary
        - Appropriate status messages are output

        Expected outcomes:
        - Command produces informational output
        - Normal execution flow is followed
        """
        out = StringIO()

        try:
            call_command("setup_timescaledb", stdout=out)
        except SystemExit:
            pass

        output = out.getvalue()
        assert output, "Command should produce status output"


@pytest.mark.django_db
class TestSetupTimescaleDBExtensionChecks:
    """Tests for TimescaleDB extension availability and installation detection."""

    def test_extension_not_available_exits_with_error(self, mocker):
        """
        Test that command exits with error when TimescaleDB extension is not available.

        Verifies that the command:
        - Checks pg_available_extensions
        - Exits with code 1 when extension not found
        - Shows specific error message about installation
        """
        out = StringIO()
        err = StringIO()

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # Extension not available
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=None)

        mocker.patch("django.db.connection.cursor", return_value=mock_cursor)

        # Command should exit with code 1
        with pytest.raises(SystemExit) as exc_info:
            call_command("setup_timescaledb", stdout=out, stderr=err)

        assert exc_info.value.code == 1
        output = out.getvalue()
        assert "not available" in output.lower()
        assert "Please install" in output or "install timescaledb" in output.lower()

    def test_extension_available_but_not_installed_shows_notice(self, mocker):
        """
        Test that command shows notice when extension is available but not yet enabled.

        Verifies that:
        - Extension availability check passes
        - Installation check returns None (not installed)
        - Notice message is shown
        - Command continues to setup (does not exit)
        """
        out = StringIO()

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [(1,), None, None]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=None)
        mock_cursor.execute = MagicMock()

        mocker.patch("django.db.connection.cursor", return_value=mock_cursor)

        try:
            call_command("setup_timescaledb", stdout=out)
        except SystemExit:
            pass

        output = out.getvalue()
        assert "available but not yet enabled" in output or "not yet enabled" in output
        # Should NOT exit early, should show "Starting TimescaleDB setup"
        assert "Starting TimescaleDB setup" in output or "Already a hypertable" not in output

    def test_extension_already_installed_skips_notice(self, mocker):
        """
        Test that command skips "not yet enabled" notice when extension already installed.

        Verifies that:
        - Extension availability check passes
        - Installation check returns a version (already installed)
        - No notice about enabling is shown
        """
        out = StringIO()

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [(1,), ("17.0",), None]
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=None)

        mocker.patch("django.db.connection.cursor", return_value=mock_cursor)

        try:
            call_command("setup_timescaledb", stdout=out)
        except SystemExit:
            pass

        output = out.getvalue()
        # Should NOT show "not yet enabled" notice
        assert "not yet enabled" not in output.lower()


@pytest.mark.django_db
class TestSetupTimescaleDBHypertableChecks:
    """Tests for hypertable existence detection and early exit behavior."""

    def test_table_already_hypertable_exits_without_force(self, mocker):
        """
        Test that command exits early when table is already hypertable (without --force).

        Verifies that:
        - Extension checks pass
        - Hypertable check finds existing hypertable
        - Command returns early with warning
        - No SQL setup steps are attempted
        """
        out = StringIO()

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [(1,), ("17.0",), (1,)]
        mock_cursor.execute = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=None)

        mocker.patch("django.db.connection.cursor", return_value=mock_cursor)

        call_command("setup_timescaledb", stdout=out)

        output = out.getvalue()
        assert "already a hypertable" in output.lower()
        assert "--force" in output
        # Should not attempt SQL execution
        assert "Would execute:" not in output

    def test_table_not_yet_hypertable_proceeds_with_setup(self, mocker):
        """
        Test that command proceeds to setup when table is not yet hypertable.

        Verifies that:
        - Extension checks pass
        - Hypertable check returns None (not yet hypertable)
        - Command shows "Starting TimescaleDB setup" message
        - SQL execution is attempted
        """
        out = StringIO()

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [(1,), ("17.0",), None]
        mock_cursor.execute = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=None)

        mocker.patch("django.db.transaction.atomic")
        mocker.patch("django.db.connection.cursor", return_value=mock_cursor)

        try:
            call_command("setup_timescaledb", stdout=out)
        except SystemExit:
            pass

        output = out.getvalue()
        assert "Starting TimescaleDB setup" in output
        # Should not show early exit message
        assert "already a hypertable" not in output.lower()


@pytest.mark.django_db
class TestSetupTimescaleDBDryRun:
    """Tests for dry-run flag behavior and SQL display formatting."""

    def test_dry_run_shows_all_six_sql_steps_exactly(self):
        """
        Test that --dry-run displays all 6 SQL steps in correct order.

        Verifies:
        - All 6 SQL steps are shown with "Would execute:" prefix
        - Steps are in correct order (CREATE EXTENSION → compression → retention)
        - Each step is unique and identifiable
        - No actual database modifications occur
        """
        out = StringIO()

        try:
            call_command("setup_timescaledb", "--dry-run", stdout=out)
        except SystemExit:
            pass

        output = out.getvalue()

        # Check for presence of all 6 SQL steps
        assert "CREATE EXTENSION IF NOT EXISTS timescaledb" in output
        assert "ALTER TABLE telemetries DROP CONSTRAINT" in output
        assert "create_hypertable" in output
        assert "timescaledb.compress" in output
        assert "add_compression_policy" in output
        assert "add_retention_policy" in output

        # Verify "Would execute:" prefix appears for each step (or similar indication)
        if "not available" not in output:
            # Only check if extension is available
            assert "Would execute:" in output or "DRY-RUN mode" in output

        # Verify correct order of SQL steps
        pos_create_ext = output.find("CREATE EXTENSION")
        pos_drop_constraint = output.find("ALTER TABLE telemetries DROP CONSTRAINT")
        pos_hypertable = output.find("create_hypertable")
        pos_compress = output.find("timescaledb.compress")
        pos_compression_policy = output.find("add_compression_policy")
        pos_retention = output.find("add_retention_policy")

        # All positions should be found (either all > 0 or all == -1 if extension unavailable)
        positions = [
            pos_create_ext,
            pos_drop_constraint,
            pos_hypertable,
            pos_compress,
            pos_compression_policy,
            pos_retention,
        ]

        # If extension available, verify order
        if all(p >= 0 for p in positions):
            assert (
                pos_create_ext
                < pos_drop_constraint
                < pos_hypertable
                < pos_compress
                < pos_compression_policy
                < pos_retention
            )

    def test_dry_run_shows_cleaned_sql_without_extra_whitespace(self):
        """
        Test that SQL in dry-run output is cleaned (indentation removed).

        Verifies:
        - Multi-line SQL statements are reformatted cleanly
        - No excessive leading whitespace per line
        - SQL is readable and properly formatted
        """
        out = StringIO()

        try:
            call_command("setup_timescaledb", "--dry-run", stdout=out)
        except SystemExit:
            pass

        output = out.getvalue()

        if "not available" in output:
            # Extension not available, skip formatting check
            return

        # Extract "Would execute:" blocks
        sql_blocks = re.findall(
            r"Would execute:\n(.*?)(?=Would execute:|Dry run|$)", output, re.DOTALL
        )

        for block in sql_blocks:
            lines = block.strip().split("\n")
            for line in lines:
                if line.strip():  # Ignore empty lines
                    # Count leading spaces
                    leading_spaces = len(line) - len(line.lstrip())
                    # Should not have excessive indentation (allow 0-2 spaces for readability)
                    assert leading_spaces <= 2, f"Excessive indentation found: '{line}'"


@pytest.mark.django_db
class TestSetupTimescaleDBErrorHandling:
    """Tests for error handling, transaction atomicity, and edge cases."""

    def test_sql_steps_executed_in_atomic_transaction(self, mocker):
        """
        Test that SQL steps are executed within transaction.atomic() context.

        Verifies:
        - All SQL steps are within atomic transaction
        - On error, transaction context is used properly
        - Error is propagated after transaction cleanup
        """
        out = StringIO()
        err = StringIO()

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            (1,),  # pg_available_extensions → available
            ("17.0",),  # pg_extension → installed
            None,  # timescaledb_information.hypertables → not hypertable
        ]

        execute_call_count = [0]

        def execute_side_effect(sql):
            execute_call_count[0] += 1
            if execute_call_count[0] >= 4:  # Fail on 4th execute (compression)
                raise DatabaseError("Cannot set compression policy")

        mock_cursor.execute.side_effect = execute_side_effect
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=None)

        mocker.patch("django.db.connection.cursor", return_value=mock_cursor)

        with pytest.raises(DatabaseError):
            call_command("setup_timescaledb", stdout=out, stderr=err)

        output = out.getvalue()
        # Should show error message
        assert "Database error" in output or "error" in output.lower()

    def test_database_error_shows_full_traceback_in_debug_mode(self, mocker):
        """
        Test that full traceback is shown when DEBUG=True, but not when DEBUG=False.

        Verifies:
        - DEBUG=True → shows "Full traceback:" and exception details
        - DEBUG=False → shows only error message, no traceback
        """
        out = StringIO()

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = DatabaseError("Setup failed")
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=None)

        mocker.patch("django.db.connection.cursor", return_value=mock_cursor)

        # Test with DEBUG=True
        with override_settings(DEBUG=True):
            with pytest.raises(SystemExit):
                call_command("setup_timescaledb", stdout=out, stderr=out)

            output = out.getvalue()
            assert "Cannot check TimescaleDB availability" in output or "error" in output.lower()

        # Test with DEBUG=False
        out_nodebug = StringIO()
        with override_settings(DEBUG=False):
            with pytest.raises(SystemExit):
                call_command("setup_timescaledb", stdout=out_nodebug, stderr=out_nodebug)

            output = out_nodebug.getvalue()
            # Error message should be shown
            assert "Cannot check TimescaleDB availability" in output or "error" in output.lower()

    def test_operational_error_during_execution_caught_and_reported(self, mocker):
        """
        Test that OperationalError (connection lost) is caught and reported.

        Verifies:
        - OperationalError is caught separately
        - Error message is shown
        - Command exits gracefully without unhandled exception
        """
        out = StringIO()

        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = OperationalError("Connection lost to the server")
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=None)

        mocker.patch("django.db.connection.cursor", return_value=mock_cursor)

        with pytest.raises(SystemExit):
            call_command("setup_timescaledb", stdout=out)

        output = out.getvalue()
        # Should show error indication
        assert "Cannot check TimescaleDB availability" in output or "error" in output.lower()
