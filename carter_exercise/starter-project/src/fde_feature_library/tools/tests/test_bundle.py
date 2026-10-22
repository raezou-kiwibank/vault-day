"""Conformance tests for the published Feature Knowledge Bundle.

The bundle claims to conform to Open Knowledge Format v0.2. A claim of
conformance that nothing checks is just a comment, so these tests assert the
spec's three conformance rules directly against the generated tree, plus the
navigation and link-integrity rules the bundle's own profile adds.

They also assert the property that makes the bundle trustworthy: it is
reproducible. Generating twice must produce identical bytes, so CI can
regenerate into a temporary directory and fail on any diff against what is
committed.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fl import bundle, yamlite  # noqa: E402

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BUNDLE_ROOT = os.path.join(REPO_ROOT, "knowledge")
RESERVED = {"index.md", "log.md"}


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Split an OKF document into frontmatter and body.

    Args:
        text: The document text.

    Returns:
        ``(frontmatter, body)``.

    Raises:
        AssertionError: If the document has no terminated frontmatter block.
    """
    assert text.startswith("---\n"), "document must open with a frontmatter fence"
    end = text.find("\n---\n", 3)
    assert end > 0, "frontmatter fence is not terminated"
    return yamlite.loads(text[4:end]), text[end + 5 :]


def bundle_documents(root: str) -> list[str]:
    """List every markdown document in a bundle.

    Args:
        root: Bundle root.

    Returns:
        Sorted document paths.
    """
    found: list[str] = []
    for dirpath, _, filenames in os.walk(root):
        found.extend(os.path.join(dirpath, f) for f in filenames if f.endswith(".md"))
    return sorted(found)


def generate(out_dir: str) -> None:
    """Run the bundle generator into a directory.

    Args:
        out_dir: Destination, relative to the repository root.
    """
    env = dict(os.environ, PYTHONPATH=os.path.join(REPO_ROOT, "tools"))
    subprocess.run(
        [sys.executable, "-m", "fl", "bundle", "--out", out_dir],
        cwd=REPO_ROOT, env=env, check=True, capture_output=True,
    )


@unittest.skipUnless(os.path.isdir(BUNDLE_ROOT), "bundle not generated; run `make fl-bundle`")
class OkfConformanceTests(unittest.TestCase):
    """The three conformance rules from OKF v0.2 §Conformance."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.docs = bundle_documents(BUNDLE_ROOT)

    def test_bundle_is_not_empty(self) -> None:
        self.assertGreater(len(self.docs), 50)

    def test_rule_1_every_document_has_parseable_frontmatter(self) -> None:
        for path in self.docs:
            with self.subTest(path=os.path.relpath(path, BUNDLE_ROOT)):
                with open(path, "r", encoding="utf-8") as fh:
                    fm, _ = split_frontmatter(fh.read())
                self.assertIsInstance(fm, dict)

    def test_rule_2_every_frontmatter_has_a_non_empty_type(self) -> None:
        for path in self.docs:
            with self.subTest(path=os.path.relpath(path, BUNDLE_ROOT)):
                with open(path, "r", encoding="utf-8") as fh:
                    fm, _ = split_frontmatter(fh.read())
                self.assertTrue(fm.get("type"), "type must be present and non-empty")

    def test_rule_3_reserved_filenames_are_indexes(self) -> None:
        for path in self.docs:
            if os.path.basename(path) not in RESERVED:
                continue
            with self.subTest(path=os.path.relpath(path, BUNDLE_ROOT)):
                with open(path, "r", encoding="utf-8") as fh:
                    fm, _ = split_frontmatter(fh.read())
                self.assertEqual(fm.get("type"), bundle.TYPE_INDEX)


@unittest.skipUnless(os.path.isdir(BUNDLE_ROOT), "bundle not generated; run `make fl-bundle`")
class BundleProfileTests(unittest.TestCase):
    """Rules this bundle's own profile adds on top of bare OKF."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.docs = bundle_documents(BUNDLE_ROOT)

    def test_okf_version_survives_a_round_trip_as_a_string(self) -> None:
        # "0.2" emitted unquoted parses back as the float 0.2 and the version
        # claim silently becomes wrong.
        for path in self.docs:
            with open(path, "r", encoding="utf-8") as fh:
                fm, _ = split_frontmatter(fh.read())
            with self.subTest(path=os.path.relpath(path, BUNDLE_ROOT)):
                self.assertEqual(fm.get("okf_version"), "0.2")
                self.assertIsInstance(fm.get("okf_version"), str)

    def test_every_directory_carries_an_index(self) -> None:
        missing = [
            os.path.relpath(d, BUNDLE_ROOT)
            for d, _, files in os.walk(BUNDLE_ROOT)
            if "index.md" not in files
        ]
        self.assertEqual(missing, [], "OKF navigation requires an index per directory")

    def test_internal_links_resolve(self) -> None:
        broken: list[str] = []
        for path in self.docs:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
            for match in re.finditer(r"\]\((/[^)\s]+\.md)\)", text):
                target = os.path.join(BUNDLE_ROOT, match.group(1).lstrip("/"))
                if not os.path.isfile(target):
                    broken.append(f"{os.path.relpath(path, BUNDLE_ROOT)} -> {match.group(1)}")
        self.assertEqual(broken, [])

    def test_llms_txt_is_published(self) -> None:
        path = os.path.join(BUNDLE_ROOT, "llms.txt")
        self.assertTrue(os.path.isfile(path))
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        self.assertTrue(text.startswith("# "), "llms.txt must open with an H1")
        self.assertIn("\n> ", text, "llms.txt must carry a blockquote summary")

    def test_feature_documents_declare_their_source_and_hash(self) -> None:
        for path in self.docs:
            with open(path, "r", encoding="utf-8") as fh:
                fm, _ = split_frontmatter(fh.read())
            if fm.get("type") != bundle.TYPE_FEATURE:
                continue
            with self.subTest(path=os.path.relpath(path, BUNDLE_ROOT)):
                source = (fm.get("identity") or {}).get("source_path")
                self.assertTrue(source)
                self.assertTrue(os.path.isfile(os.path.join(REPO_ROOT, source)))
                digest = (fm.get("version") or {}).get("content_hash", "")
                self.assertTrue(digest.startswith("sha256:"))
                self.assertEqual(
                    digest, bundle.digest_of_file(os.path.join(REPO_ROOT, source)),
                    "content_hash must match the source it describes",
                )

    def test_every_document_carries_the_generated_marker(self) -> None:
        for path in self.docs:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
            with self.subTest(path=os.path.relpath(path, BUNDLE_ROOT)):
                self.assertIn(bundle.GENERATED_END, text)


class ReproducibilityTests(unittest.TestCase):
    """The bundle must be byte-identical between runs, so CI can diff it."""

    def test_generating_twice_produces_identical_output(self) -> None:
        tmp = tempfile.mkdtemp(dir=REPO_ROOT, prefix=".bundle-check-")
        try:
            rel = os.path.relpath(tmp, REPO_ROOT)
            generate(os.path.join(rel, "a"))
            generate(os.path.join(rel, "b"))
            a_docs = bundle_documents(os.path.join(tmp, "a"))
            b_root = os.path.join(tmp, "b")
            self.assertGreater(len(a_docs), 50)
            for path in a_docs:
                counterpart = os.path.join(b_root, os.path.relpath(path, os.path.join(tmp, "a")))
                with self.subTest(doc=os.path.relpath(path, os.path.join(tmp, "a"))):
                    self.assertTrue(os.path.isfile(counterpart))
                    with open(path, "rb") as fa, open(counterpart, "rb") as fb:
                        self.assertEqual(fa.read(), fb.read())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_hand_written_prose_survives_regeneration(self) -> None:
        note = "## Operator note\n\nThis paragraph was written by a human."
        tmp = tempfile.mkdtemp(dir=REPO_ROOT, prefix=".bundle-check-")
        try:
            rel = os.path.relpath(tmp, REPO_ROOT)
            generate(os.path.join(rel, "c"))
            target = os.path.join(
                tmp, "c", "features", "deposit", "interest", "interest_accrual.md"
            )
            self.assertTrue(os.path.isfile(target))
            with open(target, "a", encoding="utf-8") as fh:
                fh.write("\n" + note + "\n")
            generate(os.path.join(rel, "c"))
            with open(target, "r", encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn(note, text, "prose below the generated marker must be preserved")
            self.assertEqual(text.count(note), 1, "preserved prose must not be duplicated")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class DocumentationPreservationTests(unittest.TestCase):
    """`fl docs` must never destroy prose a human wrote."""

    def test_the_one_hand_written_page_survives_generation(self) -> None:
        # lending/disbursal/documentation/disbursement.md predates the generator
        # and carries mermaid diagrams and business tables written by hand.
        page = os.path.join(
            REPO_ROOT, "feature_library", "src", "feature_library", "lending",
            "disbursal", "documentation", "disbursement.md",
        )
        self.assertTrue(os.path.isfile(page))
        with open(page, "r", encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("Disbursement Feature Overview", text,
                      "the authored heading must still be present")
        self.assertIn("sequenceDiagram", text,
                      "the authored sequence diagram must still be present")
        self.assertIn(bundle.GENERATED_END, text)
        self.assertEqual(text.count(bundle.GENERATED_END), 1,
                         "regeneration must not stack markers")


if __name__ == "__main__":
    unittest.main(verbosity=2)
