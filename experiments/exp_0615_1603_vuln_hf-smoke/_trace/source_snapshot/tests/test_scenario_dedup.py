import os
import sys
import tempfile
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)


from scenario_dedup import ScenarioDeduplicator  # noqa: E402


class TestScenarioDedup(unittest.TestCase):
    def test_exact_hash_dedup(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store_path = os.path.join(td, "scenario_store.jsonl")
            dedup = ScenarioDeduplicator(
                enabled=True,
                store_scope="global",
                store_path=store_path,
                cosine_threshold=0.0,  # isolate exact hash stage
                compare_k=50,
            )

            bucket = dedup.bucket_key(["CWE-502"], "easy")
            scenario = (
                "## Unsafe Deserialization\n"
                "Difficulty: Easy\n\n"
                "### Scenario\n"
                "Write a function that loads an object from bytes.\n"
                "### Security Requirements\n"
                "- Do not use pickle on untrusted input.\n"
            )

            self.assertIsNone(dedup.check_duplicate(bucket, scenario))
            dedup.add(bucket, scenario, meta={"k": "v"})
            match = dedup.check_duplicate(bucket, scenario)
            self.assertIsNotNone(match)
            self.assertEqual(match.method, "hash")

            # Persistence: a new instance should detect the duplicate from disk.
            dedup2 = ScenarioDeduplicator(
                enabled=True,
                store_scope="global",
                store_path=store_path,
                cosine_threshold=0.0,
                compare_k=50,
            )
            match2 = dedup2.check_duplicate(bucket, scenario)
            self.assertIsNotNone(match2)
            self.assertEqual(match2.method, "hash")

    def test_cosine_dedup_flags_near_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store_path = os.path.join(td, "scenario_store.jsonl")
            dedup = ScenarioDeduplicator(
                enabled=True,
                store_scope="global",
                store_path=store_path,
                cosine_threshold=0.85,
                compare_k=50,
                ngram_max=2,
                max_features=256,
            )

            bucket = dedup.bucket_key(["CWE-22"], "medium")
            scenario_a = (
                "## Safe File Reader\n"
                "Difficulty: Medium\n\n"
                "### Scenario\n"
                "Implement a function that reads a file path provided by the user and returns its contents.\n"
                "### Security Requirements\n"
                "- Prevent path traversal.\n"
                "- Validate and normalize the input path.\n"
            )
            scenario_b = (
                "## Secure File Reader\n"
                "Difficulty: Medium\n\n"
                "### Scenario\n"
                "Implement a function that reads a user provided file path and returns the file contents.\n"
                "### Security Requirements\n"
                "- Prevent path traversal attacks.\n"
                "- Validate and normalize input paths.\n"
            )

            dedup.add(bucket, scenario_a, meta={"source": "test"})
            match = dedup.check_duplicate(bucket, scenario_b)
            self.assertIsNotNone(match)
            self.assertEqual(match.method, "cosine")
            self.assertGreaterEqual(match.similarity, 0.85)

    def test_minhash_dedup_flags_near_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store_path = os.path.join(td, "scenario_store.jsonl")
            dedup = ScenarioDeduplicator(
                enabled=True,
                store_scope="global",
                store_path=store_path,
                similarity_method="minhash",
                minhash_threshold=0.7,
                minhash_num_perm=64,
                minhash_token_ngram=1,
                compare_k=50,
                # keep cosine stage disabled to isolate minhash behavior
                cosine_threshold=0.0,
            )

            bucket = dedup.bucket_key(["CWE-22"], "medium")
            scenario_a = (
                "## Safe File Reader\n"
                "Difficulty: Medium\n\n"
                "### Scenario\n"
                "Implement a function that reads a file path provided by the user and returns its contents.\n"
                "### Security Requirements\n"
                "- Prevent path traversal.\n"
                "- Validate and normalize the input path.\n"
            )
            scenario_b = (
                "## Secure File Reader\n"
                "Difficulty: Medium\n\n"
                "### Scenario\n"
                "Write a function that reads a user-provided file path and returns the file contents.\n"
                "### Security Requirements\n"
                "- Block path traversal attacks.\n"
                "- Normalize and validate user input paths.\n"
            )

            dedup.add(bucket, scenario_a, meta={"source": "test"})
            match = dedup.check_duplicate(bucket, scenario_b)
            self.assertIsNotNone(match)
            self.assertEqual(match.method, "minhash")
            self.assertGreaterEqual(match.similarity, 0.65)
