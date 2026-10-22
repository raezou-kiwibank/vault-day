"""A dependency-free reader and writer for the YAML subset this repo uses.

``PyYAML`` is a test-time dependency of the feature library, not a runtime one,
and the tooling here has to run in a pre-commit hook and in CI before any
virtualenv exists. When PyYAML *is* importable this module simply delegates to
it; otherwise it falls back to a parser covering exactly the constructs the
repository's YAML actually contains:

* document markers (``---``) and ``#`` comments
* block mappings and block sequences, nested by indentation
* plain, single- and double-quoted scalars
* literal (``|``) and folded (``>``) block scalars, with chomping indicators
* inline flow sequences of scalars (``[a, b]``)
* ``true``/``false``/``null``/``~`` and numeric coercion

That subset is verified against every ``*.resource.yaml`` in the repository by
``tools/tests/test_yamlite.py``, so the fallback is not taken on trust.
"""

from __future__ import annotations

import json
import re
from typing import Any

try:  # pragma: no cover - exercised implicitly by whichever path is available
    import yaml as _pyyaml
except ImportError:  # pragma: no cover
    _pyyaml = None  # type: ignore[assignment]


_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(r"^[+-]?(\d+\.\d*|\.\d+)([eE][+-]?\d+)?$")


class YamlError(ValueError):
    """Raised when the fallback parser meets input outside its subset."""


# --------------------------------------------------------------------------
# Scalars
# --------------------------------------------------------------------------


def _scalar(text: str) -> Any:
    """Coerce a plain scalar token to a Python value.

    Args:
        text: The raw scalar text, already stripped of surrounding whitespace.

    Returns:
        ``None``, ``bool``, ``int``, ``float`` or ``str`` as appropriate.
    """
    if text == "" or text in {"~", "null", "Null", "NULL"}:
        return None
    if text in {"true", "True", "TRUE"}:
        return True
    if text in {"false", "False", "FALSE"}:
        return False
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        inner = text[1:-1]
        if text[0] == '"':
            try:
                return json.loads(text)
            except ValueError:
                return inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner.replace("''", "'")
    if text.startswith("[") and text.endswith("]"):
        body = text[1:-1].strip()
        if not body:
            return []
        return [_scalar(p.strip()) for p in _split_flow(body)]
    if text.startswith("{") and text.endswith("}"):
        body = text[1:-1].strip()
        if not body:
            return {}
        out: dict[str, Any] = {}
        for part in _split_flow(body):
            k, _, v = part.partition(":")
            out[_scalar(k.strip())] = _scalar(v.strip())  # type: ignore[index]
        return out
    if _INT_RE.match(text):
        return int(text)
    if _FLOAT_RE.match(text):
        return float(text)
    return text


def _split_flow(body: str) -> list[str]:
    """Split a flow collection body on commas that are not inside quotes.

    Args:
        body: The text between the flow delimiters.

    Returns:
        The comma-separated parts, untrimmed.
    """
    parts: list[str] = []
    depth = 0
    quote: str | None = None
    current: list[str] = []
    for ch in body:
        if quote:
            current.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            current.append(ch)
            continue
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
            continue
        current.append(ch)
    if current:
        parts.append("".join(current))
    return parts


def _strip_comment(line: str) -> str:
    """Remove a trailing ``#`` comment that is not inside a quoted scalar.

    Args:
        line: A single source line.

    Returns:
        The line with any comment removed; trailing whitespace is kept so the
        caller can still measure indentation.
    """
    quote: str | None = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i]
    return line


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------


class _Parser:
    """Recursive-descent parser over indentation-significant lines."""

    def __init__(self, text: str) -> None:
        """Initialise the parser.

        Args:
            text: The whole document.
        """
        self.raw = text.splitlines()
        self.i = 0

    # -- line helpers ----------------------------------------------------

    def _peek(self) -> tuple[int, str] | None:
        """Return the next significant line without consuming it.

        Returns:
            ``(indent, content)``, or ``None`` at end of document.
        """
        while self.i < len(self.raw):
            raw = self.raw[self.i]
            stripped = _strip_comment(raw)
            if not stripped.strip():
                self.i += 1
                continue
            if stripped.strip() in {"---", "..."}:
                self.i += 1
                continue
            indent = len(stripped) - len(stripped.lstrip(" "))
            return indent, stripped.strip()
        return None

    def parse(self) -> Any:
        """Parse the document.

        Returns:
            The top-level value, or ``None`` for an empty document.
        """
        head = self._peek()
        if head is None:
            return None
        return self._parse_block(head[0])

    def _parse_block(self, indent: int) -> Any:
        """Parse a mapping or sequence at a given indentation level.

        Args:
            indent: The column the block starts at.

        Returns:
            A ``dict`` or ``list``.
        """
        head = self._peek()
        if head is None:
            return None
        if head[1].startswith("- "):
            return self._parse_sequence(indent)
        if head[1] == "-":
            return self._parse_sequence(indent)
        return self._parse_mapping(indent)

    def _parse_sequence(self, indent: int) -> list[Any]:
        """Parse a block sequence.

        Args:
            indent: The column the ``-`` markers sit at.

        Returns:
            The parsed list.
        """
        items: list[Any] = []
        while True:
            head = self._peek()
            if head is None or head[0] < indent:
                break
            cur_indent, content = head
            if cur_indent > indent:
                raise YamlError(f"unexpected indent in sequence at line {self.i + 1}")
            if not (content == "-" or content.startswith("- ")):
                break
            self.i += 1
            rest = content[1:].strip()
            if not rest:
                nxt = self._peek()
                if nxt is not None and nxt[0] > indent:
                    items.append(self._parse_block(nxt[0]))
                else:
                    items.append(None)
                continue
            if ":" in rest and not _looks_like_scalar_with_colon(rest):
                # An inline mapping opening a sequence item.
                item_indent = cur_indent + 2
                self.raw[self.i - 1] = " " * item_indent + rest
                self.i -= 1
                items.append(self._parse_mapping(item_indent))
                continue
            items.append(_scalar(rest))
        return items

    def _parse_mapping(self, indent: int) -> dict[str, Any]:
        """Parse a block mapping.

        Args:
            indent: The column the keys sit at.

        Returns:
            The parsed mapping.
        """
        out: dict[str, Any] = {}
        while True:
            head = self._peek()
            if head is None or head[0] < indent:
                break
            cur_indent, content = head
            if cur_indent > indent:
                raise YamlError(f"unexpected indent in mapping at line {self.i + 1}")
            if content.startswith("- "):
                break
            key, sep, rest = _split_key(content)
            if not sep:
                raise YamlError(f"expected 'key: value' at line {self.i + 1}: {content!r}")
            self.i += 1
            rest = rest.strip()
            if rest.startswith("|") or rest.startswith(">"):
                out[key] = self._parse_block_scalar(rest, cur_indent)
            elif rest:
                out[key] = _scalar(rest)
            else:
                nxt = self._peek()
                if nxt is not None and nxt[0] > cur_indent:
                    out[key] = self._parse_block(nxt[0])
                elif nxt is not None and nxt[0] == cur_indent and nxt[1].startswith("- "):
                    out[key] = self._parse_sequence(cur_indent)
                else:
                    out[key] = None
        return out

    def _parse_block_scalar(self, header: str, parent_indent: int) -> str:
        """Parse a literal or folded block scalar.

        Args:
            header: The header token (``|``, ``|-``, ``>``, ``>-`` ...).
            parent_indent: Indentation of the key that introduced the scalar.

        Returns:
            The block's text.
        """
        folded = header[0] == ">"
        chomp = ""
        for ch in header[1:]:
            if ch in "+-":
                chomp = ch
        lines: list[str] = []
        block_indent: int | None = None
        while self.i < len(self.raw):
            raw = self.raw[self.i]
            if not raw.strip():
                lines.append("")
                self.i += 1
                continue
            indent = len(raw) - len(raw.lstrip(" "))
            if indent <= parent_indent:
                break
            if block_indent is None:
                block_indent = indent
            lines.append(raw[block_indent:] if len(raw) >= block_indent else "")
            self.i += 1
        while lines and lines[-1] == "":
            lines.pop()
        if folded:
            text = " ".join(line.strip() for line in lines if line.strip())
        else:
            text = "\n".join(lines)
        if chomp == "-":
            return text
        return text + "\n"


def _split_key(content: str) -> tuple[str, bool, str]:
    """Split a mapping line into key and remainder.

    Args:
        content: The trimmed line.

    Returns:
        ``(key, found_separator, remainder)``.
    """
    quote: str | None = None
    for i, ch in enumerate(content):
        if quote:
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            continue
        if ch == ":" and (i + 1 == len(content) or content[i + 1] in " \t"):
            key = content[:i].strip()
            if len(key) >= 2 and key[0] == key[-1] and key[0] in "\"'":
                key = key[1:-1]
            return key, True, content[i + 1 :]
    return content, False, ""


def _looks_like_scalar_with_colon(text: str) -> bool:
    """Whether a sequence item is a scalar that merely contains a colon.

    Args:
        text: The item text after the ``-`` marker.

    Returns:
        True when no ``key: value`` separator is present.
    """
    _, sep, _ = _split_key(text)
    return not sep


def loads(text: str) -> Any:
    """Parse a YAML document.

    Args:
        text: The document source.

    Returns:
        The parsed value.
    """
    if _pyyaml is not None:
        return _pyyaml.safe_load(text)
    return _Parser(text).parse()


def load(path: str) -> Any:
    """Parse a YAML file.

    Args:
        path: Path to the file.

    Returns:
        The parsed value.
    """
    with open(path, "r", encoding="utf-8") as fh:
        return loads(fh.read())


# --------------------------------------------------------------------------
# Emitter
# --------------------------------------------------------------------------


def dumps(value: Any, indent: int = 0) -> str:
    """Serialise a value as block-style YAML.

    The emitter is intentionally simple and stable: keys keep insertion order,
    strings are quoted only when necessary, and multi-line strings become
    literal block scalars. Stability matters because generated manifests are
    committed and diffed.

    Args:
        value: The value to serialise.
        indent: Current indentation depth, used for recursion.

    Returns:
        The YAML text, without a trailing document marker.
    """
    pad = " " * indent
    if isinstance(value, dict):
        if not value:
            return pad + "{}\n"
        out: list[str] = []
        for k, v in value.items():
            if isinstance(v, (dict, list)) and v:
                out.append(f"{pad}{k}:\n")
                out.append(dumps(v, indent + 2))
            elif isinstance(v, (dict, list)):
                out.append(f"{pad}{k}: {'{}' if isinstance(v, dict) else '[]'}\n")
            elif isinstance(v, str) and "\n" in v:
                out.append(f"{pad}{k}: |\n")
                for line in v.rstrip("\n").split("\n"):
                    out.append(f"{pad}  {line}\n" if line else "\n")
            else:
                out.append(f"{pad}{k}: {_emit_scalar(v)}\n")
        return "".join(out)
    if isinstance(value, list):
        if not value:
            return pad + "[]\n"
        out = []
        for item in value:
            if isinstance(item, dict) and item:
                body = dumps(item, indent + 2)
                first, _, rest = body.partition("\n")
                out.append(f"{pad}- {first.strip()}\n")
                if rest.strip():
                    out.append(rest if rest.endswith("\n") else rest + "\n")
            elif isinstance(item, list) and item:
                out.append(f"{pad}-\n")
                out.append(dumps(item, indent + 2))
            else:
                out.append(f"{pad}- {_emit_scalar(item)}\n")
        return "".join(out)
    return pad + _emit_scalar(value) + "\n"


_PLAIN_SAFE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_ ./@+-]*$")


def _emit_scalar(value: Any) -> str:
    """Render a scalar, quoting only when required.

    Args:
        value: The scalar to render.

    Returns:
        The rendered text.
    """
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if text == "":
        return '""'
    if _PLAIN_SAFE.match(text) and text not in {"true", "false", "null", "yes", "no", "on", "off"}:
        if not _INT_RE.match(text) and not _FLOAT_RE.match(text):
            return text
    return json.dumps(text)


def dump(value: Any, path: str, header: str | None = None) -> None:
    """Write a value to a YAML file.

    Args:
        value: The value to serialise.
        path: Destination path.
        header: Optional comment block placed above the document marker.
    """
    with open(path, "w", encoding="utf-8") as fh:
        if header:
            for line in header.strip().split("\n"):
                fh.write(f"# {line}\n" if line else "#\n")
        fh.write("---\n")
        fh.write(dumps(value))
