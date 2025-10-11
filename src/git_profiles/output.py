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

"""Module for standardized CLI output handling.

Provides the `Outputter` class to manage normal and error messages,
respecting a quiet mode.
"""

import sys
from typing import TextIO

__all__ = ['Outputter']


class Outputter:
    """Handles printing messages to stdout or stderr for a CLI application."""

    def __init__(self, *, quiet: bool) -> None:
        """Initialize the outputter.

        Args:
            quiet (bool): Suppress normal output if True. Errors are always printed.
        """
        self._quiet = quiet

    @staticmethod
    def _log(msg: str, *, file: TextIO | None) -> None:
        """Internal method to print a message to a given file-like object.

        Args:
            msg (str): The message to print.
            file (Optional[Any]): The file or stream to print to (e.g., sys.stdout,
                                  sys.stderr).
                                  If None, defaults to sys.stdout.
        """
        print(msg, file=sys.stdout if file is None else file)

    def log(self, msg: str, *, file: TextIO | None = None) -> None:
        """Print a normal message if quiet mode is not enabled.

        Args:
            msg (str): The message to print.
            file (Optional[Any]): The output file or stream. Defaults to stdout if None.
        """
        if not self._quiet:
            self._log(msg, file=file)

    def error(self, msg: str) -> None:
        """Print an error message to stderr regardless of quiet mode.

        Args:
            msg (str): The error message to print.
        """
        self._log(msg, file=sys.stderr)
