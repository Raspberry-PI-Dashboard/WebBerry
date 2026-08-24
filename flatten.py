#!/usr/bin/env python3

# Usage: py flatten.py ./ -o myproject_ai.py

import ast
import argparse
import keyword
import tokenize
from pathlib import Path
from collections import defaultdict, deque


def is_python_file(path: Path) -> bool:
    return path.suffix == ".py" and path.name != "__pycache__"


def module_name(path: Path, root: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    parts = list(rel.parts)

    if parts[-1] == "__init__":
        parts.pop()

    return ".".join(parts)


def collect_files(root: Path):
    return {
        module_name(path, root): path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
    }


def local_dependencies(tree, current_module, modules):
    deps = set()

    package = current_module.split(".")
    if current_module.endswith(".__init__"):
        package = package[:-1]

    for node in ast.walk(tree):

        # from foo.bar import x
        if isinstance(node, ast.ImportFrom):
            level = node.level
            imported = node.module or ""

            if level:
                base = package[:len(package) - level + 1]
                if imported:
                    base += imported.split(".")
            else:
                base = imported.split(".") if imported else []

            if base:
                candidate = ".".join(base)

                # Exact module
                if candidate in modules:
                    deps.add(candidate)

                # Parent package
                parts = candidate.split(".")
                for i in range(len(parts) - 1, 0, -1):
                    candidate2 = ".".join(parts[:i])
                    if candidate2 in modules:
                        deps.add(candidate2)
                        break

        # import foo.bar
        elif isinstance(node, ast.Import):
            for alias in node.names:
                candidate = alias.name

                if candidate in modules:
                    deps.add(candidate)
                    continue

                parts = candidate.split(".")
                for i in range(len(parts) - 1, 0, -1):
                    candidate2 = ".".join(parts[:i])
                    if candidate2 in modules:
                        deps.add(candidate2)
                        break

    return deps


def strip_docstrings(tree):
    """
    Remove module/class/function docstrings while preserving the AST.
    """
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef,
                             ast.AsyncFunctionDef, ast.ClassDef)):
            if node.body:
                first = node.body[0]
                if (
                    isinstance(first, ast.Expr)
                    and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)
                ):
                    node.body.pop(0)


def remove_comments_and_docstrings(source):
    """
    Remove comments while preserving reasonably readable formatting.
    """
    lines = source.splitlines(keepends=True)

    try:
        tokens = list(tokenize.generate_tokens(iter(lines).__next__))
    except Exception:
        return source

    replacements = []

    for tok in tokens:
        if tok.type == tokenize.COMMENT:
            replacements.append(
                (tok.start, tok.end, "")
            )

    # Apply replacements backwards.
    for start, end, replacement in reversed(replacements):
        sl, sc = start
        el, ec = end

        if sl == el:
            line = lines[sl - 1]
            lines[sl - 1] = line[:sc] + replacement + line[ec:]
        else:
            lines[sl - 1] = lines[sl - 1][:sc] + replacement
            for i in range(sl, el - 1):
                lines[i] = ""
            lines[el - 1] = lines[el - 1][ec:]

    return "".join(lines)


def clean_source(source):
    tree = ast.parse(source)
    strip_docstrings(tree)

    # ast.unparse gives us normalized, readable Python.
    source = ast.unparse(tree)

    # Remove comments that survived.
    source = remove_comments_and_docstrings(source)

    # Remove excessive blank lines.
    output = []
    previous_blank = False

    for line in source.splitlines():
        line = line.rstrip()

        if not line:
            if previous_blank:
                continue
            previous_blank = True
            output.append("")
        else:
            previous_blank = False
            output.append(line)

    return "\n".join(output).strip()


def topological_sort(modules, dependencies):
    """
    Put dependencies before modules that depend on them.
    Cycles are handled gracefully.
    """
    indegree = {m: 0 for m in modules}
    reverse = defaultdict(set)

    for module, deps in dependencies.items():
        for dep in deps:
            if dep not in modules:
                continue

            indegree[module] += 1
            reverse[dep].add(module)

    queue = deque(
        m for m in modules
        if indegree[m] == 0
    )

    result = []

    while queue:
        module = queue.popleft()
        result.append(module)

        for dependent in reverse[module]:
            indegree[dependent] -= 1

            if indegree[dependent] == 0:
                queue.append(dependent)

    # Cyclic modules are appended in stable order.
    for module in modules:
        if module not in result:
            result.append(module)

    return result


def remove_local_imports(source, module, modules):
    """
    Remove imports that point to modules being inlined.
    """
    tree = ast.parse(source)
    lines = source.splitlines()

    remove_lines = set()

    for node in ast.walk(tree):

        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in modules:
                    for line in range(node.lineno, node.end_lineno + 1):
                        remove_lines.add(line)

        elif isinstance(node, ast.ImportFrom):
            imported = node.module or ""

            # Handle relative imports approximately.
            if node.level:
                parts = module.split(".")
                base = parts[:-node.level]

                if imported:
                    base += imported.split(".")

                candidate = ".".join(base)

                if candidate in modules:
                    for line in range(node.lineno, node.end_lineno + 1):
                        remove_lines.add(line)

            elif imported in modules:
                for line in range(node.lineno, node.end_lineno + 1):
                    remove_lines.add(line)

    return "\n".join(
        line for i, line in enumerate(lines, 1)
        if i not in remove_lines
    )


def flatten(root: Path, output: Path):
    modules = collect_files(root)

    if not modules:
        raise RuntimeError("No Python files found.")

    trees = {}
    sources = {}

    for name, path in modules.items():
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)

            trees[name] = tree
            sources[name] = source

        except SyntaxError as e:
            print(f"WARNING: skipping {path}: {e}")

    dependencies = {}

    for name, tree in trees.items():
        dependencies[name] = local_dependencies(
            tree,
            name,
            trees
        )

    order = topological_sort(
        list(trees),
        dependencies
    )

    output_parts = []

    output_parts.append(
        "# ============================================================\n"
        "# AI-FLATTENED PYTHON PROJECT\n"
        f"# Source: {root}\n"
        "# Generated automatically by flatten.py\n"
        "# ============================================================\n"
    )

    for name in order:
        path = modules[name]

        try:
            cleaned = clean_source(sources[name])
            cleaned = remove_local_imports(
                cleaned,
                name,
                modules
            )

            if not cleaned.strip():
                continue

            output_parts.append(
                "\n"
                "# ============================================================\n"
                f"# MODULE: {path.relative_to(root)}\n"
                "# ============================================================\n"
            )

            output_parts.append(cleaned)

        except Exception as e:
            print(f"WARNING: could not process {path}: {e}")

    output.write_text(
        "\n".join(output_parts).rstrip() + "\n",
        encoding="utf-8"
    )

    print(f"Flattened {len(order)} modules")
    print(f"Output: {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Flatten a Python project into one AI-friendly .py file."
    )

    parser.add_argument(
        "project",
        type=Path,
        help="Project directory"
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("project_flat.py"),
        help="Output Python file"
    )

    args = parser.parse_args()

    root = args.project.resolve()

    if not root.is_dir():
        raise SystemExit(
            f"Not a directory: {root}"
        )

    flatten(root, args.output.resolve())


if __name__ == "__main__":
    main()