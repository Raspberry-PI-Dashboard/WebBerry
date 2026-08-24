#!/usr/bin/env python3

"""
Compact Python project flattener for AI/code-analysis use.

Examples:

    python flatten.py ./ -o myproject_ai.py

Recommended:

    python flatten.py ./ \
        --entry myproject.main \
        -o myproject_ai.py

The --entry option restricts the output to modules reachable from
the specified entry module.
"""

import argparse
import ast
import tokenize
from collections import defaultdict, deque
from pathlib import Path


# ============================================================================
# FILE DISCOVERY
# ============================================================================

SKIP_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "build",
    "dist",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}


def collect_files(root: Path, output: Path | None = None):
    """
    Discover Python modules below root.

    The generated output file is explicitly excluded so repeated runs do
    not accidentally flatten the previous flattened file.
    """
    modules = {}

    output_resolved = (
        output.resolve()
        if output is not None
        else None
    )

    for path in root.rglob("*.py"):

        if "__pycache__" in path.parts:
            continue

        if output_resolved and path.resolve() == output_resolved:
            continue

        relative = path.relative_to(root)

        if any(
            part in SKIP_DIRECTORIES
            for part in relative.parts
        ):
            continue

        parts = list(
            relative.with_suffix("").parts
        )

        # package/__init__.py -> package
        if parts and parts[-1] == "__init__":
            parts.pop()

        if not parts:
            continue

        modules[".".join(parts)] = path

    return modules


# ============================================================================
# MODULE / IMPORT RESOLUTION
# ============================================================================

def resolve_relative_import(
    current_module: str,
    node: ast.ImportFrom,
):
    """
    Resolve relative imports.

    Examples:

        myproject.foo
            from .bar import x
            -> myproject.bar

        myproject.foo
            from ..utils import x
            -> utils
    """
    parts = current_module.split(".")

    # Current module's package.
    package = parts[:-1]

    if node.level == 0:
        return node.module or ""

    # level=1 => current package
    # level=2 => parent package
    base_length = len(package) - (node.level - 1)

    if base_length < 0:
        return None

    base = package[:base_length]

    if node.module:
        base.extend(node.module.split("."))

    return ".".join(base)


def find_local_module(
    candidate: str,
    modules,
):
    """
    Find the most specific local module/package matching an import.

    Example:

        candidate = "myproject.utils.helpers"

    may resolve to:

        myproject.utils.helpers
        myproject.utils
        myproject
    """
    if not candidate:
        return None

    if candidate in modules:
        return candidate

    parts = candidate.split(".")

    for i in range(len(parts) - 1, 0, -1):
        name = ".".join(parts[:i])

        if name in modules:
            return name

    return None


def local_dependencies(
    tree,
    current_module,
    modules,
):
    """
    Determine which local modules a module imports.
    """
    dependencies = set()

    for node in ast.walk(tree):

        # ---------------------------------------------------------------
        # import foo
        # import foo.bar
        # ---------------------------------------------------------------

        if isinstance(node, ast.Import):

            for alias in node.names:

                dependency = find_local_module(
                    alias.name,
                    modules,
                )

                if dependency:
                    dependencies.add(dependency)

        # ---------------------------------------------------------------
        # from foo.bar import thing
        # from .foo import thing
        # ---------------------------------------------------------------

        elif isinstance(node, ast.ImportFrom):

            if node.level:
                candidate = resolve_relative_import(
                    current_module,
                    node,
                )
            else:
                candidate = node.module

            if not candidate:
                continue

            dependency = find_local_module(
                candidate,
                modules,
            )

            if dependency:
                dependencies.add(dependency)

    return dependencies


# ============================================================================
# DEPENDENCY GRAPH
# ============================================================================

def reachable_modules(
    entry: str,
    dependencies,
):
    """
    Return the dependency closure starting at entry.
    """
    if entry not in dependencies:
        raise RuntimeError(
            f"Entry module not found: {entry}"
        )

    result = set()
    queue = deque([entry])

    while queue:

        module = queue.popleft()

        if module in result:
            continue

        result.add(module)

        for dependency in dependencies.get(
            module,
            (),
        ):
            if dependency not in result:
                queue.append(dependency)

    return result


def topological_sort(
    modules,
    dependencies,
):
    """
    Put dependencies before modules that use them.

    Cycles are handled gracefully.
    """
    modules = set(modules)

    indegree = {
        module: 0
        for module in modules
    }

    reverse = defaultdict(set)

    for module in modules:

        for dependency in dependencies.get(
            module,
            (),
        ):
            if dependency not in modules:
                continue

            indegree[module] += 1
            reverse[dependency].add(module)

    queue = deque(
        sorted(
            module
            for module in modules
            if indegree[module] == 0
        )
    )

    result = []

    while queue:

        module = queue.popleft()
        result.append(module)

        for dependent in sorted(
            reverse[module]
        ):
            indegree[dependent] -= 1

            if indegree[dependent] == 0:
                queue.append(dependent)

    # Cyclic modules.
    for module in sorted(modules):

        if module not in result:
            result.append(module)

    return result


# ============================================================================
# AST HELPERS
# ============================================================================

def is_docstring(node):
    return (
        isinstance(node, ast.Expr)
        and isinstance(
            node.value,
            ast.Constant,
        )
        and isinstance(
            node.value.value,
            str,
        )
    )


def is_main_guard(node):
    """
    Detect:

        if __name__ == "__main__":
            ...
    """
    if not isinstance(node, ast.If):
        return False

    test = node.test

    if not isinstance(
        test,
        ast.Compare,
    ):
        return False

    if len(test.ops) != 1:
        return False

    if not isinstance(
        test.ops[0],
        ast.Eq,
    ):
        return False

    if len(test.comparators) != 1:
        return False

    left = test.left
    right = test.comparators[0]

    return (
        isinstance(left, ast.Name)
        and left.id == "__name__"
        and isinstance(
            right,
            ast.Constant,
        )
        and right.value == "__main__"
    )


def remove_docstrings(tree):
    """
    Remove module, class and function docstrings.
    """
    for node in ast.walk(tree):

        if isinstance(
            node,
            (
                ast.Module,
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            if (
                node.body
                and is_docstring(node.body[0])
            ):
                node.body.pop(0)


def remove_main_guards(tree):
    """
    Remove CLI/test entry points such as:

        if __name__ == "__main__":
            main()
    """

    statement_containers = (
        ast.Module,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.If,
        ast.With,
        ast.AsyncWith,
        ast.Try,
        ast.ExceptHandler,
    )

    for node in ast.walk(tree):

        if not isinstance(
            node,
            statement_containers,
        ):
            continue

        if not isinstance(
            node.body,
            list,
        ):
            continue

        node.body = [
            child
            for child in node.body
            if not is_main_guard(child)
        ]


# ============================================================================
# LOCAL IMPORT REMOVAL
# ============================================================================

def is_local_import(
    node,
    current_module,
    modules,
):
    """
    Return True if an import points to a module that will be inlined.
    """

    if isinstance(node, ast.Import):

        for alias in node.names:

            if find_local_module(
                alias.name,
                modules,
            ):
                return True

        return False

    if isinstance(
        node,
        ast.ImportFrom,
    ):

        if node.level:
            candidate = resolve_relative_import(
                current_module,
                node,
            )
        else:
            candidate = node.module

        if not candidate:
            return False

        return (
            find_local_module(
                candidate,
                modules,
            )
            is not None
        )

    return False


def remove_local_imports(
    tree,
    current_module,
    modules,
):
    """
    Remove imports from modules that are being flattened into this file.

    External/third-party imports are intentionally preserved.
    """
    containers = (
        ast.Module,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.If,
        ast.With,
        ast.AsyncWith,
        ast.Try,
        ast.ExceptHandler,
    )

    for node in ast.walk(tree):

        if not isinstance(
            node,
            containers,
        ):
            continue

        if not isinstance(
            node.body,
            list,
        ):
            continue

        node.body = [
            child
            for child in node.body
            if not is_local_import(
                child,
                current_module,
                modules,
            )
        ]


# ============================================================================
# OPTIONAL SAFE IMPORT COMPACTION
# ============================================================================

def collect_loaded_names(tree):
    """
    Collect names used in Load context.

    This is intentionally separate from import removal because arbitrary
    unused-import removal can change program behavior.
    """
    names = set()

    for node in ast.walk(tree):

        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
        ):
            names.add(node.id)

    return names


def remove_obviously_unused_imports(tree):
    """
    Conservative unused-import removal.

    This only removes imports whose bound name is definitely unused.

    Wildcard imports are never removed.

    NOTE:
    This is intended for AI context reduction, not guaranteed
    behavior-preserving source transformation.
    """
    used = collect_loaded_names(tree)

    containers = (
        ast.Module,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.If,
        ast.With,
        ast.AsyncWith,
        ast.Try,
        ast.ExceptHandler,
    )

    for node in ast.walk(tree):

        if not isinstance(
            node,
            containers,
        ):
            continue

        if not isinstance(
            node.body,
            list,
        ):
            continue

        new_body = []

        for child in node.body:

            # -----------------------------------------------------------
            # import foo
            # -----------------------------------------------------------

            if isinstance(
                child,
                ast.Import,
            ):
                kept = []

                for alias in child.names:

                    bound_name = (
                        alias.asname
                        if alias.asname
                        else alias.name.split(".")[0]
                    )

                    if bound_name in used:
                        kept.append(alias)

                if kept:
                    child.names = kept
                    new_body.append(child)

                continue

            # -----------------------------------------------------------
            # from foo import bar
            # -----------------------------------------------------------

            if isinstance(
                child,
                ast.ImportFrom,
            ):

                # Never touch wildcard imports.
                if any(
                    alias.name == "*"
                    for alias in child.names
                ):
                    new_body.append(child)
                    continue

                kept = []

                for alias in child.names:

                    bound_name = (
                        alias.asname
                        if alias.asname
                        else alias.name
                    )

                    if bound_name in used:
                        kept.append(alias)

                if kept:
                    child.names = kept
                    new_body.append(child)

                continue

            new_body.append(child)

        node.body = new_body


# ============================================================================
# DUPLICATE DEFINITIONS
# ============================================================================

def definition_key(node):
    """
    Produce a structural key for a top-level class/function.

    Identical definitions can occur because of re-exports or duplicated
    utility code.
    """
    if not isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
            ast.ClassDef,
        ),
    ):
        return None

    try:
        return (
            type(node).__name__,
            node.name,
            ast.dump(
                node,
                include_attributes=False,
            ),
        )
    except Exception:
        return None


def deduplicate_definitions(
    tree,
    seen_definitions,
):
    """
    Remove structurally identical top-level definitions.
    """
    if not isinstance(
        tree,
        ast.Module,
    ):
        return

    result = []

    for node in tree.body:

        key = definition_key(node)

        if key is not None:

            if key in seen_definitions:
                continue

            seen_definitions.add(key)

        result.append(node)

    tree.body = result


# ============================================================================
# COMMENT REMOVAL
# ============================================================================

def remove_comments(source):
    """
    Remove Python comments while retaining string contents.
    """
    lines = source.splitlines(
        keepends=True
    )

    try:
        tokens = list(
            tokenize.generate_tokens(
                iter(lines).__next__
            )
        )
    except Exception:
        return source

    replacements = []

    for token in tokens:

        if token.type == tokenize.COMMENT:
            replacements.append(
                (
                    token.start,
                    token.end,
                )
            )

    for start, end in reversed(
        replacements
    ):

        start_line, start_col = start
        end_line, end_col = end

        if start_line == end_line:

            line = lines[start_line - 1]

            lines[start_line - 1] = (
                line[:start_col]
                + line[end_col:]
            )

        else:

            lines[start_line - 1] = (
                lines[start_line - 1][:start_col]
            )

            for i in range(
                start_line,
                end_line - 1,
            ):
                lines[i] = ""

            lines[end_line - 1] = (
                lines[end_line - 1][end_col:]
            )

    return "".join(lines)


# ============================================================================
# SOURCE NORMALIZATION
# ============================================================================

def normalize_source(source):
    """
    Normalize whitespace after AST unparsing.
    """
    source = remove_comments(source)

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


def clean_module(
    source,
    module,
    selected_modules,
    seen_definitions,
    remove_unused=False,
):
    """
    Parse and compact a module.
    """
    tree = ast.parse(source)

    # Biggest safe reductions.
    remove_docstrings(tree)
    remove_main_guards(tree)

    # Local modules are already emitted elsewhere.
    remove_local_imports(
        tree,
        module,
        selected_modules,
    )

    # Optional and intentionally conservative.
    if remove_unused:
        remove_obviously_unused_imports(tree)

    # Remove exact duplicate definitions.
    deduplicate_definitions(
        tree,
        seen_definitions,
    )

    ast.fix_missing_locations(tree)

    if not tree.body:
        return ""

    source = ast.unparse(tree)

    return normalize_source(source)


# ============================================================================
# FLATTEN
# ============================================================================

def flatten(
    root: Path,
    output: Path,
    entry: str | None = None,
    remove_unused=False,
):
    modules = collect_files(
        root,
        output,
    )

    if not modules:
        raise RuntimeError(
            "No Python files found."
        )

    trees = {}
    sources = {}

    for name, path in modules.items():

        try:

            source = path.read_text(
                encoding="utf-8"
            )

            tree = ast.parse(source)

            trees[name] = tree
            sources[name] = source

        except SyntaxError as error:

            print(
                f"WARNING: skipping "
                f"{path}: {error}"
            )

    # ---------------------------------------------------------------
    # Build dependency graph.
    # ---------------------------------------------------------------

    dependencies = {}

    for name, tree in trees.items():

        dependencies[name] = (
            local_dependencies(
                tree,
                name,
                trees,
            )
        )

    # ---------------------------------------------------------------
    # Select dependency closure.
    # ---------------------------------------------------------------

    if entry:

        if entry not in trees:

            available = "\n".join(
                sorted(trees)
            )

            raise RuntimeError(
                f"Entry module not found: "
                f"{entry}\n\n"
                f"Available modules:\n"
                f"{available}"
            )

        selected = reachable_modules(
            entry,
            dependencies,
        )

    else:
        selected = set(trees)

    # ---------------------------------------------------------------
    # Limit dependency graph to selected modules.
    # ---------------------------------------------------------------

    selected_dependencies = {
        module: {
            dependency
            for dependency in dependencies.get(
                module,
                set(),
            )
            if dependency in selected
        }
        for module in selected
    }

    order = topological_sort(
        selected,
        selected_dependencies,
    )

    # ---------------------------------------------------------------
    # Generate output.
    # ---------------------------------------------------------------

    output_parts = [
        "# ============================================================",
        "# AI-FLATTENED PYTHON PROJECT",
        "# Generated automatically by flatten.py",
        "# ============================================================",
    ]

    seen_definitions = set()

    for name in order:

        path = modules[name]

        try:

            cleaned = clean_module(
                sources[name],
                name,
                selected,
                seen_definitions,
                remove_unused=remove_unused,
            )

            if not cleaned:
                continue

            output_parts.extend(
                [
                    "",
                    "# ============================================================",
                    f"# MODULE: {path.relative_to(root)}",
                    "# ============================================================",
                    "",
                    cleaned,
                ]
            )

        except Exception as error:

            print(
                f"WARNING: could not process "
                f"{path}: {error}"
            )

    result = (
        "\n".join(output_parts).rstrip()
        + "\n"
    )

    output.write_text(
        result,
        encoding="utf-8",
    )

    original_lines = sum(
        source.count("\n") + 1
        for source in sources.values()
        if source
    )

    output_lines = (
        result.count("\n") + 1
    )

    print()
    print("Flatten complete")
    print("----------------")
    print(f"Modules found:    {len(modules)}")
    print(f"Modules included: {len(order)}")
    print(f"Original lines:   {original_lines:,}")
    print(f"Output lines:     {output_lines:,}")
    print(f"Reduction:        {max(0, 100 - (output_lines / max(original_lines, 1) * 100)):.1f}%")
    print(f"Output:           {output}")


# ============================================================================
# CLI
# ============================================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Flatten a Python project into a compact "
            "AI-friendly .py file."
        )
    )

    parser.add_argument(
        "project",
        type=Path,
        help="Project directory",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path(
            "project_flat.py"
        ),
        help="Output Python file",
    )

    parser.add_argument(
        "--entry",
        help=(
            "Entry module, e.g. myproject.main. "
            "Only modules reachable from this module "
            "are included."
        ),
    )

    parser.add_argument(
        "--remove-unused-imports",
        action="store_true",
        help=(
            "Conservatively remove imports whose bound "
            "names are not referenced. May change behavior "
            "for imports with side effects."
        ),
    )

    args = parser.parse_args()

    root = args.project.resolve()
    output = args.output.resolve()

    if not root.is_dir():
        raise SystemExit(
            f"Not a directory: {root}"
        )

    try:

        flatten(
            root=root,
            output=output,
            entry=args.entry,
            remove_unused=(
                args.remove_unused_imports
            ),
        )

    except RuntimeError as error:

        raise SystemExit(
            f"ERROR: {error}"
        )


if __name__ == "__main__":
    main()
