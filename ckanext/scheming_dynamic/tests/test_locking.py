from __future__ import annotations

import sqlalchemy as sa
import pytest

from ckan import model

from ckanext.scheming_dynamic.utils import lock_schema, lock_schema_shared


@pytest.mark.ckan_config("ckan.plugins", "scheming_datasets scheming_dynamic")
@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestLockSchema:
    """The per-schema-type advisory locks that serialise schema writes
    against each other and against pin creation.

    A real cross-transaction race needs two connections and is left to
    manual/load testing; here we just prove the locks are actually acquired
    (not a silent no-op or a SQL error) and keyed per type.
    """

    def _held_advisory_locks(self) -> int:
        return model.Session.execute(
            sa.text(
                "SELECT count(*) FROM pg_locks "
                "WHERE locktype = 'advisory' AND pid = pg_backend_pid()"
            )
        ).scalar()

    def test_exclusive_lock_is_acquired(self):
        before = self._held_advisory_locks()
        lock_schema("dataset", "test-type")
        assert self._held_advisory_locks() == before + 1

    def test_shared_lock_is_acquired(self):
        before = self._held_advisory_locks()
        lock_schema_shared("dataset", "test-type")
        assert self._held_advisory_locks() == before + 1

    def test_distinct_schema_types_take_distinct_locks(self):
        lock_schema("dataset", "a")
        after_first = self._held_advisory_locks()
        lock_schema("dataset", "b")
        assert self._held_advisory_locks() == after_first + 1

    def test_reentrant_within_a_transaction(self):
        # transaction-level advisory locks don't stack: re-acquiring in the
        # same transaction must not block or error
        lock_schema("dataset", "a")
        lock_schema("dataset", "a")
        lock_schema_shared("dataset", "a")
