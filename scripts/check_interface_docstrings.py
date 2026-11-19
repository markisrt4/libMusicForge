"""Enforce Doxygen documentation for Python interface declarations."""

from __future__ import annotations

import ast
import re
from pathlib import Path

SOURCE_ROOT = Path("src/musicforge")


def _terminal_name(node: ast.expr) -> str | None:
    """Return the terminal identifier from a name or attribute expression."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_interface(node: ast.ClassDef) -> bool:
    """Return whether a class declares a protocol or abstract interface."""
    if any(_terminal_name(base) in {"Protocol", "ABC"} for base in node.bases):
        return True
    return any(
        isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(
            _terminal_name(decorator) == "abstractmethod"
            for decorator in member.decorator_list
        )
        for member in node.body
    )


def _parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Return all declared parameter names for a callable."""
    args = node.args
    names = [argument.arg for argument in (*args.posonlyargs, *args.args, *args.kwonlyargs)]
    if args.vararg is not None:
        names.append(args.vararg.arg)
    if args.kwarg is not None:
        names.append(args.kwarg.arg)
    return names


def _returns_value(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return whether a callable annotation declares a result."""
    annotation = node.returns
    return not (
        annotation is None
        or isinstance(annotation, ast.Constant) and annotation.value is None
        or isinstance(annotation, ast.Name) and annotation.id == "None"
    )


def _documentation_errors(path: Path) -> list[str]:
    """Return incomplete interface documentation found in one Python file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    errors: list[str] = []
    for interface in (node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)):
        if not _is_interface(interface):
            continue
        symbols: list[tuple[str, ast.AST]] = [(interface.name, interface)]
        symbols.extend(
            (f"{interface.name}.{member.name}", member)
            for member in interface.body
            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        for name, node in symbols:
            location = f"{path}:{node.lineno}: {name}"
            docstring = ast.get_docstring(node, clean=False)
            if docstring is None:
                errors.append(f"{location}: missing docstring")
                continue
            if not docstring.lstrip().startswith("!"):
                errors.append(f'{location}: Doxygen docstring must start with """!')
            if "@brief" not in docstring:
                errors.append(f"{location}: missing @brief")
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for parameter in _parameters(node):
                    pattern = rf"@param(?:\[[^]]+\])?\s+{re.escape(parameter)}\b"
                    if re.search(pattern, docstring) is None:
                        errors.append(f"{location}: missing @param {parameter}")
                if _returns_value(node) and "@return" not in docstring:
                    errors.append(f"{location}: missing @return")
                if not _returns_value(node) and "@return" in docstring:
                    errors.append(f"{location}: unexpected @return for a None return")
    return errors


def documentation_errors(root: Path = SOURCE_ROOT) -> list[str]:
    """Return incomplete documentation from every interface under *root*."""
    errors: list[str] = []
    for path in sorted(root.rglob("*.py")):
        errors.extend(_documentation_errors(path))
    return errors


def main() -> int:
    """Print interface documentation failures and return a CI status code."""
    errors = documentation_errors()
    if not errors:
        print("All Python interfaces have complete Doxygen documentation.")
        return 0
    print("Interface documentation errors:")
    for error in errors:
        print(f"  {error}")
    print(f"\n{len(errors)} interface documentation error(s) found.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
