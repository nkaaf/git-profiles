# git-profiles

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/git-profiles?style=for-the-badge)
![PyPI - License](https://img.shields.io/pypi/l/git-profiles?style=for-the-badge)
![Codecov](https://img.shields.io/codecov/c/github/nkaaf/git-profiles?style=for-the-badge)

![PyPI - Version](https://img.shields.io/pypi/v/git-profiles?style=for-the-badge)
![Homebrew Formula Version](https://img.shields.io/homebrew/v/git-profiles?style=for-the-badge)

A **CLI tool to manage multiple Git configuration profiles**, allowing developers to switch between
different identities and settings quickly. Profiles are stored persistently and can be applied to
local Git repositories with ease.

---

## Features

- Create, update, and delete Git config profiles.
- Set and unset key-value pairs in profiles (`user.name`, `user.email`, etc.).
- Apply a profile to the local Git repository.
- Duplicate existing profiles.
- List all available profiles and show profile contents.
- Cross-platform persistent storage using `platformdirs`.
- Input validation for safe keys and valid emails.
- Quiet mode for scripting or automation.

---

## Installation

### Install from PyPI

The latest stable version is available on PyPI:

```bash
pip install git-profiles
````

### Install via Homebrew (macOS / Linux)

```bash
brew install nkaaf/tap/git-profiles
```

### Development Installation

Clone the repository and install in editable mode using `uv`:

```bash
git clone https://github.com/yourusername/git-profiles.git
cd git-profiles

# Install development dependencies
uv install --dev
```

This allows you to modify the source code while testing.

---

## Usage

After installation (via PyPI, Homebrew, or `uv` dev workflow), the `git-profiles` command is
available globally.

### Set a key-value pair in a profile

```bash
git-profiles set work user.name "Alice Example"
git-profiles set work user.email "alice@example.com"
````

### Remove a key from a profile

```bash
git-profiles unset work user.email
```

### Apply a profile to the local Git repository

```bash
git-profiles apply work
```

This sets all the keys in the `work` profile for the current repository.

### List all available profiles

```bash
git-profiles list
```

### Show all key-values of a profile

```bash
git-profiles show work
```

### Remove an entire profile

```bash
git-profiles remove work
```

### Duplicate a profile

```bash
git-profiles duplicate work personal
```

Creates a copy of the `work` profile named `personal`.

### Quiet mode

```bash
git-profiles -q apply work
```

Suppresses normal output; errors are still printed.

---

**Notes:**

* If installed via **Homebrew** or **PyPI**, the `git-profiles` CLI is automatically on your PATH.
* If installed via the **dev workflow (`uv install --dev`)**, you may need to run it using Python:

```bash
python3 -m git_profiles <command>
```

---

## Options

* `-q`, `--quiet`: Suppress normal output. Errors are still shown.

Example:

```bash
git-profiles -q apply work
```

---

## Development

* Run tests:

```bash
uv run test
```

* Run linter:

```bash
uv run lint
```

---

## License

Apache License 2.0 – see [LICENSE](LICENSE) for details.
