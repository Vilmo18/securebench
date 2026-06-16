import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)


from attack_surface_conditions import (  # noqa: E402
    attack_surface_reward_weight,
    attack_surface_prompt_guidance,
    next_attack_surface_label,
    normalize_attack_surface,
    ordered_attack_surfaces,
    seed_attack_surfaces,
)


class TestAttackSurfaceConditions(unittest.TestCase):
    def test_attack_surface_order_is_stable(self) -> None:
        labels = ordered_attack_surfaces()
        self.assertEqual(
            labels,
            [
                "User Inputs & Data",
                "Web Outputs & Rendering",
                "Storage & Filesystem",
                "Authentication & Access Control",
                "Data Exchange & External Services",
                "Execution Environment & Infrastructure",
            ],
        )
        self.assertEqual(seed_attack_surfaces(), ["User Inputs & Data"])
        self.assertEqual(
            seed_attack_surfaces(
                [
                    "Data Exchange & External Services",
                    "Execution Environment & Infrastructure",
                    "User Inputs & Data",
                ]
            ),
            ["Data Exchange & External Services"],
        )

    def test_attack_surface_aliases_work(self) -> None:
        self.assertEqual(normalize_attack_surface("Entrées & Données Utilisateur"), "User Inputs & Data")
        self.assertEqual(normalize_attack_surface("web output & rendering"), "Web Outputs & Rendering")
        self.assertEqual(normalize_attack_surface("Authentication & Access Control"), "Authentication & Access Control")

    def test_attack_surface_guidance_mentions_surface(self) -> None:
        self.assertIn("browser", attack_surface_prompt_guidance("Web Outputs & Rendering").lower())

    def test_attack_surface_progression_and_weight_are_monotonic(self) -> None:
        self.assertEqual(
            next_attack_surface_label("User Inputs & Data"),
            "Web Outputs & Rendering",
        )
        self.assertGreater(
            attack_surface_reward_weight("Execution Environment & Infrastructure"),
            attack_surface_reward_weight("User Inputs & Data"),
        )


if __name__ == "__main__":
    unittest.main()
