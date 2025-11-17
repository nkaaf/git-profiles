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

import subprocess

import pytest

from test_git_profiles.common_helpers_test import (
    VALUE_ARGPARSE_ERROR,
    VALUE_ERROR,
    VALUE_SUCCESS,
    VERSION,
    execute,
    execute_via_git,
    execute_via_module,
)


def test_execution_success() -> None:
    ret_val, _stdout, _stderr, _config = execute('version')
    assert ret_val == VALUE_SUCCESS


def test_execution_error() -> None:
    ret_val, _stdout, _stderr, _config = execute(['apply', 'not_existing'])
    assert ret_val == VALUE_ERROR


def test_execution_argparse_error() -> None:
    with pytest.raises(SystemExit) as exec_info:
        _ret_val, _stdout, _stderr, _config = execute('--version')
    assert exec_info.value.code == VALUE_ARGPARSE_ERROR


def test_execution_via_git_success() -> None:
    output = execute_via_git('version')
    assert VERSION in output


def test_execution_via_git_error() -> None:
    with pytest.raises(subprocess.CalledProcessError) as exec_info:
        execute_via_git(['apply', 'not_existing'])

    assert exec_info.value.returncode == VALUE_ERROR


def test_execution_via_git_argparse_error() -> None:
    with pytest.raises(subprocess.CalledProcessError) as exec_info:
        execute_via_git('--version')

    assert exec_info.value.returncode == VALUE_ARGPARSE_ERROR


def test_execution_via_module_success() -> None:
    output = execute_via_module('version')
    assert VERSION in output


def test_execution_via_module_error() -> None:
    with pytest.raises(subprocess.CalledProcessError) as exec_info:
        execute_via_module(['apply', 'not_existing'])

    assert exec_info.value.returncode == VALUE_ERROR


def test_execution_via_module_argparse_error() -> None:
    with pytest.raises(subprocess.CalledProcessError) as exec_info:
        execute_via_module('--version')

    assert exec_info.value.returncode == VALUE_ARGPARSE_ERROR
