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

"""CLI module for managing and applying Git configuration profiles.

This module provides the `Cli` class that implements a fully-featured
command-line interface for creating, updating, applying, importing,
exporting, and removing git configuration profiles.

Profiles are stored persistently using the `Storage` class, and each
profile consists of key-value pairs representing git config settings.

Commands supported:
- `set`      : Add or update a key=value in a profile
- `unset`    : Remove a key from a profile
- `apply`    : Apply a profile to the local git repository
- `list`     : List all available profiles
- `show`     : Show all key=value pairs for a profile
- `remove`   : Delete a profile entirely
- `duplicate`: Duplicate an existing profile under a new name
- `version`  : Show the CLI version
- `export`   : Export all profiles to a file
- `import`   : Import profiles from a file with optional merge
"""

import argparse
import builtins
import contextlib
import importlib.metadata
import shutil
import subprocess
from pathlib import Path

from git_profiles.const import PROGRAM_NAME
from git_profiles.output import Outputter
from git_profiles.storage import (
    DictMergeConflictError,
    Storage,
    StorageError,
)

__all__ = ['Cli', 'ExitError']


class ExitError(Exception):
    """Exception used to signal that the program should exit with an error.

    This can be raised in CLI command handlers to indicate a fatal error
    that should terminate the program, optionally after printing a user-friendly
    message. Caught in the main CLI entrypoint to exit with a non-zero status.
    """


class Cli:
    """Command-line interface for managing git configuration profiles.

    Parses CLI arguments, executes commands, and handles output and error reporting.
    """

    def __init__(self, argv: list[str]) -> None:
        """Initialize the CLI, parse arguments, and execute the selected command.

        Args:
            argv (list[str]): The list of command-line arguments.

        Raises:
            ExitError: If any exception occurs during runtime.
        """
        parser = self._build_parser()
        args = parser.parse_args(argv)

        self._outputter = Outputter(quiet=args.quiet)

        self._git_path = self._evaluate_git_path()

        self._storage_path = Path(args.storage)

        try:
            self._run(args)
        except StorageError as e:
            self._outputter.error(str(e))
            raise ExitError from e

    def _build_storage(self) -> Storage:
        return Storage(self._storage_path)

    def _run(self, args: argparse.Namespace) -> None:  # noqa: C901
        """Dispatch the CLI command based on parsed arguments.

        Args:
            args (argparse.Namespace):  Parsed argparse arguments with a `.func`
                                        attribute pointing to the correct command
                                        handler.

        Raises:
            StorageError: If another instance is running.
            ExitError: If program should exit due to error.
        """
        match args.func:
            case self._handle_set:
                self._handle_set(args.name, args.key, args.value)
            case self._handle_unset:
                self._handle_unset(args.name, args.key)
            case self._handle_apply:
                self._handle_apply(args.name)
            case self._handle_list:
                self._handle_list()
            case self._handle_show:
                self._handle_show(args.name)
            case self._handle_remove:
                self._handle_remove(args.name)
            case self._handle_duplicate:
                self._handle_duplicate(args.src, args.dest)
            case self._handle_version:
                self._handle_version()
            case self._handle_import:
                self._handle_import(Path(args.src), force=args.force)
            case self._handle_export:
                self._handle_export(Path(args.dest))

    def _evaluate_git_path(self) -> str:
        """Locate the `git` executable in the system PATH.

        Returns:
            str: Full path to the `git` executable.

        Raises:
            ExitError: If program should exit due to error.
        """
        path = shutil.which('git')
        if path is None:
            self._outputter.error("'git' is not available.")
            raise ExitError
        return path

    def _handle_set(self, profile_name: str, key: str, value: str) -> None:
        """Add or update a key=value pair in a profile.

        Creates the profile if it does not exist.

        Args:
            profile_name (str): Name of the profile to update.
            key (str): Git configuration key (e.g., 'user.email').
            value (str): Value to set for the key.

        Raises:
            StorageError: If key=value pair cannot be set or another instance is
                          running.
        """
        storage = self._build_storage()
        added_profile = storage.set(profile_name, key, value)

        if added_profile:
            self._outputter.log(
                f"[+] Created new profile '{profile_name}' and set '{key}={value}'"
            )
        else:
            self._outputter.log(f"[+] Updated '{profile_name}': set '{key}={value}'")

    def _handle_unset(self, profile_name: str, key: str) -> None:
        """Remove a key from a profile.

        Args:
            profile_name (str): Name of the profile.
            key (str): Git configuration key to remove.

        Raises:
            StorageError: If the profile does not exist or another instance is running.
        """
        storage = self._build_storage()
        storage.unset(profile_name, key)

        self._outputter.log(f"[x] Unset key '{key}' in profile '{profile_name}'")

    def _handle_apply(self, profile_name: str) -> None:
        """Apply a profile to the local git repository.

        Args:
            profile_name (str): Name of the profile to apply.

        Raises:
            StorageError: If the profile does not exist or another instance is running.
        """
        storage = self._build_storage()
        profile = storage.get_profile(profile_name)

        for key, value in profile.items():
            subprocess.check_call(  # noqa: S603
                [self._git_path, 'config', '--local', key, value]
            )
        self._outputter.log(
            f"[✔] Applied profile '{profile_name}' with {len(profile)} setting(s)"
        )

    def _handle_list(self) -> None:
        """List all available profiles.

        Raises:
            StorageError: If another instance is running.
        """
        storage = self._build_storage()
        profiles = storage.config.keys()

        if len(profiles) == 0:
            self._outputter.log('[i] No profiles found')
        else:
            self._outputter.log('[>] Available profiles:')
            for name in profiles:
                self._outputter.log(f'\t- {name}')

    def _handle_show(self, profile_name: str) -> None:
        """Display all key=value pairs of a profile.

        Args:
            profile_name (str): Name of the profile to show.

        Raises:
            StorageError: If the profile does not exist or another instance is running.
        """
        storage = self._build_storage()
        profile = storage.get_profile(profile_name)

        self._outputter.log(f"[>] Profile '{profile_name}':")
        for key, value in profile.items():
            self._outputter.log(f'\t{key} = {value}')

    def _handle_remove(self, profile_name: str) -> None:
        """Delete a profile.

        Args:
            profile_name (str): Name of the profile to remove.

        Raises:
            StorageError: If the profile does not exist or another instance is running.
        """
        storage = self._build_storage()
        storage.remove(profile_name)

        self._outputter.log(f"[✔] Removed profile '{profile_name}'")

    def _handle_duplicate(self, src: str, dest: str) -> None:
        """Duplicate a profile under a new name.

        Args:
            src (str): Source profile name.
            dest (str): Destination profile name.

        Raises:
            StorageError: If source does not exist, merge fails, or another instance is
                          running.
            ExitError: If program should exit due to error.
        """
        with self._build_storage() as storage:
            src_profile = storage.get_profile(src)

            try:
                storage.get_profile(dest)
            except StorageError:
                pass
            else:
                self._outputter.error(f"Destination profile '{dest}' already exists")
                raise ExitError

            try:
                for key, value in src_profile.items():
                    storage.set(dest, key, value)
            except StorageError as e:
                with contextlib.suppress(builtins.BaseException):
                    storage.remove(dest)

                self._outputter.error(
                    'Failed to duplicate profile for unknown reason',
                )
                raise ExitError from e

        self._outputter.log(f"[✔] Duplicate '{src}' to '{dest}'")

    def _handle_version(self) -> None:
        """Show the current version of git-profiles CLI."""
        self._outputter.log(importlib.metadata.version('git-profiles'))

    def _handle_export(self, dest: Path) -> None:
        """Export all profiles to a new configuration file.

        Args:
            dest (Path): Destination path.

        Raises:
            StorageError: If another instance is running.
            ExitError: If program should exit due to error.
        """
        storage = self._build_storage()

        try:
            storage.export_storage(dest)
        except FileExistsError as e:
            self._outputter.error(f"Destination file '{dest}' already exists")
            raise ExitError from e

        self._outputter.log(f"[✔] Export to '{dest}' successful")

    def _handle_import(self, src: Path, *, force: bool) -> None:
        """Import profiles from a configuration file.

        Args:
            src (Path): Source path.
            force (Path): Overwrite existing profiles on conflict if True.

        Raises:
            StorageError: If another instance is running.
            ExitError: If program should exit due to error.
        """
        storage = self._build_storage()

        try:
            storage.import_storage(src, force=force)
        except FileNotFoundError as e:
            self._outputter.error(f"Source file '{src}' not existing")
            raise ExitError from e
        except DictMergeConflictError as e:
            conflict_lines = ['Found the following merge conflicts during import:']

            for profile_name, entries in e.conflicts.items():
                conflict_lines.append(f'\tProfile: {profile_name}')
                for key, (old_value, new_value) in entries.items():
                    conflict_lines.append(
                        f'\t\t{key}: existing={old_value!r}, incoming={new_value!r}'
                    )

            self._outputter.error('\n'.join(conflict_lines))
            raise ExitError from e

        self._outputter.log(f"[✔] Import from '{src}' successful")

    def _build_parser(self) -> argparse.ArgumentParser:
        """Build the argument parser with all subcommands and options.

        Returns:
            argparse.ArgumentParser: Configured parser for the CLI.
        """
        parser = argparse.ArgumentParser(
            prog=PROGRAM_NAME, description='Manage and apply git config profiles.'
        )
        parser.add_argument(
            '-q',
            '--quiet',
            action='store_true',
            help='Suppress normal output',
        )
        parser.add_argument(
            '--storage',
            default=Storage.STORAGE_FILE_PATH_DEFAULT,
            help='Path to git-profiles storage file',
        )
        subparsers = parser.add_subparsers(dest='command', required=True)

        p_set = subparsers.add_parser(
            'set', help='Set key=value in a profile (creates if missing)'
        )
        p_set.add_argument('name', help='Profile name')
        p_set.add_argument('key', help='Config key (e.g., user.email)')
        p_set.add_argument('value', help='Config value')
        p_set.set_defaults(func=self._handle_set)

        p_unset = subparsers.add_parser('unset', help='Remove a key from a profile')
        p_unset.add_argument('name', help='Profile name')
        p_unset.add_argument('key', help='Config key to unset')
        p_unset.set_defaults(func=self._handle_unset)

        p_apply = subparsers.add_parser(
            'apply', help='Apply a profile to the local git repo'
        )
        p_apply.add_argument('name', help='Profile name')
        p_apply.set_defaults(func=self._handle_apply)

        p_list = subparsers.add_parser('list', help='List all available profiles')
        p_list.set_defaults(func=self._handle_list)

        p_show = subparsers.add_parser('show', help='Show all key-values for a profile')
        p_show.add_argument('name', help='Profile name')
        p_show.set_defaults(func=self._handle_show)

        p_remove = subparsers.add_parser('remove', help='Delete a profile entirely')
        p_remove.add_argument('name', help='Profile name')
        p_remove.set_defaults(func=self._handle_remove)

        p_duplicate = subparsers.add_parser('duplicate', help='Duplicate a profile')
        p_duplicate.add_argument('src', help='Source profile')
        p_duplicate.add_argument('dest', help='Destination profile')
        p_duplicate.set_defaults(func=self._handle_duplicate)

        p_version = subparsers.add_parser('version', help='Show version')
        p_version.set_defaults(func=self._handle_version)

        p_export = subparsers.add_parser('export', help='Export Configuration file')
        p_export.add_argument('dest', help='Destination path')
        p_export.set_defaults(func=self._handle_export)

        p_import = subparsers.add_parser(
            'import',
            help='Import Configuration file (overwriting or merging by force flag)',
        )
        p_import.add_argument('--force', action='store_true')
        p_import.add_argument('src', help='Source path')
        p_import.set_defaults(func=self._handle_import)

        return parser
