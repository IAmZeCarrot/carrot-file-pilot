# Carrot File Pilot

A safety-first desktop and command-line organizer for Windows downloads and other busy folders. It always previews first, never deletes files, never silently overwrites, and records applied moves in an undo journal.

The interface uses Python's built-in native GUI toolkit, while all planning and filesystem work stays in the same cross-platform, tested core as the CLI.

## Desktop app

After installing from source, launch the native interface:

```powershell
carrot-file-pilot-gui
```

Or download the `CarrotFilePilot-Windows` artifact from a successful **Build Windows app** workflow run. Release builds use the same workflow to produce a single `CarrotFilePilot.exe`.

The desktop workflow is deliberately two-step:

1. Choose a folder and optionally a custom rules file.
2. Click **Preview**. No files move.
3. Inspect every source, destination, rule, collision rename, and skipped item.
4. Click **Organize previewed files** and confirm.
5. Use **Undo last run** or select an earlier JSON journal if needed.

Changing the folder or rules invalidates the preview, so the new inputs must be previewed again. Journals are stored under `%LOCALAPPDATA%\CarrotFilePilot\journals` on Windows.

## Safety guarantees

- Opening the app and previewing never moves files.
- Apply is unavailable until a preview contains at least one planned move.
- Never deletes files and never silently overwrites.
- Existing names become `name (1).ext`, `name (2).ext`, and so on, or are skipped by configuration.
- A destination that appears between preview and execution causes that move to fail.
- Undo refuses to replace anything at the original path.
- Destination folders are excluded from recursive scans.
- Every applied transaction has a machine-readable journal.
- Partial apply and undo failures remain visible instead of being hidden.

Always keep independent backups for irreplaceable files. A journal helps reverse successful moves, but it is not a backup.

## Install from source

Python 3.10 or newer is required.

```powershell
git clone https://github.com/IAmZeCarrot/carrot-file-pilot.git
cd carrot-file-pilot
py -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
.venv\Scripts\carrot-file-pilot-gui.exe
```

The package is not currently published to PyPI. The commands above install the checked-out source locally.

## Command line

The CLI remains available for repeatable or scripted organization. Its default is also a dry run.

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

Choose a JSON file in the desktop app or pass `--config rules.json` to the CLI. See [examples/rules.json](examples/rules.json). `collision` is `rename` or `skip`; `recursive` and `include_hidden` are booleans; and ordered rules use a name, relative destination, and filename or extension matches. Destinations cannot contain `..`. Matching is case-insensitive and the first rule wins. Unknown fields are errors.

## Journals and undo

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

CI runs formatting, linting, strict typing, tests, and package builds across supported Python versions, including a Windows test job. The manually triggered Windows workflow packages the GUI with PyInstaller. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## Limitations

- The current executable artifact is unsigned, so Windows SmartScreen may show a warning.
- The desktop interface runs file operations on the UI thread; exceptionally large folders may briefly appear busy while scanning.
- Rules match filenames and extensions only; they do not inspect contents or metadata.
- Permission, lock, disk, drive, and concurrent-change errors are reported and journaled, but moves are not an all-or-nothing filesystem transaction.
- Undo cannot restore a changed, removed, or replaced file and refuses occupied original paths.
- Empty destination folders are not removed during undo.
- Symlinked files are not followed because candidates must be regular files.

## License

MIT
