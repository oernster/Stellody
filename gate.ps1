# Every check, run against the project's own virtual environment.
#
# It exists because the environment the checks ran in drifted from the one the
# application runs in, with nothing noticing. PyAV was installed into the system
# Python while `python main.py` used the venv, so the whole suite reported green
# while M4A could not be played at all: the gate was testing a machine nobody
# was using. Naming the interpreter here is what stops the two coming apart.
#
# Each step reads its own exit code rather than its output. A coverage-gated
# pytest prints a coverage table last and no summary line, so the text says
# nothing useful about whether it passed.

$ErrorActionPreference = "Stop"
$env:QT_QPA_PLATFORM = "offscreen"

$python = Join-Path $PSScriptRoot "venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "No virtual environment at $python. Create one, then: venv\Scripts\python.exe -m pip install -r requirements-dev.txt" }

Write-Output "Running the gate with $python"

& $python -m black --check .
if ($LASTEXITCODE -ne 0) { throw "black would reformat files" }

& $python -m flake8
if ($LASTEXITCODE -ne 0) { throw "flake8 found problems" }

& $python -m ruff check .
if ($LASTEXITCODE -ne 0) { throw "ruff found problems" }

& $python -m pytest tests
if ($LASTEXITCODE -ne 0) { throw "the test suite failed" }

Write-Output "Gate green."
