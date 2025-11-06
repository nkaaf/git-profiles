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

import contextlib
import importlib.metadata
import shutil
import subprocess
import sys
import tempfile
from io import StringIO

import pytest

from git_profiles.__main__ import main

GIT_EXECUTABLE = shutil.which('git')
assert GIT_EXECUTABLE is not None
PYTHON_EXECUTABLE = shutil.which('python')
assert PYTHON_EXECUTABLE is not None

VALUE_SUCCESS = 0
VALUE_ERROR = 1
VALUE_ARGPARSE_ERROR = 2

VERSION = importlib.metadata.version('git-profiles')

ENCODING = 'utf-8'


def test_execution_via_git_success() -> None:
    assert VERSION in subprocess.check_output(  # noqa: S603
        [GIT_EXECUTABLE, 'profiles', 'version']
    ).decode(ENCODING)


def test_execution_via_git_error() -> None:
    with (
        tempfile.NamedTemporaryFile('r+', encoding=ENCODING) as temp_file,
        pytest.raises(subprocess.CalledProcessError) as exec_info,
    ):
        subprocess.check_output(  # noqa: S603
            [
                GIT_EXECUTABLE,
                'profiles',
                '--storage',
                temp_file.name,
                'apply',
                'not_existing',
            ]
        ).decode(ENCODING)
    assert exec_info.value.returncode == VALUE_ERROR


def test_execution_via_git_argparse_error() -> None:
    with pytest.raises(subprocess.CalledProcessError) as exec_info:
        subprocess.check_output(  # noqa: S603
            [GIT_EXECUTABLE, 'profiles', '--version']
        ).decode(ENCODING)
    assert exec_info.value.returncode == VALUE_ARGPARSE_ERROR


def test_execution_via_module_success() -> None:
    assert VERSION in subprocess.check_output(  # noqa: S603
        [PYTHON_EXECUTABLE, '-m', 'git_profiles', 'version']
    ).decode(ENCODING)


def test_execution_via_module_error() -> None:
    with (
        tempfile.NamedTemporaryFile('r+', encoding=ENCODING) as temp_file,
        pytest.raises(subprocess.CalledProcessError) as exec_info,
    ):
        subprocess.check_output(  # noqa: S603
            [
                PYTHON_EXECUTABLE,
                '-m',
                'git_profiles',
                '--storage',
                temp_file.name,
                'apply',
                'not_existing',
            ]
        ).decode(ENCODING)
    assert exec_info.value.returncode == VALUE_ERROR


def test_execution_via_module_argparse_error() -> None:
    with pytest.raises(subprocess.CalledProcessError) as exec_info:
        subprocess.check_call([PYTHON_EXECUTABLE, '-m', 'git_profiles', '--version'])  # noqa: S603
    assert exec_info.value.returncode == VALUE_ARGPARSE_ERROR


def test_execution_success() -> None:
    with (
        StringIO() as buffer,
        contextlib.redirect_stdout(buffer),
    ):
        sys.argv = ['', 'version']
        assert main() == VALUE_SUCCESS

        buffer.flush()
        buffer.seek(0)
        assert VERSION in buffer.read()


def test_execution_error() -> None:
    with (
        tempfile.NamedTemporaryFile('r+', encoding=ENCODING) as temp_file,
    ):
        sys.argv = ['', '--storage', temp_file.name, 'apply', 'not_existing']
        assert main() == VALUE_ERROR


def test_execution_argparse_error() -> None:
    sys.argv = ['', '--version']
    with pytest.raises(SystemExit) as exec_info:
        main()
    assert exec_info.value.code == VALUE_ARGPARSE_ERROR
