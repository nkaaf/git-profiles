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
import functools
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import tempfile
import typing
from io import StringIO
from pathlib import Path
from typing import Any

from faker import Faker

from git_profiles.__main__ import main

__all__ = [
    'BASH_EXECUTABLE',
    'ENCODING',
    'FAKER',
    'GIT_EXECUTABLE',
    'PYTHON_EXECUTABLE',
    'VALUE_ARGPARSE_ERROR',
    'VALUE_ERROR',
    'VALUE_SUCCESS',
    'VERSION',
    'assert_str_in_str',
    'execute',
    'execute_transaction',
    'execute_via_git',
    'execute_via_module',
    'with_tempfile',
]

FAKER = Faker()

VALUE_SUCCESS = 0
VALUE_ERROR = 1
VALUE_ARGPARSE_ERROR = 2

VERSION = importlib.metadata.version('git-profiles')

GIT_EXECUTABLE = shutil.which('git')
assert GIT_EXECUTABLE is not None
PYTHON_EXECUTABLE = shutil.which('python')
assert PYTHON_EXECUTABLE is not None
BASH_EXECUTABLE = shutil.which('bash')
assert BASH_EXECUTABLE is not None

ENCODING = 'utf-8'


def with_tempfile(func):  # noqa: ANN001, ANN201
    @functools.wraps(func)
    def wrapper(*args, **kwargs):  # noqa: ANN002,ANN003,ANN202
        with tempfile.NamedTemporaryFile(
            'r+', delete=True, encoding=ENCODING
        ) as temp_file:
            if 'init_config' in kwargs:
                obj = kwargs.pop('init_config')
                if not isinstance(obj, str):
                    obj = json.dumps(obj)
                temp_file.write(obj)
                temp_file.flush()
                temp_file.seek(0)
            return func(temp_file, *args, **kwargs)

    return wrapper


def _execute(
    temp_file: typing.IO[Any],
    commands: list[str],
    *,
    in_dir: Path | None = None,
) -> tuple[int, str, str, str]:
    in_dir = in_dir if in_dir is not None else Path.cwd()
    sys.argv = ['git-profiles', '--storage', temp_file.name, *commands]

    saved_path = Path.cwd()
    # Change to ContextManager usage of chdir, if PY311 is Min Version
    os.chdir(in_dir)

    with (
        StringIO() as buffer_stdout,
        StringIO() as buffer_stderr,
        contextlib.redirect_stderr(buffer_stderr),
        contextlib.redirect_stdout(buffer_stdout),
    ):
        ret_val = main()

        buffer_stdout.flush()
        buffer_stdout.seek(0)
        stdout = buffer_stdout.read()

        buffer_stderr.flush()
        buffer_stderr.seek(0)
        stderr = buffer_stderr.read()

    os.chdir(saved_path)

    return ret_val, stdout, stderr, Path(temp_file.name).read_text()


@with_tempfile
def execute(
    temp_file: typing.IO[Any],
    commands: list[str] | str,
    *,
    in_dir: Path | None = None,
) -> tuple[int, str, str, str]:
    commands = [commands] if isinstance(commands, str) else commands
    return _execute(temp_file, commands, in_dir=in_dir)


@with_tempfile
def execute_transaction(
    temp_file: typing.IO[Any],
    command_sets: list[list[str]],
    *,
    in_dir: Path | None = None,
) -> list[tuple[int, str, str, str]]:
    return [
        _execute(temp_file, command_set, in_dir=in_dir) for command_set in command_sets
    ]


@with_tempfile
def execute_via_git(temp_file: typing.IO[Any], commands: list[str] | str) -> str:
    commands = [commands] if isinstance(commands, str) else commands

    args = [GIT_EXECUTABLE, 'profiles', '--storage', temp_file.name, *commands]
    return subprocess.check_output(args).decode(ENCODING)  # noqa: S603


@with_tempfile
def execute_via_module(temp_file: typing.IO[Any], commands: list[str] | str) -> str:
    commands = [commands] if isinstance(commands, str) else commands

    args = [
        PYTHON_EXECUTABLE,
        '-m',
        'git_profiles',
        '--storage',
        temp_file.name,
        *commands,
    ]
    return subprocess.check_output(args).decode(ENCODING)  # noqa: S603


def assert_str_in_str(
    text: str,
    *,
    words_exact: list[str] | None = None,
    words_norm: list[str] | None = None,
    words_exact_excl: list[str] | None = None,
) -> None:
    words_exact = [] if words_exact is None else words_exact
    words_norm = [] if words_norm is None else [word.lower() for word in words_norm]
    words_exact_excl = [] if words_exact_excl is None else words_exact_excl

    for word in words_exact:
        assert word in text

    for word in words_norm:
        assert word in text.lower()

    for word in words_exact_excl:
        assert word not in text
