import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)


from scenario_conditions import (  # noqa: E402
    axis_order,
    condition_axis_label,
    condition_order_index,
    condition_prompt_guidance,
    next_condition_label,
    normalize_condition,
    ordered_condition_labels,
    seed_condition_labels,
)


class TestScenarioConditions(unittest.TestCase):
    def test_difficulty_order_is_restored(self) -> None:
        labels = ordered_condition_labels()
        self.assertEqual(
            labels,
            [
                "very easy",
                "easy",
                "medium",
                "hard",
                "very hard",
            ],
        )
        self.assertEqual(seed_condition_labels(), ["very easy"])
        self.assertEqual(axis_order(), ["Very Easy/Easy", "Medium", "Hard/Very Hard"])

    def test_aliases_normalize_to_difficulties(self) -> None:
        self.assertEqual(normalize_condition("Very Easy"), "very easy")
        self.assertEqual(normalize_condition("veryhard"), "very hard")
        self.assertEqual(normalize_condition("Easy"), "easy")

    def test_difficulty_order_and_progression_are_consistent(self) -> None:
        self.assertEqual(condition_axis_label("easy"), "Very Easy/Easy")
        self.assertLess(
            condition_order_index("very easy"),
            condition_order_index("very hard"),
        )
        self.assertEqual(
            next_condition_label("very easy"),
            "easy",
        )

    def test_prompt_guidance_mentions_the_requested_surface(self) -> None:
        self.assertIn("local", condition_prompt_guidance("very easy").lower())
        self.assertIn("state", condition_prompt_guidance("hard").lower())


if __name__ == "__main__":
    unittest.main()
