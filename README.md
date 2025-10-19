# git-profiles

[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/nkaaf/git-profiles/main.svg)](https://results.pre-commit.ci/latest/github/nkaaf/git-profiles/main)
![PyPI - Status](https://img.shields.io/pypi/status/git-profiles)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/git-profiles)
![PyPI - License](https://img.shields.io/pypi/l/git-profiles)
![Codecov](https://img.shields.io/codecov/c/github/nkaaf/git-profiles)

![PyPI - Version](https://img.shields.io/pypi/v/git-profiles)

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

> ⚠️ **Note:** The recommended method is via **pipx**. If `pipx` is not installed, you can fall back
> to `pip` or other methods below.

---

### 1️⃣ Recommended: Install via **pipx** (isolated and global CLI)

`pipx` installs Python CLI tools in isolated environments while making them available system-wide.
This prevents conflicts with other Python packages and keeps your environment clean:

```bash
pipx install git-profiles
```

---

### 2️⃣ Alternative: Install via **pip** (inside a virtual environment recommended)

If `pipx` is not available, you can use `pip`. It is recommended to install inside a virtual
environment to avoid polluting your global Python packages:

```bash
# Optional: create a virtual environment
python3 -m venv ~/.venvs/git-profiles
source ~/.venvs/git-profiles/bin/activate

# Install the package
pip install git-profiles
```

---

### 3️⃣ Alternative: Install via **Homebrew** (macOS / Linux)

```bash
brew install nkaaf/tap/git-profiles
```

> ⚡ Makes `git-profiles` globally available. Recommended if you already manage packages with
> Homebrew.

---

### 4️⃣ Development Installation (Editable / Contributing)

Clone the repository and install in **editable mode** using `uv`:

```bash
git clone https://github.com/nkaaf/git-profiles.git
cd git-profiles

# Ensure dependencies match the lockfile
uv sync
```

> ⚡ This allows you to modify the source code while testing. Make sure `uv` is installed; it manages
> dependencies and project commands.

---

## Usage

After installation (via pipx, pip, Homebrew, or the development workflow), you can use
`git-profiles` in **three ways**:

1. **Global CLI (recommended fallback):**

```bash
git-profiles <command>
```

2. **Git alias (preferred and automatically available if Git is installed):**

```bash
git profiles <command>
```

> 💡 **Tip:** The Git alias integrates seamlessly with your workflow and is the most convenient way
> to run commands.

3. **Python module (for development or scripting):**

```bash
python3 -m git_profiles <command>
```

> 💡 Examples below will show both the **global CLI** and **Git alias** variants.

---

### Set a key-value pair in a profile

```bash
git-profiles set work user.name "Alice Example"
git-profiles set work user.email "alice@example.com"

# Git alias equivalent:
git profiles set work user.name "Alice Example"
git profiles set work user.email "alice@example.com"
```

### Remove a key from a profile

```bash
git-profiles unset work user.email

# Git alias equivalent:
git profiles unset work user.email
```

### Apply a profile to the local Git repository

```bash
git-profiles apply work

# Git alias equivalent:
git profiles apply work
```

This sets all the keys in the `work` profile for the current repository.

### List all available profiles

```bash
git-profiles list

# Git alias equivalent:
git profiles list
```

### Show all key-values of a profile

```bash
git-profiles show work

# Git alias equivalent:
git profiles show work
```

### Remove an entire profile

```bash
git-profiles remove work

# Git alias equivalent:
git profiles remove work
```

### Duplicate a profile

```bash
git-profiles duplicate work personal

# Git alias equivalent:
git profiles duplicate work personal
```

Creates a copy of the `work` profile named `personal`.

---

### Options

* `-q`, `--quiet`: Suppress normal output. Errors are still shown.

```bash
git-profiles -q apply work

# Git alias equivalent:
git profiles -q apply work
```

---

## Development

> 💡 **Prerequisite:** Make sure you have **uv installed** on your system. It is the dependency
> manager used to install dev dependencies, manage Python interpreters, and run project commands.

Get your development environment ready in a few steps:

```bash
# 1. Install all development dependencies (pytest, tox, ruff, pre-commit, etc.)
uv sync

# 2. Install pre-commit git hooks
pre-commit install
```

> 💡 After this, your environment is ready to run tests, linting, and builds.

> ⚠️ **Important:** Always run commands via `uv run poe <script>` (e.g., `uv run poe lint`,
`uv run poe test`).
> This ensures the correct uv-managed environment is used. Running `poe` or `tox` directly may fail
> if the environment isn’t active, especially on CI runners.

---

### Linting

```bash
# Run all linting checks
uv run poe lint
```

> ℹ️ This internally runs `pre-commit` using the uv-managed environment.
> 💡 Commits automatically trigger pre-commit hooks after `pre-commit install`.
> If any hook fails (e.g., lint errors), the commit is blocked until fixed.

---

### Testing

```bash
# Run all test environments defined in pyproject.toml
uv run poe test
```

> ℹ️ This internally runs `tox` using the uv-managed environment.
> ⚠️ **Note:** Tox requires the Python interpreters listed in `[tool.tox].envlist`.
> With the `tox-uv` plugin, missing interpreters are installed automatically.
> You can also install specific Python versions manually with `uv python install <version>`.

---

### Building

You can build the `git-profiles` package locally for testing or distribution:

```bash
# Ensure your development environment is synced
uv sync

# Build both wheel and source distribution
uv build
```

> ⚡ Using `uv sync` ensures that all development dependencies are available during the build
> process.

---

### References / Helpful Links

For more information on the tools used in this project, you can visit their official documentation:

* **[uv](https://docs.astral.sh/uv/)** – Dependency manager for Python projects, used here to
  manage dev dependencies and Python interpreters.
* **[tox](https://tox.wiki/)** – Automate testing across multiple Python versions.
* **[pre-commit](https://pre-commit.com/)** – Manage and run pre-commit hooks to ensure code
  quality.
* **[Poe the Poet](https://poethepoet.natn.io/)** – Task runner that simplifies running
  scripts (like `lint` and `test`) defined in `pyproject.toml`.
* **[pipx](https://pipx.pypa.io/stable/)** – Install and run Python CLI tools in isolated
  environments while making them available globally.
* **[Python Packaging Guide](https://packaging.python.org/en/latest/tutorials/packaging-projects/)**
  – Official guide for building, packaging, and distributing Python projects, including creating
  source distributions and wheels.
* **[Homebrew](https://brew.sh/)** – Popular package manager for macOS and Linux, used to install
  CLI tools and dependencies system-wide.

> 💡 These links provide detailed documentation, installation guides, and examples for each tool.
> They’re especially useful if you’re new to Python project tooling.

---

## CI / GitHub Actions

The repository’s CI pipelines automatically run:

* Tests across all Python versions defined in `[tool.tox].envlist`
* Pre-commit hooks for linting and code quality

> ✅ This ensures that every commit and pull request is tested and checked consistently with your
> local development setup.

---

## License

Apache License 2.0 – see [LICENSE](LICENSE) for details.

---

## Acknowledgements

This project depends on the following open source libraries:

- [platformdirs](https://github.com/tox-dev/platformdirs) — MIT License
- [pydantic](https://github.com/pydantic/pydantic) — MIT License
