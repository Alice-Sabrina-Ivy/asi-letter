from __future__ import annotations

import os
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.find_latest_ots import find_latest_ots, _format_outputs


class FindLatestOtsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.tmp_path = Path(self.tmp.name)

    def create_file(self, name: str, *, mtime: float | None = None) -> Path:
        path = self.tmp_path / name
        path.write_text("sample")
        ts = mtime if mtime is not None else time.time()
        os.utime(path, (ts, ts))
        return path

    def test_selects_newest_file_by_mtime(self) -> None:
        base_time = 1_700_000_000
        files = [
            self.create_file("letter-old.ots", mtime=base_time),
            self.create_file("letter-newer.ots", mtime=base_time + 10),
            self.create_file("letter-newest.ots", mtime=base_time + 20),
        ]

        latest = find_latest_ots(self.tmp_path)
        self.assertEqual(latest.basename, files[-1].name)

    def test_version_extraction_cases(self) -> None:
        base_time = 1_700_100_000
        cases = [
            ("alpha.md.asc.ots", "alpha.md.asc", "alpha"),
            ("beta.md.ots", "beta.md", "beta.md"),
            ("gamma.asc.ots", "gamma.asc", "gamma.asc"),
            ("delta.ots", "delta", "delta"),
        ]

        created = {name: self.create_file(name, mtime=base_time + idx) for idx, (name, _, _) in enumerate(cases)}

        for idx, (name, expected_noext, expected_version) in enumerate(cases, start=1):
            # bump the mtime to ensure this file is selected as the newest
            mtime = base_time + len(cases) + idx
            path = created[name]
            os.utime(path, (mtime, mtime))

            latest = find_latest_ots(self.tmp_path)
            self.assertEqual(latest.basename, name)
            self.assertEqual(latest.noext, expected_noext)
            self.assertEqual(latest.version, expected_version)

    def test_format_outputs_relative_path(self) -> None:
        path = self.create_file("epsilon.ots")
        latest = find_latest_ots(self.tmp_path)
        outputs = _format_outputs(latest, base_dir=self.tmp_path)
        expected_prefix = f"latest={path.name}"
        self.assertTrue(outputs[0].startswith(expected_prefix))

    def test_raises_when_directory_missing(self) -> None:
        with self.assertRaises(FileNotFoundError):
            find_latest_ots(self.tmp_path / "missing")

    def test_raises_when_no_ots_present(self) -> None:
        empty_dir = self.tmp_path / "empty"
        empty_dir.mkdir()
        with self.assertRaises(FileNotFoundError):
            find_latest_ots(empty_dir)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
