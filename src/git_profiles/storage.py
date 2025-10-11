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
- Key/value validation and whitelisting.
- Schema validation using Pydantic.
"""

import json
import re
import tempfile
from pathlib import Path
from typing import ClassVar

from platformdirs import PlatformDirs
from pydantic import RootModel
from pydantic import ValidationError as PydanticValidationError

from .const import PROGRAM_NAME

__all__ = ['ConfigLoadError', 'Storage']


class Profile(RootModel[dict[str, str]]):
    """Represents a single profile with key-value settings."""


class ConfigModel(RootModel[dict[str, Profile]]):
    """Root model for the entire configuration (multiple profiles)."""


class ConfigLoadError(Exception):
    """Raised when the config file is invalid or cannot be loaded."""

    def __init__(self, path: Path, message: str) -> None:
        """Initialize a ConfigLoadError.

        Args:
            path (Path): Path to the configuration file that caused the error.
            message (str): Description of the error (e.g., parse or validation failure).
        """
        super().__init__(f"Invalid config file '{path}': {message}")
        self.path = path
        self.message = message


class ValidationError(ValueError):
    """Raised when a git profile key or value is invalid.

    This is used instead of a generic ValueError to allow
    targeted error handling in CLI commands.
    """

    def __init__(self, key: str, value: str, message: str) -> None:
        super().__init__(f'Invalid key/value pair: {key}={value!r}: {message}')
        self.key = key
        self.value = value
        self.message = message


class Validator:
    """Validator for git profile keys and values.

    Enforces a whitelist of safe keys and validates values to prevent injection or
    invalid data.
    """

    SAFE_KEYS: ClassVar = {
        'user.name',
        'user.email',
        'user.signingkey',
        'commit.gpgSign',
        'tag.gpgSign',
    }

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
        if key not in cls.SAFE_KEYS:
            raise ValidationError(key, value, 'Key is not allowed for security reasons')

        if key == 'user.email' and not cls.EMAIL_REGEX.fullmatch(value):
            raise ValidationError(key, value, 'Invalid email address')

        if '\n' in value or '\r' in value:
            raise ValidationError(
                key, value, 'Values must not contain newline characters'
            )


class Storage:
    """Persistent storage for git profiles.

    Handles loading, saving, and validating profiles as JSON files.
    """

    DIRNAME = PROGRAM_NAME.replace('-', '_')
    FILENAME = 'config.json'
    STORAGE_FILE_PATH = PlatformDirs(PROGRAM_NAME).user_data_path / FILENAME

    def __init__(self) -> None:
        """Initialize storage and load configuration."""
        self.STORAGE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._config: dict = self._load() or {}

    @property
    def config(self) -> dict:
        """Return a copy of the current configuration."""
        return self._config.copy()

    @classmethod
    def _load(cls) -> dict[str, dict[str, str]] | None:
        """Load and validate the configuration from disk.

        Returns:
            dict[str, dict[str, str]]: Loaded config data.

        Raises:
            ConfigLoadError: If the file is invalid JSON, schema fails,
                             or contains unsafe keys/values.
        """
        if not cls.STORAGE_FILE_PATH.is_file():
            return None

        try:
            raw_data = json.loads(cls.STORAGE_FILE_PATH.read_text())
            validated = ConfigModel.model_validate(raw_data)

            for profile_data in validated.model_dump().values():
                for key, value in profile_data.items():
                    Validator.validate_key_value(key, value)

        except (json.JSONDecodeError, ValidationError, PydanticValidationError) as e:
            raise ConfigLoadError(cls.STORAGE_FILE_PATH, str(e)) from e

        return validated.model_dump()

    def _save(self) -> None:
        """Atomically save the configuration to disk."""
        data = json.dumps(self.config)

        tmp_dir = self.STORAGE_FILE_PATH.parent
        with tempfile.NamedTemporaryFile('w', dir=tmp_dir, delete=False) as temp_file:
            temp_file.write(data)
            tmp_path = Path(temp_file.name)

        tmp_path.replace(self.STORAGE_FILE_PATH)

    def set(self, profile_name: str, key: str, value: str) -> bool:
        """Set a key=value pair in a profile.

        Args:
            profile_name (str): The profile to update or create.
            key (str): Git config key.
            value (str): Git config value.

        Returns:
            bool: True if a new profile was created, False if updated.

        Raises:
            ValueError: If key/value are invalid.
        """
        Validator.validate_key_value(key, value)

        added_profile = False

        if profile_name not in self._config:
            self._config[profile_name] = {}
            added_profile = True

        self._config[profile_name][key] = value
        self._save()

        return added_profile

    # raises KeyError if profile does not exist
    def unset(self, profile_name: str, key: str) -> None:
        """Remove a key from a profile.

        Args:
            profile_name (str): Profile name.
            key (str): Key to remove.

        Raises:
            KeyError: If the profile does not exist.
        """
        self._config[profile_name].pop(key, None)
        self._save()

    # raises KeyError if profile does not exists
    def get_profile(self, profile_name: str) -> dict[str, str]:
        """Get all key-value pairs of a profile.

        Args:
            profile_name (str): Profile name.

        Returns:
            dict[str, str]: The profile's key-value data.

        Raises:
            KeyError: If the profile does not exist.
        """
        return self._config[profile_name]

    def remove(self, profile_name: str) -> None:
        """Remove an entire profile.

        Args:
            profile_name (str): Profile name.

        Raises:
            KeyError: If the profile does not exist.
        """
        del self._config[profile_name]
        self._save()
