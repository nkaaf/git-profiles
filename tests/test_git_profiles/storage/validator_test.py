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

import random

import pytest

from git_profiles.storage import ValidationError, Validator
from test_git_profiles.common_helpers_test import FAKER, assert_str_in_str

KEYS = Validator.SAFE_KEYS
KEYS_WITHOUT_EMAIL = [key for key in KEYS.copy() if 'email' not in key]


@pytest.mark.parametrize('key', KEYS_WITHOUT_EMAIL)
def test_validate_keys(key: str) -> None:
    Validator.validate_key_value(key, '')


def test_validate_keys_email() -> None:
    Validator.validate_key_value(Validator.KEY_EMAIL, FAKER.email(safe=True))


def test_validate_keys_bad(subtests: pytest.Subtests) -> None:
    fake_keys = [FAKER.name() for _i in range(100)]

    value = 'value'

    for key in fake_keys:
        with subtests.test(key=key):
            with pytest.raises(ValidationError) as exc:
                Validator.validate_key_value(key, value)

            assert_str_in_str(
                str(exc.value),
                words_exact=[key, value],
                words_norm=['key', 'value'],
            )


def test_validate_keys_case_insensitivity(subtests: pytest.Subtests) -> None:
    fake_keys = [
        ''.join(c.upper() if random.random() < 0.3 else c for c in key)  # noqa: S311
        for key in KEYS_WITHOUT_EMAIL
    ]

    for key in fake_keys:
        with subtests.test(key=key):
            Validator.validate_key_value(key, '')


def test_validate_keys_case_insensitivity_email(subtests: pytest.Subtests) -> None:
    fake_keys = [
        ''.join(c.upper() if random.random() < 0.3 else c for c in Validator.KEY_EMAIL)  # noqa: S311
    ]

    for key in fake_keys:
        with subtests.test(key=key):
            Validator.validate_key_value(key, FAKER.email(safe=True))


def test_email_regex_good_email(subtests: pytest.Subtests) -> None:
    fake_emails = [FAKER.email(safe=False) for _i in range(100)]

    for email in fake_emails:
        with subtests.test(email=email):
            Validator.validate_key_value(Validator.KEY_EMAIL, email)


@pytest.mark.parametrize(
    'email',
    [
        '',  # empty
        'noatsign.example.com',  # missing @
        'double@@example.com',  # two @ symbols
        'missing-domain@',  # nothing after @
        '@missing-local-part.com',  # nothing before @
        'user@.domain',  # domain cannot start with dot
        'user@domain.',  # domain cannot end in dot
        'user@domain..com',  # consecutive dots in domain
        'user@-domain.com',  # domain label cannot start with hyphen
        'user@domain-.com',  # domain label cannot end with hyphen
        'us er@example.com',  # space not allowed
        'user@exa mple.com',  # space not allowed
        'user@exam\nple.com',  # newline disallowed
        'user@exam\tple.com',  # tab disallowed
        'user@ex(ample).com',  # parentheses not allowed
        'user@[127.0.0.1]',  # IP literals not allowed in WHATWG
        'üser@example.com',  # non-ASCII local-part disallowed
        'user@例子.测试',  # non-ASCII domain disallowed
    ],
)
def test_email_regex_bad_email(email: str) -> None:
    with pytest.raises(ValidationError) as exc:
        Validator.validate_key_value(Validator.KEY_EMAIL, email)

    assert_str_in_str(
        str(exc.value),
        words_exact=[Validator.KEY_EMAIL, email],
        words_norm=['email'],
    )


def test_validate_values_invalid_char(subtests: pytest.Subtests) -> None:
    fake_values = [
        ('a' * (int(random.random() * 10))) + c + ('b' * (int(random.random() * 10)))  # noqa: S311
        for c in Validator.VALUES_INVALID_CHAR
    ]

    key = Validator.SAFE_KEYS[0]

    for value in fake_values:
        with subtests.test(value=value):
            with pytest.raises(ValidationError) as exc:
                Validator.validate_key_value(key, value)

            assert_str_in_str(
                str(exc.value),
                words_exact=[key, value],
                words_norm=['char'],
            )
