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

Provides the `Cli` class which handles argument parsing, command dispatch,
and integrates with the `Storage` class to manage persistent profiles.

Commands supported:
- set
- unset
- apply
- list
- show
- remove
- duplicate
"""

import argparse
import builtins
import contextlib
import shutil
import subprocess

from .const import PROGRAM_NAME
from .output import Outputter
from .storage import ConfigLoadError, Storage

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
        """
        parser = self._build_parser()
        args = parser.parse_args(argv)

        self._outputter = Outputter(quiet=args.quiet)

        try:
            self._storage = Storage()
        except ConfigLoadError as e:
            self._outputter.error(f'Error: {e}')
            raise ExitError from e

        self._git_path = self._evaluate_git_path()

        self._run(args)

    @staticmethod
    def _run(args) -> None:  # noqa: ANN001
        """Execute the command selected by the user.

        Args:
            args: Parsed argparse arguments.
        """
        args.func(args)

    def _evaluate_git_path(self) -> str:
        """Locate the `git` executable in the system PATH.

        Uses `shutil.which` to find the full path to the `git` binary.

        Returns:
            str: Full path to the `git` executable.

        Raises:
            ExitError: If `git` is not found in the system PATH.
        """
        path = shutil.which('git')
        if path is None:
            self._outputter.log("[!] 'git' is not available.")
            raise ExitError
        return path

    def _handle_set(self, args) -> None:  # noqa: ANN001
        """Set a key=value pair in a profile.

        Creates the profile if it does not exist.

        Args:
            args: Parsed argparse arguments with 'name', 'key', and 'value'.
        """
        profile_name, key, value = args.name, args.key, args.value

        try:
            added_profile = self._storage.set(profile_name, key, value)
        except ValueError as e:
            self._outputter.error(f'[X] Error: {e}')
            raise ExitError from e

        if added_profile:
            self._outputter.log(
                f"[+] Created new profile '{profile_name}' and set '{key}={value}'"
            )
        else:
            self._outputter.log(f"[+] Updated '{profile_name}': set '{key}={value}'")

    def _handle_unset(self, args) -> None:  # noqa: ANN001
        """Remove a key from a profile.

        Args:
            args: Parsed argparse arguments with 'name' and 'key'.
        """
        profile_name, key = args.name, args.key

        try:
            self._storage.unset(profile_name, key)
        except KeyError as e:
            self._outputter.error(f"[!] Profile '{profile_name}' does not exist")
            raise ExitError from e

        self._outputter.log(f"[x] Unset key '{key}' in profile '{profile_name}'")

    def _handle_apply(self, args) -> None:  # noqa: ANN001
        """Apply a profile's key-values to the local Git repository.

        Args:
            args: Parsed argparse arguments with 'name'.
        """
        profile_name = args.name

        try:
            profile = self._storage.get_profile(profile_name)
        except KeyError as e:
            self._outputter.error(f"[!] Profile '{profile_name}' does not exist")
            raise ExitError from e

        for key, value in profile.items():
            subprocess.check_call(  # noqa: S603
                [self._git_path, 'config', '--local', key, value]
            )
        self._outputter.log(
            f"[✔] Applied profile '{profile_name}' with {len(profile)} setting(s)"
        )

    def _handle_list(self, _args) -> None:  # noqa: ANN001
        """List all available profiles."""
        profiles = self._storage.config.keys()

        if not profiles:
            self._outputter.error('[i] No profiles found')
            raise ExitError

        self._outputter.log('[>] Available profiles:')
        for name in profiles:
            self._outputter.log(f' - {name}')

    def _handle_show(self, args) -> None:  # noqa: ANN001
        """Show all key=value pairs for a profile.

        Args:
            args: Parsed argparse arguments with 'name'.
        """
        name = args.name

        try:
            profile = self._storage.get_profile(name)
        except KeyError as e:
            self._outputter.error(f"[!] Profile '{name}' does not exist")
            raise ExitError from e

        self._outputter.log(f"[>] Profile '{name}':")
        for key, value in profile.items():
            self._outputter.log(f'  {key} = {value}')

    def _handle_remove(self, args) -> None:  # noqa: ANN001
        """Delete a profile entirely.

        Args:
            args: Parsed argparse arguments with 'name'.
        """
        name = args.name

        try:
            self._storage.remove(name)
        except KeyError as e:
            self._outputter.error(f"[!] Profile '{name}' does not exist")
            raise ExitError from e

        self._outputter.log(f"[x] Removed profile '{name}'")

    def _handle_duplicate(self, args) -> None:  # noqa: ANN001
        """Duplicate a profile under a new name.

        Args:
            args: Parsed argparse arguments with 'src' and 'dest'.
        """
        src, dest = args.src, args.dest

        try:
            src_profile = self._storage.get_profile(src)
        except KeyError as e:
            self._outputter.error(f"[X] Source profile '{src}' not found")
            raise ExitError from e

        try:
            self._storage.get_profile(dest)
        except KeyError:
            pass
        else:
            self._outputter.error(f"[X] Destination profile '{dest}' already exists")
            raise ExitError

        try:
            for key, value in src_profile.items():
                self._storage.set(dest, key, value)
        except ValueError as e:
            with contextlib.suppress(builtins.BaseException):
                self._storage.remove(dest)

            self._outputter.error(
                '[X] Failed to duplicate profile for unknown reason',
            )
            raise ExitError from e

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

        return parser
