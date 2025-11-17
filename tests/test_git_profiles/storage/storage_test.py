# SPDX-License-Identifier: Apache-2.0
#
# Copyright 2025 Niklas Kaaf
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import tempfile
from collections.abc import Generator, Sequence
from pathlib import Path
from typing import Any

import filelock
import pytest

from git_profiles.storage import (
    ConfigLoadError,
    DictMergeConflictError,
    Storage,
    StorageError,
    StorageFileLockError,
)
from test_git_profiles.common_helpers_test import ENCODING, assert_str_in_str


@pytest.fixture
def storage() -> Generator[Storage, None, None]:
    with (
        tempfile.NamedTemporaryFile('r+', delete=True, encoding=ENCODING) as temp_file,
        Storage(Path(temp_file.name)) as storage,
    ):
        yield storage


def test_storage_create_dir() -> None:
    dir_name = 'Test'
    with tempfile.TemporaryDirectory() as tmp_dir:
        Storage(Path(tmp_dir) / dir_name / 'config.json')
        assert (Path(tmp_dir) / dir_name).is_dir()


def test_file_lock_contextmanager() -> None:
    lock_file_path = None
    with (
        tempfile.NamedTemporaryFile('r+', delete=True) as temp_file,
        Storage(Path(temp_file.name)) as storage,
    ):
        lock_file_path = storage.config_file.absolute().with_suffix('.lock')
        assert lock_file_path.is_file()

    assert not lock_file_path.is_file()


def test_file_lock_variable() -> None:
    lock_file_path = None
    with (
        tempfile.NamedTemporaryFile('r+', delete=True) as temp_file,
    ):
        storage = Storage(Path(temp_file.name))
        lock_file_path = storage.config_file.absolute().with_suffix('.lock')

        class Counter:
            COUNTER = 0

            @classmethod
            def counter(cls) -> int:
                return cls.COUNTER

            @classmethod
            def inc(cls) -> None:
                cls.COUNTER += 1

        # Mock acquire function to check if it was called and the lockfile exists
        filelock.FileLock.acquire_original = filelock.FileLock.acquire

        def mock_acquire(*args: Sequence[...], **kwargs: dict[str, Any]) -> None:
            Counter.inc()
            filelock.FileLock.acquire_original(*args, **kwargs)
            assert lock_file_path.is_file()

        filelock.FileLock.acquire = mock_acquire

        # The operation that triggers a locking
        _config = storage.config

        assert Counter.counter() != 0

    assert not lock_file_path.is_file()

    filelock.FileLock.acquire = filelock.FileLock.acquire_original
    del filelock.FileLock.acquire_original


def test_file_lock_timeout() -> None:
    with (
        tempfile.NamedTemporaryFile('r+', delete=True) as temp_file,
        Storage(Path(temp_file.name)) as _storage,
    ):
        # File lock is acquired, due to context manager

        storage_2 = Storage(Path(temp_file.name))

        with pytest.raises(StorageFileLockError) as exc:
            _config = storage_2.config

        assert_str_in_str(str(exc.value), words_norm=['instance', 'current', 'run'])


def test_atomic_save(storage: Storage) -> None:
    storage.set('p', 'user.name', 'Alice')

    config_dir = storage.config_file.parent
    before = set(config_dir.iterdir())

    storage.set('p', 'user.email', 'alice@example.com')

    after = set(config_dir.iterdir())

    new_files = after - before
    assert storage.config_file in new_files or new_files == set()

    data = json.loads(storage.config_file.read_text())
    assert data['p']['user.name'] == 'Alice'
    assert data['p']['user.email'] == 'alice@example.com'


def test_load_non_existing_config() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / 'does_not_exist.json'
        storage = Storage(config_path)

        assert storage.config == {}


def test_load_invalid_profile_value() -> None:
    profile = 'profile'
    key = 'user.email'
    value = 'invalid'

    with tempfile.NamedTemporaryFile('w+', delete=False) as f:
        path = Path(f.name)
        json.dump({profile: {key: value}}, f)

    with pytest.raises(ConfigLoadError) as exc, Storage(path):
        """ This 'with' context is required to trigger the load (or an other config
        manipulating operation)"""

    path.unlink()

    assert_str_in_str(
        str(exc.value),
        words_exact=[profile, key, value],
        words_norm=['invalid'],
    )


def test_load_invalid_json_schema() -> None:
    profile = 'profile'
    key = 'user.email'
    value = 1

    with tempfile.NamedTemporaryFile('w+', delete=False) as f:
        path = Path(f.name)
        json.dump({profile: {key: value}}, f)

    with pytest.raises(ConfigLoadError) as exc, Storage(path):
        """ This 'with' context is required to trigger the load (or an other
            config manipulating operation)"""

    path.unlink()

    assert_str_in_str(
        str(exc.value),
        words_exact=[profile, key, str(value)],
        words_norm=['invalid'],
    )


def test_set_fail(storage: Storage) -> None:
    profile = 'test'
    key = 'invalidkey'
    value = 'Alice'

    with pytest.raises(StorageError) as exc:
        storage.set(profile, key, value)

    assert_str_in_str(
        str(exc.value),
        words_exact=[profile, key, value],
        words_norm=['invalid', 'key'],
    )


def test_get_fail(storage: Storage) -> None:
    profile = 'does_not_exist'

    with pytest.raises(StorageError) as exc:
        storage.get_profile(profile)

    assert_str_in_str(
        str(exc.value),
        words_exact=[profile],
        words_norm=['not', 'exist', 'profile'],
    )


def test_unset_fail(storage: Storage) -> None:
    profile = 'does_not_exist'
    key = 'user.name'

    with pytest.raises(StorageError) as exc:
        storage.unset(profile, key)

    assert_str_in_str(
        str(exc.value),
        words_exact=[profile],
        words_norm=['not', 'exist', 'profile'],
    )


def test_remove_fail(storage: Storage) -> None:
    profile = 'does_not_exist'

    with pytest.raises(StorageError) as exc:
        storage.remove(profile)

    assert_str_in_str(
        str(exc.value),
        words_exact=[profile],
        words_norm=['not', 'exist', 'profile'],
    )


def test_set_and_get(storage: Storage) -> None:
    profile = 'test'
    key = 'user.name'
    value = 'Alice'

    storage.set(profile, key, value)
    assert storage.get_profile(profile)[key] == value

    new_value = 'Bob'
    storage.set(profile, key, new_value)
    assert storage.get_profile(profile)[key] == new_value


def test_unset(storage: Storage) -> None:
    profile = 'test'
    key = 'user.name'
    value = 'Alice'

    storage.set(profile, key, value)
    storage.unset(profile, key)

    assert key not in storage.get_profile(profile)


def test_remove_profile(storage: Storage) -> None:
    profile1 = 'default'
    profile2 = 'word'

    key = 'user.name'

    storage.set(profile1, key, 'Alice')
    storage.set(profile2, key, 'Bob')

    storage.remove(profile2)

    profiles = json.loads(storage.config_file.read_text())
    assert list(profiles.keys()) == [profile1]


def test_import_file_not_found(storage: Storage) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        non_existent_file = Path(f'{tmp_dir}/non_existent_config.json')
        with pytest.raises(FileNotFoundError):
            storage.import_storage(non_existent_file, force=True)


def test_export_and_import(storage: Storage) -> None:
    src_profile = 'test'
    key = 'user.name'
    value = 'Alice'
    storage.set(src_profile, key, value)

    with tempfile.NamedTemporaryFile('w+', delete=False) as export_file:
        dest = Path(export_file.name)

    with pytest.raises(FileExistsError):
        storage.export_storage(dest)

    dest.unlink()
    storage.export_storage(dest)

    exported_data = json.loads(dest.read_text())
    assert exported_data == storage.config

    with (
        tempfile.NamedTemporaryFile('r+', delete=True) as temp_file,
        Storage(Path(temp_file.name)) as new_storage,
    ):
        new_storage.import_storage(dest, force=True)
        assert new_storage.get_profile(src_profile)[key] == value

    dest.unlink()


def test_import_merge_conflict(storage: Storage) -> None:
    profile = 'test'
    storage.set(profile, 'user.name', 'Alice')

    with tempfile.NamedTemporaryFile('w+', delete=False) as import_file:
        src_path = Path(import_file.name)
        json.dump({profile: {'user.name': 'Bob'}}, import_file)

    with pytest.raises(DictMergeConflictError):
        storage.import_storage(src_path, force=False)

    src_path.unlink()


def test_import_merge_no_conflict(storage: Storage) -> None:
    storage.set('p1', 'user.name', 'Alice')
    storage.set('p1', 'user.email', 'alice@example.com')

    import_data = {
        'p1': {'user.signingkey': 'ABC123'},
        'p2': {'user.name': 'Bob', 'user.email': 'bob@example.com'},
    }

    with tempfile.NamedTemporaryFile('w+', delete=False) as f:
        src = Path(f.name)
        json.dump(import_data, f)

    storage.import_storage(src, force=False)

    p1 = storage.get_profile('p1')
    assert p1['user.name'] == 'Alice'
    assert p1['user.email'] == 'alice@example.com'
    assert p1['user.signingkey'] == 'ABC123'

    p2 = storage.get_profile('p2')
    assert p2['user.name'] == 'Bob'
    assert p2['user.email'] == 'bob@example.com'

    src.unlink()
