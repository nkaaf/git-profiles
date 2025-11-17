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
import os
import subprocess
from pathlib import Path

import pytest

from test_git_profiles.common_helpers_test import (
    BASH_EXECUTABLE,
    ENCODING,
    FAKER,
    GIT_EXECUTABLE,
    VALUE_ERROR,
    VALUE_SUCCESS,
    assert_str_in_str,
    execute,
    execute_transaction,
)


@pytest.fixture
def git_init(tmp_path: Path) -> Path:
    subprocess.check_call(  # noqa: S603
        [BASH_EXECUTABLE, '-c', f'cd {tmp_path.absolute()} && {GIT_EXECUTABLE} init']
    )

    return tmp_path


def test_handle_set_fail() -> None:
    profile_name = 'profile'
    invalid_key = 'user'
    value = 'value'

    ret_val, _stdout, stderr, _config = execute(
        ['set', profile_name, invalid_key, value]
    )
    assert ret_val == VALUE_ERROR

    assert_str_in_str(
        stderr,
        words_exact=[profile_name, invalid_key, value],
        words_norm=['invalid', 'key'],
    )


def test_handle_set_create_profile() -> None:
    key = 'user.name'

    profile1_name = 'new_profile1'
    user1_name = 'testname1'

    profile2_name = 'new_profile2'
    user2_name = 'testname2'

    checkpoints = execute_transaction(
        [
            ['set', profile1_name, key, user1_name],
            ['set', profile2_name, key, user2_name],
        ]
    )

    # Checkpoint 1
    ret_val, stdout, stderr, _config = checkpoints[0]
    assert ret_val == VALUE_SUCCESS
    assert stderr == ''
    assert_str_in_str(
        stdout,
        words_exact=[profile1_name, user1_name, key],
        words_norm=['Create'],
    )

    # Checkpoint 2
    ret_val, stdout, stderr, _config = checkpoints[1]
    assert ret_val == VALUE_SUCCESS
    assert stderr == ''
    assert_str_in_str(
        stdout,
        words_exact=[profile2_name, user2_name, key],
        words_norm=['Create'],
        words_exact_excl=[profile1_name, user1_name],
    )


def test_handle_set_update_profile() -> None:
    key = 'user.name'

    profile1_name = 'new_profile1'
    user1_name = 'testname1'
    user1_name_new = 'testname1new'

    profile2_name = 'new_profile2'
    user2_name = 'testname2'

    checkpoints = execute_transaction(
        [
            ['set', profile1_name, key, user1_name],
            ['set', profile2_name, key, user2_name],
            ['set', profile1_name, key, user1_name_new],
        ]
    )

    # Checkpoint 1 and 2 are covered by other test

    # Checkpoint 3
    ret_val, stdout, stderr, _config = checkpoints[2]
    assert ret_val == VALUE_SUCCESS
    assert stderr == ''
    assert_str_in_str(
        stdout,
        words_exact=[profile1_name, user1_name_new, key],
        words_norm=['Update'],
        words_exact_excl=[profile2_name, user2_name],
    )


def test_handle_unset_fail() -> None:
    not_existing_profile = 'profile'
    key = 'key'

    ret_val, _stdout, stderr, _config = execute(['unset', not_existing_profile, key])
    assert ret_val == VALUE_ERROR

    assert_str_in_str(
        stderr,
        words_exact=[not_existing_profile],
        words_norm=['Not', 'Exist', 'profile'],
    )


def test_handle_unset() -> None:
    key_user_name = 'user.name'

    profile1_name = 'profile1'
    user1_name = 'testname1'

    profile2_name = 'profile2'
    user2_name = 'testname2'

    checkpoints = execute_transaction(
        [
            ['set', profile1_name, key_user_name, user1_name],
            ['set', profile2_name, key_user_name, user2_name],
            ['unset', profile1_name, key_user_name],
            ['unset', profile2_name, key_user_name],
        ]
    )

    # Checkpoint 1 and 2 are covered by other test

    # Checkpoint 3
    ret_val, stdout, stderr, _config = checkpoints[2]
    assert ret_val == VALUE_SUCCESS
    assert stderr == ''
    assert_str_in_str(
        stdout,
        words_exact=[profile1_name, key_user_name],
        words_norm=['Unset'],
        words_exact_excl=[profile2_name, user2_name],
    )

    # Checkpoint 4
    ret_val, stdout, stderr, _config = checkpoints[3]
    assert ret_val == VALUE_SUCCESS
    assert stderr == ''
    assert_str_in_str(
        stdout,
        words_exact=[profile2_name, key_user_name],
        words_norm=['Unset'],
        words_exact_excl=[profile1_name],
    )


def test_handle_show_fail() -> None:
    not_existing_profile = 'profile'

    ret_val, _stdout, stderr, _config = execute(['show', not_existing_profile])
    assert ret_val == VALUE_ERROR

    assert_str_in_str(
        stderr,
        words_exact=[not_existing_profile],
        words_norm=['Not', 'Exist', 'profile'],
    )


def test_handle_show() -> None:
    key_user_name = 'user.name'
    key_user_email = 'user.email'

    profile1_name = 'profile1'
    user1_name = 'testname1'

    profile2_name = 'profile2'
    user2_name = 'testname2'
    user2_email = FAKER.safe_email()

    checkpoints = execute_transaction(
        [
            ['set', profile1_name, key_user_name, user1_name],
            ['set', profile2_name, key_user_name, user2_name],
            ['set', profile2_name, key_user_email, user2_email],
            ['show', profile1_name],
            ['show', profile2_name],
        ]
    )

    # Checkpoints 1, 2 and 3 are covered by other tests

    # Checkpoint 4
    ret_val, stdout, stderr, _config = checkpoints[3]
    assert ret_val == VALUE_SUCCESS
    assert stderr == ''
    assert_str_in_str(
        stdout,
        words_exact=[profile1_name, key_user_name, user1_name],
        words_exact_excl=[profile2_name, user2_name, user2_email],
    )

    # Checkpoint 5
    ret_val, stdout, stderr, _config = checkpoints[4]
    assert ret_val == VALUE_SUCCESS
    assert stderr == ''
    assert_str_in_str(
        stdout,
        words_exact=[
            profile2_name,
            key_user_name,
            user2_name,
            key_user_email,
            user2_email,
        ],
        words_exact_excl=[profile1_name, user1_name],
    )


def test_handle_apply_fail(git_init: Path) -> None:
    not_existing_profile = 'profile'

    ret_val, _stdout, stderr, _config = execute(
        ['apply', not_existing_profile], in_dir=git_init
    )
    assert ret_val == VALUE_ERROR

    assert_str_in_str(
        stderr,
        words_exact=[not_existing_profile],
        words_norm=['Not', 'Exist', 'profile'],
    )


def test_handle_apply(git_init: Path) -> None:
    key_user_name = 'user.name'
    key_user_email = 'user.email'

    profile1_name = 'new_profile1'
    user1_name = 'testname1'

    profile2_name = 'new_profile2'
    user2_name = 'testname2'
    user2_email = FAKER.safe_email()

    checkpoints = execute_transaction(
        [
            ['set', profile1_name, key_user_name, user1_name],
            ['set', profile2_name, key_user_name, user2_name],
            ['set', profile2_name, key_user_email, user2_email],
            ['apply', profile2_name],
        ],
        in_dir=git_init,
    )

    # Checkpoints 1, 2 and 3 are covered by other tests

    # Checkpoint 4
    ret_val, stdout, stderr, config = checkpoints[3]
    assert ret_val == VALUE_SUCCESS
    assert stderr == ''
    assert_str_in_str(
        stdout,
        words_exact=[profile2_name, '2'],
        words_norm=['Appl'],  # "covers" Apply and Applied
        words_exact_excl=[profile1_name, user1_name, user2_name, user2_email],
    )

    dir_saved = Path.cwd()
    # Change to ContextManager usage of chdir, if PY311 is Min Version
    os.chdir(git_init)

    config_user_name = subprocess.check_output(
        [GIT_EXECUTABLE, 'config', 'user.name']
    ).decode(  # noqa: S603
        ENCODING
    )[:-1]
    assert config_user_name == user2_name

    config_user_email = subprocess.check_output(
        [GIT_EXECUTABLE, 'config', 'user.email']
    ).decode(  # noqa: S603
        ENCODING
    )[:-1]
    assert config_user_email == user2_email

    ret_val, stdout, stderr, _config = execute(
        ['apply', profile1_name], in_dir=git_init, init_config=config
    )
    assert ret_val == VALUE_SUCCESS
    assert stderr == ''
    assert_str_in_str(
        stdout,
        words_exact=[profile1_name, '1'],
        words_norm=['Appl'],  # "covers" Apply and Applied
        words_exact_excl=[profile2_name, user1_name, user2_name, user2_email],
    )

    assert (
        subprocess.check_output([GIT_EXECUTABLE, 'config', 'user.name']).decode(  # noqa: S603
            ENCODING
        )[:-1]
        == user1_name
    )

    os.chdir(dir_saved)


def test_handle_export_fail(tmp_path: Path) -> None:
    export_file = tmp_path / 'export.json'
    export_file.touch()

    ret_val, _stdout, stderr, _config = execute(['export', str(export_file.absolute())])
    assert ret_val == VALUE_ERROR
    assert_str_in_str(
        stderr, words_exact=[str(export_file.absolute())], words_norm=['exist']
    )


def test_handle_export(tmp_path: Path) -> None:
    export_file = tmp_path / 'export.json'

    checkpoints = execute_transaction(
        [['set', 'dev', 'user.name', 'Alice'], ['export', str(export_file.absolute())]]
    )

    assert export_file.is_file()

    config = checkpoints[0][3]
    exported = export_file.read_text()
    assert exported == config

    ret_val, stdout, stderr, _config = checkpoints[1]
    assert ret_val == VALUE_SUCCESS
    assert stderr == ''
    assert_str_in_str(
        stdout, words_exact=[str(export_file.absolute())], words_norm=['export']
    )


def test_handle_import_fail(tmp_path: Path) -> None:
    import_file = tmp_path / 'import.json'

    ret_val, _stdout, stderr, _config = execute(
        ['import', str(import_file.absolute())],
    )
    assert ret_val == VALUE_ERROR
    assert_str_in_str(
        stderr,
        words_exact=[str(import_file.absolute())],
        words_norm=['not', 'exist'],
    )


def test_handle_import_force(tmp_path: Path) -> None:
    import_file = tmp_path / 'force.json'

    execute_transaction(
        [
            ['set', 'dev', 'user.name', 'OVERRIDDEN'],
            ['export', str(import_file.absolute())],
        ]
    )

    checkpoints = execute_transaction(
        [
            ['set', 'dev', 'user.name', 'Alice'],
            ['import', '--force', str(import_file.absolute())],
            ['show', 'dev'],
        ]
    )

    ret_val, stdout, stderr, _config = checkpoints[1]
    assert ret_val == VALUE_SUCCESS
    assert stderr == ''

    _ret_val, stdout, _stderr, _config = checkpoints[2]
    assert_str_in_str(stdout, words_exact=['user.name', 'OVERRIDDEN'])


def test_handle_import_merge_no_conflict(tmp_path: Path) -> None:
    import_file = tmp_path / 'merge.json'

    execute_transaction(
        [
            ['set', 'ops', 'user.email', 'ops@example.com'],
            ['set', 'qa', 'user.name', 'Carol'],
            ['export', str(import_file.absolute())],
        ]
    )

    checkpoints = execute_transaction(
        [
            ['set', 'dev', 'user.name', 'Alice'],
            ['set', 'ops', 'user.name', 'Bob'],
            ['import', str(import_file.absolute())],
            ['show', 'dev'],
            ['show', 'ops'],
            ['show', 'qa'],
        ]
    )

    ret_val, stdout, stderr, _config = checkpoints[2]
    assert ret_val == VALUE_SUCCESS
    assert stderr == ''
    assert_str_in_str(
        stdout, words_exact=[str(import_file.absolute())], words_norm=['import']
    )

    ret_val, stdout, stderr, _config = checkpoints[3]
    assert ret_val == VALUE_SUCCESS
    assert_str_in_str(stdout, words_exact=['user.name', 'Alice'])

    ret_val, stdout, stderr, _config = checkpoints[4]
    assert ret_val == VALUE_SUCCESS
    assert_str_in_str(stdout, words_exact=['user.name', 'Bob'])
    assert_str_in_str(stdout, words_exact=['user.name', 'ops@example.com'])

    ret_val, stdout, stderr, _config = checkpoints[5]
    assert ret_val == VALUE_SUCCESS
    assert_str_in_str(stdout, words_exact=['user.name', 'Carol'])


def test_handle_import_export_roundtrip(tmp_path: Path) -> None:
    export_file = tmp_path / 'roundtrip.json'

    execute_transaction(
        [
            ['set', 'dev', 'user.name', 'Alice'],
            ['set', 'dev', 'user.email', 'alice@example.com'],
            ['set', 'ops', 'user.name', 'Bob'],
            ['export', str(export_file.absolute())],
        ]
    )

    checkpoints = execute_transaction(
        [
            ['import', str(export_file.absolute()), '--force'],
            ['show', 'dev'],
            ['show', 'ops'],
        ]
    )

    ret_val, stdout, stderr, _config = checkpoints[0]
    assert ret_val == VALUE_SUCCESS
    assert stderr == ''
    assert_str_in_str(
        stdout, words_exact=[str(export_file.absolute())], words_norm=['import']
    )

    ret_val, stdout, stderr, _config = checkpoints[1]
    assert ret_val == VALUE_SUCCESS
    assert_str_in_str(stdout, words_exact=['user.name', 'Alice'])

    ret_val, stdout, stderr, _config = checkpoints[2]
    assert ret_val == VALUE_SUCCESS
    assert_str_in_str(stdout, words_exact=['user.name', 'Bob'])


def test_handle_import_merge_conflict(tmp_path: Path) -> None:
    import_file = tmp_path / 'conflict.json'

    execute_transaction(
        [
            ['set', 'ops', 'user.name', 'ORIGINAL'],
            ['export', str(import_file.absolute())],
        ]
    )

    import_data = {'ops': {'user.name': 'CHANGED'}}
    import_file.write_text(json.dumps(import_data))

    original_data = import_data.copy()
    original_data['ops']['user.name'] = 'ORIGINAL'

    ret_val, stdout, stderr, _config = execute(
        ['import', str(import_file.absolute())], init_config=original_data
    )

    assert ret_val == VALUE_ERROR
    assert stdout == ''

    assert_str_in_str(
        stderr,
        words_norm=['conflict', 'Found', 'import'],
        words_exact=['ops', 'user.name', 'CHANGED', 'ORIGINAL'],
    )


def test_handle_list_with_profiles() -> None:
    checkpoints = execute_transaction(
        [
            ['list'],
            ['set', 'dev', 'user.name', 'Alice'],
            ['set', 'ops', 'user.name', 'Bob'],
            ['list'],
        ]
    )

    ret_val, stdout, stderr, _config = checkpoints[0]

    assert ret_val == VALUE_SUCCESS
    assert stderr == ''

    assert_str_in_str(stdout, words_norm=['no', 'profile'])

    ret_val, stdout, stderr, _config = checkpoints[3]

    assert ret_val == VALUE_SUCCESS
    assert stderr == ''

    assert_str_in_str(stdout, words_norm=['profiles'], words_exact=['dev', 'ops'])


def test_handle_remove() -> None:
    checkpoints = execute_transaction(
        [
            ['remove', 'non_existing'],
            ['set', 'dev', 'user.name', 'Alice'],
            ['remove', 'dev'],
        ]
    )

    ret_val, stdout, stderr, _config = checkpoints[0]

    assert ret_val == VALUE_ERROR
    assert_str_in_str(
        stderr, words_norm=['profile', 'not', 'exist'], words_exact=['non_existing']
    )

    ret_val, stdout, stderr, _config = checkpoints[2]

    assert ret_val == VALUE_SUCCESS
    assert stderr == ''

    assert_str_in_str(
        stdout,
        words_exact=['dev'],
        words_norm=['removed'],
    )


def test_handle_duplicate() -> None:
    checkpoints = execute_transaction(
        [
            ['set', 'dev', 'user.name', 'Alice'],
            ['duplicate', 'dev', 'copy'],
        ]
    )

    ret_val, stdout, stderr, config = checkpoints[1]

    assert ret_val == VALUE_SUCCESS
    assert stderr == ''

    assert_str_in_str(
        stdout,
        words_exact=['dev', 'copy'],
        words_norm=['duplicate'],
    )

    assert json.loads(config)['copy']['user.name'] == 'Alice'


def test_handle_duplicate_fail_missing_source() -> None:
    ret_val, stdout, stderr, _config = execute(['duplicate', 'ghost', 'copy'])

    assert ret_val == VALUE_ERROR
    assert stdout == ''

    assert_str_in_str(
        stderr,
        words_exact=['ghost'],
        words_norm=['not', 'exist'],
    )
