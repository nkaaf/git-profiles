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

"""`git_profiles` package.

Provides a CLI tool and underlying storage for managing multiple
Git configuration profiles. Profiles can be created, updated, applied,
listed, shown, duplicated, or removed, allowing users to switch between
different Git identities and settings easily.

Modules:
- cli: Command-line interface implementation.
- storage: Persistent storage and validation of profiles.
- output: Unified handling of console output.
- const: Constants used across the package.

Usage:
    # Typically used via the CLI entry point
    git-profiles <command> [options]
"""

__all__ = []
