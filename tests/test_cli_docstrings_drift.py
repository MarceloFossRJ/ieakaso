"""Every CLI documents its exit codes (issue #90). Reads the real repo; never writes to it.

A CLI is a module under src/ieakaso/ with a top-level `main`. Its module docstring needs an `Exit codes`
sentence naming every integer literal `main` itself returns; codes returned through a helper are not seen.
"""

import ast
import re
from pathlib import Path

from conftest import write_files

SRC = Path(__file__).resolve().parents[1] / "src/ieakaso"


def cli_modules(src: Path) -> list[tuple[Path, ast.Module, ast.FunctionDef]]:
    """Every module under src with a top-level `main`, with its syntax tree and that function."""
    found = []
    for path in sorted(src.rglob("*.py")):
        tree = ast.parse(path.read_text())
        main = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"), None)
        if main is not None:
            found.append((path, tree, main))
    return found


def returned_codes(main: ast.FunctionDef) -> set[int]:
    """The integer literals main itself returns, not those of functions nested in it."""
    codes, todo = set(), list(main.body)
    while todo:
        node = todo.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            continue
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) and type(node.value.value) is int:
            codes.add(node.value.value)
        todo.extend(ast.iter_child_nodes(node))
    return codes


def exit_codes_sentence(docstring: str) -> str | None:
    """From `Exit codes` to the end of its paragraph: numbers before it (an ADR, a count) are not codes."""
    paragraph = next((p for p in re.split(r"\n\s*\n", docstring) if "Exit codes" in p), None)
    return None if paragraph is None else paragraph[paragraph.index("Exit codes") :]


def problems(src: Path) -> list[str]:
    found = []
    for path, tree, main in cli_modules(src):
        where = path.relative_to(src).as_posix()
        sentence = exit_codes_sentence(ast.get_docstring(tree) or "")
        if sentence is None:
            found.append(f"{where}: no `Exit codes` sentence in the module docstring")
            continue
        named = {int(n) for n in re.findall(r"\b\d+\b", sentence)}
        for code in sorted(returned_codes(main) - named):
            found.append(f"{where}: `main` returns {code}, which the `Exit codes` sentence doesn't name")
    return found


def test_a_cli_without_an_exit_codes_sentence_is_reported(tmp_path: Path):
    write_files(tmp_path, {"tool/cli.py": '"""Does a thing."""\n\n\ndef main(argv=None):\n    return 0\n'})

    assert problems(tmp_path) == ["tool/cli.py: no `Exit codes` sentence in the module docstring"]


CLI_RETURNING_4 = '''"""Copies 4 files.

Exit codes: 0 done, 1 bad input.
"""


def main(argv=None):
    if argv:
        return 1
    if argv == []:
        return 4
    return 0
'''


def test_a_returned_code_the_sentence_does_not_name_is_reported(tmp_path: Path):
    write_files(tmp_path, {"tool/cli.py": CLI_RETURNING_4})

    assert problems(tmp_path) == ["tool/cli.py: `main` returns 4, which the `Exit codes` sentence doesn't name"]


def test_codes_returned_through_a_helper_and_modules_without_main_are_not_checked(tmp_path: Path):
    write_files(
        tmp_path,
        {
            "tool/cli.py": '"""Exit codes: 0 done."""\n\n\ndef run():\n    return 7\n\n\ndef main(argv=None):\n    return run()\n',
            "tool/helpers.py": '"""No main here."""\n\n\ndef count():\n    return 3\n',
        },
    )

    assert problems(tmp_path) == []


def test_a_number_before_the_exit_codes_sentence_does_not_count(tmp_path: Path):
    cli = '"""Opens it (ADR 13). Exit codes: 0 done."""\n\n\ndef main(argv=None):\n    if argv:\n        return 13\n    return 0\n'
    write_files(tmp_path, {"tool/cli.py": cli})

    assert problems(tmp_path) == ["tool/cli.py: `main` returns 13, which the `Exit codes` sentence doesn't name"]

def test_every_cli_documents_its_exit_codes():
    assert problems(SRC) == []
