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

from unittest.mock import patch

from test_git_profiles.common_helpers_test import VALUE_ERROR, execute


def test_git_not_available() -> None:
    with patch('shutil.which', cmd='git', return_value=None):
        ret_val, _stdout, stderr, _config = execute('version')

    assert ret_val == VALUE_ERROR
    assert 'git' in stderr
