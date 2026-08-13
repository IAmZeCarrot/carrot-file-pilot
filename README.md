# Carrot File Pilot

A safety-first command-line organizer for Windows downloads and other busy folders. The default command is a dry run: it shows exactly what would move and changes nothing. Applying a plan records a JSON undo journal.

The core uses Python's cross-platform filesystem APIs and is tested on Linux in addition to being designed for normal Windows paths.

## Safety guarantees

- Dry run unless `--apply` is explicit.
- Never deletes files and never silently overwrites.
- Existing names become `name (1).ext`, `name (2).ext`, and so on, or are skipped by configuration.
- A destination that appears between preview and execution causes that move to fail.
- Undo refuses to replace anything at the original path.
- Destination folders are excluded from recursive scans.
- Every applied transaction has a machine-readable journal; optional logs capture actions and errors.

Always keep independent backups for irreplaceable files. A journal helps reverse successful moves, but it is not a backup.

## Install

Python 3.10 or newer is required.

```powershell
py -m pip install carrot-file-pilot
carrot-file-pilot --version
```

For a source checkout:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -e .
```

## Use

```powershell
carrot-file-pilot organize "$env:USERPROFILE\Downloads"
carrot-file-pilot organize "$env:USERPROFILE\Downloads" --apply --journal-dir "$env:LOCALAPPDATA\CarrotFilePilot\journals" --log-file "$env:LOCALAPPDATA\CarrotFilePilot\pilot.log"
carrot-file-pilot undo "$env:LOCALAPPDATA\CarrotFilePilot\journals\TRANSACTION.json"
```

Exit codes are `0` for success (including a clean dry run), `1` when one or more file actions fail, and `2` for invalid input, configuration, or paths.

## Default organization

| Rule | Destination | Extensions |
|---|---|---|
| documents | `Documents` | doc, docx, odt, pdf, txt |
| images | `Images` | gif, jpeg, jpg, png, svg, webp |
| audio | `Audio` | flac, m4a, mp3, ogg, wav |
| video | `Video` | avi, mkv, mov, mp4, webm |
| archives | `Archives` | 7z, gz, rar, tar, zip |
| spreadsheets | `Spreadsheets` | csv, ods, xls, xlsx |

Unmatched files stay where they are.

## Configuration

Pass `--config rules.json`. See [examples/rules.json](examples/rules.json). `collision` is `rename` or `skip`; `recursive` and `include_hidden` are booleans; and ordered `rules` use a name, relative destination, and filename or extension matches. Destinations cannot contain `..`. Matching is case-insensitive and the first rule wins. Unknown fields are errors.

## Journals, logs, and undo

The journal records absolute source and destination paths, rule names, timestamps, and final statuses. It is updated atomically after each attempted operation so an interrupted run still records completed moves. Treat journals and logs as private because paths can reveal usernames and folder names.

Undo processes successful moves in reverse order. It reports failures and continues restoring independent files. Empty destination directories are retained because deleting directories could remove content the tool did not create.

## Development

```shell
python -m pip install -e ".[dev]" build
ruff format --check .
ruff check .
mypy
pytest
python -m build
```

CI runs formatting, linting, strict typing, tests, and a package build across supported Python versions. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## Limitations

- v1 is a CLI, not a graphical Windows application.
- Rules match filenames and extensions only; they do not inspect contents or metadata.
- Permission, lock, disk, drive, and concurrent-change errors are reported and journaled, but moves are not an all-or-nothing transaction.
- Undo cannot restore a changed, removed, or replaced file and refuses occupied original paths.
- Windows reserved names, path-length policy, and filesystem-specific case behavior surface as move errors.
- Symlinked files are not followed because candidates must be regular files.

## License

MIT
