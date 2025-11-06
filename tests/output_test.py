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
from io import StringIO

import pytest

from git_profiles.output import Outputter


def test_log() -> None:
    msg = 'This is a log'

    with (
        StringIO() as buffer,
        contextlib.redirect_stdout(buffer),
    ):
        Outputter(quiet=False).log(msg)

        buffer.flush()
        buffer.seek(0)
        assert buffer.read().strip() == msg


def test_log_quiet() -> None:
    msg = 'This is a log'

    with (
        StringIO() as buffer,
        contextlib.redirect_stdout(buffer),
    ):
        Outputter(quiet=True).log(msg)

        buffer.flush()
        buffer.seek(0)
        assert buffer.read() == ''


@pytest.mark.parametrize('quiet', [True, False])
def test_error(quiet: bool) -> None:  # noqa: FBT001
    msg = 'This is an error'

    with (
        StringIO() as buffer,
        contextlib.redirect_stderr(buffer),
    ):
        Outputter(quiet=quiet).error(msg)

        buffer.flush()
        buffer.seek(0)
        assert buffer.read().strip() == msg
