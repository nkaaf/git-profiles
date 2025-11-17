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

"""Storage module for managing persistent git profiles.

This module provides classes to handle reading, writing, and validating
profile configurations stored in JSON format. Each profile is a set of
key-value pairs for git configuration.

Features:
- Atomic writes to prevent corruption.
- Key/value validation (Email according to WHATWG spec) and whitelisting.
- Schema validation using Pydantic.
- File-locking and transactional support
"""

import functools
import json
import re
import tempfile
import types
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar, Concatenate, ParamSpec, TypeVar, cast

from filelock import FileLock, Timeout
from platformdirs import PlatformDirs
from pydantic import RootModel
from pydantic import ValidationError as PydanticValidationError
from typing_extensions import Self

from git_profiles.const import PROGRAM_NAME

__all__ = ['DictMergeConflictError', 'Storage', 'StorageError']

ProfileType = dict[str, str]
ConfigType = dict[str, ProfileType]
ConflictsType = dict[str, dict[str, tuple[str, str]]]


class ProfileModel(RootModel[ProfileType]):
    """Represents a single profile with key-value settings."""


class ConfigModel(RootModel[dict[str, ProfileModel]]):
    """Root model for the entire configuration (multiple profiles)."""


class StorageError(Exception):
    """Base exception for storage-related errors.

    This serves as the root class for all exceptions raised by the `Storage`
    subsystem. It stores an error message that can be easily formatted and displayed.

    Attributes:
        message (str): Human-readable description of the error.
    """

    def __init__(self, message: str) -> None:
        """Initialize the exception with a message.

        Args:
            message (str): The error message to display.
        """
        super().__init__()
        self.message = message

    def __str__(self) -> str:
        """Return a formatted string representation of the error."""
        return f'Error in Storage: "{self.message}"'


class ConfigLoadError(StorageError):
    """Raised when the config file is invalid or cannot be loaded."""

    def __init__(self, path: Path, message: str) -> None:
        """Initialize a ConfigLoadError."""
        super().__init__(f"Invalid config file '{path}': {message}")


class StorageProfileError(StorageError):
    """Raised when an error occurs while handling a specific profile.

    Typically raised when loading, saving, or modifying a profile fails.
    """

    def __init__(self, profile: str, message: str) -> None:
        """Initialize the profile error with the affected profile and message.

        Args:
            profile (str): The name of the problematic profile.
            message (str): The error message to display.
        """
        super().__init__(message)
        self.profile = profile

    def __str__(self) -> str:
        """Return a formatted string representation of the error."""
        return f'Error in profile "{self.profile}": "{self.message}"'


class StorageFileLockError(StorageError):
    """Raised when the storage file lock cannot be acquired.

    This indicates that another instance of the program is already running and
    holding the lock, preventing concurrent access to the configuration storage.
    """

    def __init__(self) -> None:
        """Initialize the exception with a predefined message."""
        super().__init__('Another instance is currently running.')


class ValidationError(ValueError):
    """Raised when a git profile key or value is invalid.

    This is used instead of a generic ValueError to allow
    targeted error handling in CLI commands.
    """

    def __init__(self, key: str, value: str, message: str) -> None:
        """Initialize a ValidationError.

        Args:
            key (str): Git config key.
            value (str): Invalid value.
            message (str): Error description.
        """
        super().__init__()
        self.key = key
        self.value = value
        self.message = message

    def __str__(self) -> str:
        return f'Invalid key/value pair: "{self.key}"="{self.value}": "{self.message}"'


class Validator:
    """Validator for git profile keys and values.

    Enforces a whitelist of safe keys and validates values to prevent injection or
    invalid data.
    """

    KEY_EMAIL = 'user.email'

    SAFE_KEYS: ClassVar[list[str]] = [
        'user.name',
        KEY_EMAIL,
        'user.signingkey',
        'commit.gpgsign',
        'tag.gpgsign',
    ]

    VALUES_INVALID_CHAR: ClassVar[list[str]] = ['\r', '\n']

    # https://html.spec.whatwg.org/multipage/input.html#valid-e-mail-address
    EMAIL_REGEX = re.compile(
        r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
    )

    @classmethod
    def validate_key_value(cls, key: str, value: str) -> None:
        """Validate a git configuration key-value pair.

        Ensures that:
        1. The key is in the allowed whitelist (`SAFE_KEYS`).
        2. The value is valid for the key (e.g., email format for 'user.email').
        3. The value does not contain newline characters.

        Args:
            key (str): Git config key to validate.
            value (str): Value associated with the key.

        Raises:
            ValidationError: If the key is not allowed, the value is invalid,
                             or it contains forbidden characters.
        """
        key_internal = key.lower()

        if key_internal not in cls.SAFE_KEYS:
            raise ValidationError(key, value, 'Key is not allowed for security reasons')

        if key_internal == cls.KEY_EMAIL and not cls.EMAIL_REGEX.fullmatch(value):
            raise ValidationError(key, value, 'Invalid email address')

        for invalid_char in cls.VALUES_INVALID_CHAR:
            if invalid_char in value:
                raise ValidationError(
                    key, value, 'Values must not only contain allowed characters'
                )


class DictMergeConflictError(ValueError):
    """Raised when merging two configurations encounters conflicting keys."""

    def __init__(self, conflicts: ConflictsType) -> None:
        """Initialize DictMergeConflictError.

        Args:
            conflicts (ConflictsType): Mapping of conflicts by profile/key.
        """
        super().__init__()
        self.conflicts = conflicts


P = ParamSpec('P')
R = TypeVar('R')
S = TypeVar('S', bound='Storage')


class Storage:
    """Persistent storage for git profiles.

    Handles loading, saving, and validating profiles as JSON files.

    This class can be used as a context manager which enables transactional (guarantee
    multiple sequential operations) support.
    If only one operation is required, this can also be used as a normal variable.
    """

    STORAGE_FILE_PATH_DEFAULT = (
        PlatformDirs(PROGRAM_NAME).user_data_path / 'config.json'
    )

    def __init__(self, config_file: Path) -> None:
        """Initialize storage and load configuration.

        Args:
            config_file (Path): Path to the JSON config file.
        """
        self.config_file = config_file
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        self._config: ConfigType = {}

        self._file_lock_path = self.config_file.with_suffix('.lock')
        self._file_lock = FileLock(self._file_lock_path, timeout=3, blocking=True)

    def __enter__(self) -> Self:
        """Enter the runtime context for the Storage instance.

        Returns:
            Self: The current `Storage` instance.

        Raises:
            StorageError: If the file lock could not be acquired.
        """
        self._lock_and_load()

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Exit the runtime context and release resources.

        This method is automatically called when the `with` block exits.
        It ensures the file lock is released and the lock file is removed.

        Args:
            exc_type (type[BaseException] | None): Exception type, if raised within the
                                                   context.
            exc_val (BaseException | None): Exception instance, if raised within the
                                            context.
            exc_tb (types.TracebackType | None): Traceback object, if an exception was
                                                 raised.
        """
        self._release()

    def _lock_and_load(self) -> None:
        """Acquire the file lock and load the configuration.

        This method ensures exclusive access to the configuration file
        by acquiring the lock before reading or initializing the configuration.

        If the configuration file does not exist or is empty, a new
        default configuration is created and saved to disk.

        Raises:
            StorageFileLockError: If the file lock cannot be acquired because
                another instance is already running.
            ConfigLoadError: If the configuration file cannot be loaded.
        """
        try:
            self._file_lock.acquire()
        except Timeout as e:
            raise StorageFileLockError from e

        self._config = self._load(self.config_file)
        if self._config == {}:
            self._save()

    @staticmethod
    def with_file_lock(
        func: Callable[Concatenate[S, P], R],
    ) -> Callable[Concatenate[S, P], R]:
        """Decorator to ensure that the file lock is acquired during method execution.

        This decorator can be applied to any method that interacts with
        the configuration file to guarantee thread/process-safe access.

        - If the lock is **already held** (e.g., inside a context manager),
          the function executes directly.
        - If the lock is **not held**, it is automatically acquired before
          executing the function and released afterward.

        Args:
            func (types.FunctionType): The method to wrap with locking behavior.

        Returns:
            types.FunctionType: The wrapped function that ensures the lock
            is acquired and released correctly.

        Raises:
            StorageFileLockError: If the file lock cannot be acquired.
        """

        @functools.wraps(func)
        def wrapper(self: S, *args: P.args, **kwargs: P.kwargs) -> R:
            """Wrapper that acquires and releases the file lock as needed."""
            locked_here = False
            if not self._file_lock.is_locked:
                self._lock_and_load()
                locked_here = True

            try:
                return func(self, *args, **kwargs)
            finally:
                if locked_here:
                    self._release()

        return cast('Callable[Concatenate[S, P], R]', wrapper)

    def _release(self) -> None:
        """Safely release the file lock and delete the lock file."""
        self._file_lock.release()
        self._file_lock_path.unlink()

    @property
    @with_file_lock
    def config(self) -> ConfigType:
        """Return a copy of the current configuration.

        Returns:
            ConfigType: Copy of the profiles' dictionary.

        Raises:
            StorageError: If another instance is running and file lock cannot be
                          acquired or the config file cannot be loaded.
        """
        return self._config.copy()

    @staticmethod
    def _load(file: Path) -> ConfigType:
        """Load and validate the configuration from disk.

        Args:
            file (Path): Path to JSON config file.

        Returns:
            ConfigType: Loaded config data.

        Raises:
            ConfigLoadError: If the file is invalid JSON, schema fails,
                             or contains unsafe keys/values.
        """
        if not file.is_file():
            return {}

        config_text = file.read_text()
        if config_text == '':
            return {}

        try:
            validated = ConfigModel.model_validate_json(config_text, strict=True)

            for profile_name, profile_data in validated.model_dump().items():
                try:
                    for key, value in profile_data.items():
                        Validator.validate_key_value(key, value)
                except ValidationError as e:  # noqa: PERF203
                    raise StorageProfileError(profile_name, str(e)) from e

        except (StorageProfileError, PydanticValidationError) as e:
            raise ConfigLoadError(file, str(e)) from e

        return {name: profile.root for name, profile in validated.root.items()}

    def _save(self) -> None:
        """Atomically save the configuration to disk."""
        data = json.dumps(self._config)

        tmp_dir = self.config_file.parent
        with tempfile.NamedTemporaryFile('w', dir=tmp_dir, delete=False) as temp_file:
            temp_file.write(data)
            tmp_path = Path(temp_file.name)

        tmp_path.replace(self.config_file)

    def _ensure_profile_exists(self, profile_name: str) -> None:
        """Ensure that the profile exists."""
        if profile_name not in self._config:
            raise StorageProfileError(profile_name, 'Profile does not exist')

    @with_file_lock
    def set(self, profile_name: str, key: str, value: str) -> bool:
        """Set a key=value pair in a profile.

        Args:
            profile_name (str): The profile to update or create.
            key (str): Git config key.
            value (str): Git config value.

        Returns:
            bool: True if a new profile was created, False if updated.

        Raises:
            StorageError: If key/value are invalid, another instance is running and
                          file lock cannot be acquired or the config file cannot be
                          loaded.
        """
        try:
            Validator.validate_key_value(key, value)
        except ValidationError as e:
            raise StorageProfileError(profile_name, str(e)) from e

        added_profile = False

        if profile_name not in self._config:
            self._config[profile_name] = {}
            added_profile = True

        self._config[profile_name][key] = value
        self._save()

        return added_profile

    @with_file_lock
    def unset(self, profile_name: str, key: str) -> None:
        """Remove a key from a profile.

        Args:
            profile_name (str): Profile name.
            key (str): Key to remove.

        Raises:
            StorageError: If the profile does not exist, another instance is running
                          and file lock cannot be acquired or the config file cannot be
                          loaded.
        """
        self._ensure_profile_exists(profile_name)
        self._config[profile_name].pop(key, None)
        self._save()

    @with_file_lock
    def get_profile(self, profile_name: str) -> ProfileType:
        """Get all key-value pairs of a profile.

        Args:
            profile_name (str): Profile name.

        Returns:
            ProfileType: The profile's key-value data.

        Raises:
            StorageError: If the profile does not exist, another instance is running
                          and file lock cannot be acquired or the config file cannot be
                          loaded.
        """
        self._ensure_profile_exists(profile_name)
        return self._config[profile_name]

    @with_file_lock
    def remove(self, profile_name: str) -> None:
        """Remove an entire profile.

        Args:
            profile_name (str): Profile name.

        Raises:
            StorageError: If the profile does not exist, another instance is running
                          and file lock cannot be acquired or the config file cannot be
                          loaded.
        """
        self._ensure_profile_exists(profile_name)
        del self._config[profile_name]
        self._save()

    @with_file_lock
    def export_storage(self, dest: Path) -> None:
        """Export current configuration to a file.

        Args:
            dest (Path): Destination path for export.

        Raises:
            FileExistsError: If destination file already exists.
            StorageError: If another instance is running and file lock cannot be
                          acquired or the config file cannot be loaded.
        """
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.is_file():
            raise FileExistsError

        dest.write_text(json.dumps(self._config))

    @with_file_lock
    def import_storage(self, src: Path, *, force: bool) -> None:
        """Import configuration from a file.

        Args:
            src (Path): Source file to import.
            force (bool): If True, overwrite existing config. Otherwise, merge.

        Raises:
            StorageError: If another instance is running and file lock cannot be
                          acquired or the config file cannot be loaded.
            FileNotFoundError: If source file does not exist.
            DictMergeConflictError: If merge conflicts occur and force=False.
        """
        if not src.is_file():
            raise FileNotFoundError

        imported_config = self._load(src)
        self._config = (
            imported_config
            if force
            else self._merge_config(self._config.copy(), imported_config.copy())
        ).copy()
        self._save()

    @staticmethod
    def _merge_config(config1: ConfigType, config2: ConfigType) -> ConfigType:
        """Merge two configuration dictionaries.

        Args:
            config1 (ConfigType): Existing config.
            config2 (ConfigType): New config to merge.

        Returns:
            ConfigType: Merged configuration.

        Raises:
            DictMergeConflictError: If conflicting keys are found.
        """
        conflicts: ConflictsType = {}

        duplicated_profile_names = config1.keys() & config2.keys()
        for duplicated_profile_name in duplicated_profile_names:
            duplicated_keys = (
                config1[duplicated_profile_name].keys()
                & config2[duplicated_profile_name].keys()
            )

            if len(duplicated_keys) > 0:
                conflicts[duplicated_profile_name] = {}
                for duplicated_key in duplicated_keys:
                    value1 = config1[duplicated_profile_name][duplicated_key]
                    value2 = config2[duplicated_profile_name][duplicated_key]
                    if value1 != value2:
                        conflicts[duplicated_profile_name][duplicated_key] = (
                            value1,
                            value2,
                        )
                if len(conflicts[duplicated_profile_name].keys()) == 0:
                    conflicts.pop(duplicated_profile_name)

        if len(conflicts.keys()) > 0:
            raise DictMergeConflictError(conflicts.copy())

        for profile_name, new_entries in config2.items():
            if profile_name not in config1:
                config1[profile_name] = new_entries.copy()
            else:
                config1[profile_name].update(new_entries)

        return config1
