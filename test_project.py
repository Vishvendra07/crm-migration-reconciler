import unittest
from project import CANONICAL, LEGACY, reconcile, stage_creates


class MigrationTests(unittest.TestCase):
    def test_conflicting_keys_never_auto_match(self):
        result = reconcile(LEGACY, CANONICAL)
        self.assertEqual(result["counts"], {"match": 2, "review": 2, "create": 1})
        self.assertEqual(result["rows"][1]["candidates"], ["c-2", "c-3"])
        self.assertEqual(result["rows"][1]["action"], "review")
        self.assertEqual(result["planned_canonical_after"], 4)

    def test_duplicate_input_identity_requires_review(self):
        duplicate = {**LEGACY[2], "id": "l-duplicate"}
        self.assertEqual(reconcile([LEGACY[2], duplicate], CANONICAL)["counts"], {"review": 2})

    def test_staged_snapshot_reruns_without_writing_a_second_contact(self):
        _, staged = stage_creates(LEGACY, CANONICAL)
        _, repeated = stage_creates(LEGACY, staged)
        self.assertEqual(len(staged), 4)
        self.assertEqual(repeated, staged)
