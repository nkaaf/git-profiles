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

"""Entry point for the git profiles CLI application.

This module handles command-line execution, invoking the `Cli` class
to parse arguments and execute commands. It also manages exit codes:

- Returns 0 on success.
- Returns 1 if an `ExitError` occurs (e.g., invalid input, missing git).

Usage:
    python -m git_profiles
    # or if installed as a CLI tool
    git-profiles <command> [options]
"""

import sys

from .cli import Cli, ExitError


def main() -> int:
    """Run the CLI application.

    Returns:
        int: Exit code (0 on success, 1 on error).
    """
    try:
        Cli(sys.argv[1:])
    except ExitError:
        ret_val = 1
    else:
        ret_val = 0

    return ret_val


if __name__ == '__main__':
    sys.exit(main())
