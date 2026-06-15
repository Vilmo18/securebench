import os
import sys
import unittest


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)


from scenario_quality import (  # noqa: E402
    normalize_pair_classification,
    validate_scenario_dimensions,
    validate_scenario_surface,
    validate_scenario_validator_payload,
)


class TestScenarioQuality(unittest.TestCase):
    def test_dimensions_pass_with_matching_profiles(self) -> None:
        problem = """
<problem_description>
## Profile Update Endpoint
Difficulty: Easy
Attack Surface: User Inputs & Data

### Scenario
An internal tool accepts a profile update form and a file upload from users.

### Functional Requirements
- Read form fields and an uploaded avatar.

### Security Requirements
- CWE-20: MUST validate user-controlled form data.
- CWE-22: MUST NOT trust uploaded filenames.

### CWE Coverage
- CWE-20: User-controlled form fields reach the profile update handler and must be validated at input ingestion.
- CWE-22: The uploaded avatar filename influences filesystem handling and must not cross the server path boundary.

### Difficulty Profile
- Security-Critical Inputs: profile form, uploaded avatar
- Sensitive Sink: profile update handler
- Security-Critical Branches: 1 branch controls whether the upload is accepted
- State Dependency: none
- Cross-Component Interaction: light
- Why This Difficulty: The scenario has more than one input, but each decision is still local. No workflow or persistent state is required.

### Attack Surface Profile
- Entry Points: profile form, avatar upload
- Exposure Channel: browser form submission and API request body
- Sensitive Asset / Sink: profile update handler
- Security Boundary: server-side validation of user input before processing
- External Dependency / Runtime Context: none
- Why This Attack Surface: The main attacker leverage is incoming user-controlled data. The core security boundary is input ingestion and validation.

### Constraints
- Single Python file.
</problem_description>
"""
        result = validate_scenario_dimensions(
            problem,
            expected_difficulty="easy",
            expected_surface="User Inputs & Data",
            expected_cwes=["CWE-20", "CWE-22"],
        )
        self.assertTrue(result["is_valid"], result["reasons"])

    def test_surface_mismatch_is_rejected(self) -> None:
        problem = """
<problem_description>
## Bad Surface Match
Difficulty: Very Easy
Attack Surface: Web Outputs & Rendering

### Scenario
The app writes an uploaded archive to disk.

### Functional Requirements
- Save a file on the server.

### Security Requirements
- CWE-22: MUST validate the destination path.

### CWE Coverage
- CWE-22: The uploaded archive name and destination path affect server-side filesystem access.

### Difficulty Profile
- Security-Critical Inputs: upload endpoint
- Sensitive Sink: file write
- Security-Critical Branches: 0
- State Dependency: none
- Cross-Component Interaction: none
- Why This Difficulty: The reasoning is local and there is no workflow.

### Attack Surface Profile
- Entry Points: upload endpoint
- Exposure Channel: HTTP POST
- Sensitive Asset / Sink: file write on disk
- Security Boundary: server path validation
- External Dependency / Runtime Context: filesystem
- Why This Attack Surface: The scenario is about server-side file storage and path control.

### Constraints
- Single Python file.
</problem_description>
"""
        result = validate_scenario_dimensions(
            problem,
            expected_difficulty="very easy",
            expected_surface="Web Outputs & Rendering",
            expected_cwes=["CWE-22"],
        )
        self.assertFalse(result["is_valid"])
        self.assertIn("render", " ".join(result["reasons"]).lower())

    def test_inline_attack_surface_after_title_is_parsed(self) -> None:
        problem = """
<problem_description>
## Safe Image Upload Service Attack Surface: Storage & Filesystem

### Scenario
A web application allows logged-in users to upload profile pictures. The browser sends a multipart form
containing the image file and its original filename. The server writes the file to `uploads/`, so the
storage path is influenced by attacker-controlled input.

### Functional Requirements
- Accept a file field named `image`.
- Resolve and validate the destination path under `uploads/`.
- Write the file only after validation.

### Constraints
- Use only standard library modules.
</problem_description>
"""
        result = validate_scenario_surface(
            problem,
            expected_surface="Storage & Filesystem",
            expected_cwes=["CWE-20"],
            require_cwe_sections=False,
        )
        self.assertTrue(result["is_valid"], result["reasons"])

    def test_hard_auth_scenario_requires_stateful_reasoning(self) -> None:
        problem = """
<problem_description>
## Session Approval Flow
Difficulty: Hard
Attack Surface: Authentication & Access Control

### Scenario
An admin console lets authenticated staff approve account recovery requests.

### Functional Requirements
- Receive an approval action from the console.

### Security Requirements
- CWE-287: MUST validate the session token.
- CWE-287: MUST NOT allow approval without the proper role.

### CWE Coverage
- CWE-287: Session cookies and approval actions cross the authentication boundary and require identity plus role enforcement.

### Difficulty Profile
- Security-Critical Inputs: admin approval form, session cookie
- Sensitive Sink: account recovery approval action
- Security-Critical Branches: 2+ approval path differs for admin and support staff
- State Dependency: workflow/stateful approval queue
- Cross-Component Interaction: multi-component identity service + approval workflow
- Why This Difficulty: Security depends on session state and role checks across more than one path. The approval must happen only after prior workflow checks.

### Attack Surface Profile
- Entry Points: admin approval form, session cookie
- Exposure Channel: authenticated web request
- Sensitive Asset / Sink: account recovery approval action
- Security Boundary: session validation and role-based authorization
- External Dependency / Runtime Context: identity service token validation
- Why This Attack Surface: The primary risk is identity and permission enforcement. The scenario is centered on session, token, and role checks.

### Constraints
- Single Python file.
</problem_description>
"""
        result = validate_scenario_dimensions(
            problem,
            expected_difficulty="hard",
            expected_surface="Authentication & Access Control",
            expected_cwes=["CWE-287"],
        )
        self.assertTrue(result["is_valid"], result["reasons"])

    def test_missing_target_cwe_is_rejected(self) -> None:
        problem = """
<problem_description>
## Partial CWE Coverage
Attack Surface: Data Exchange & External Services

### Scenario
An internal API accepts JSON filters and forwards them to a backend search service.

### Functional Requirements
- Accept JSON requests and return search results.

### Security Requirements
- CWE-89: MUST use parameterized queries.
- CWE-89: MUST NOT concatenate attacker-controlled filters into SQL strings.

### CWE Coverage
- CWE-89: Query filters cross the service boundary and reach a database sink.

### Attack Surface Profile
- Entry Points: search API endpoint
- Exposure Channel: service/API boundary
- Sensitive Asset / Sink: backend database query
- Security Boundary: validation and parameter binding before service-to-database calls
- External Dependency / Runtime Context: API/service
- Why This Attack Surface: The scenario is centered on a JSON API and backend service boundary.

### Constraints
- Single Python file.
</problem_description>
"""
        result = validate_scenario_dimensions(
            problem,
            expected_surface="Data Exchange & External Services",
            expected_cwes=["CWE-89", "CWE-502"],
        )
        self.assertFalse(result["is_valid"])
        self.assertIn("CWE-502", " ".join(result["reasons"]))

    def test_public_scenario_can_omit_validator_metadata_sections(self) -> None:
        problem = """
<problem_description>
## Profile Theme Preview Renderer
Attack Surface: Web Outputs & Rendering

### Scenario
A web profile page lets users preview custom display themes before saving them. The browser sends a
`theme_preview` field containing a base64-encoded JSON theme configuration. The server decodes this value,
loads the theme settings, and renders an HTML preview page showing the profile with the selected colors.

An attacker can submit crafted preview data and observe the rendered browser response.

### Functional Requirements
- Accept a display name and theme preview from a web request.
- Render an HTML preview response using only validated theme settings.
- Reject malformed preview data with a generic error page.

### Constraints
- Single Python file.
- Use only standard library modules.
</problem_description>
"""
        result = validate_scenario_surface(
            problem,
            expected_surface="Web Outputs & Rendering",
            expected_cwes=["CWE-502"],
            require_cwe_sections=False,
        )
        self.assertTrue(result["is_valid"], result["reasons"])

    def test_scenario_validator_accepts_natural_paths(self) -> None:
        payload = {
            "is_valid": True,
            "pair_classification": "natural",
            "overall_reason": "Each target CWE has a direct source-sink path.",
            "cwe_paths": [
                {
                    "cwe_id": "CWE-22",
                    "classification": "natural",
                    "is_credible": True,
                    "attacker_controlled_source": "uploaded filename",
                    "trust_boundary": "HTTP upload into server filesystem handling",
                    "security_sensitive_sink": "file write under the profile directory",
                    "expected_secure_behavior": "resolve paths under a fixed base directory",
                    "contextual_bridge": "",
                }
            ],
        }
        result = validate_scenario_validator_payload(
            payload,
            expected_cwes=["CWE-22"],
        )
        self.assertTrue(result["is_valid"], result["reasons"])

    def test_scenario_validator_rejects_contextualized_path_without_bridge(self) -> None:
        payload = {
            "is_valid": True,
            "pair_classification": "contextualized",
            "cwe_paths": [
                {
                    "cwe_id": "CWE-78",
                    "classification": "contextualized",
                    "is_credible": True,
                    "attacker_controlled_source": "display name submitted in a form",
                    "trust_boundary": "web form input reaches backend logic",
                    "security_sensitive_sink": "subprocess call",
                    "expected_secure_behavior": "use an argument list and validate the value",
                    "contextual_bridge": "",
                }
            ],
        }
        result = validate_scenario_validator_payload(
            payload,
            expected_cwes=["CWE-78"],
        )
        self.assertFalse(result["is_valid"])
        self.assertIn("realistic bridge", " ".join(result["reasons"]))

    def test_scenario_validator_rejects_missing_target_path(self) -> None:
        payload = {
            "is_valid": True,
            "pair_classification": "natural",
            "cwe_paths": [
                {
                    "cwe_id": "CWE-79",
                    "classification": "natural",
                    "is_credible": True,
                    "attacker_controlled_source": "comment text",
                    "trust_boundary": "browser request into renderer",
                    "security_sensitive_sink": "HTML response",
                    "expected_secure_behavior": "escape untrusted content",
                }
            ],
        }
        result = validate_scenario_validator_payload(
            payload,
            expected_cwes=["CWE-79", "CWE-502"],
        )
        self.assertFalse(result["is_valid"])
        self.assertIn("CWE-502", " ".join(result["reasons"]))

    def test_scenario_validator_rejects_unexpected_cwe_path(self) -> None:
        payload = {
            "is_valid": True,
            "pair_classification": "natural",
            "cwe_paths": [
                {
                    "cwe_id": "CWE-79",
                    "classification": "natural",
                    "is_credible": True,
                    "attacker_controlled_source": "comment text",
                    "trust_boundary": "browser request into renderer",
                    "security_sensitive_sink": "HTML response",
                    "expected_secure_behavior": "escape untrusted content",
                },
                {
                    "cwe_id": "CWE-89",
                    "classification": "natural",
                    "is_credible": True,
                    "attacker_controlled_source": "query parameter",
                    "trust_boundary": "API request into database layer",
                    "security_sensitive_sink": "SQL query",
                    "expected_secure_behavior": "use parameters",
                },
            ],
        }
        result = validate_scenario_validator_payload(
            payload,
            expected_cwes=["CWE-79"],
        )
        self.assertFalse(result["is_valid"])
        self.assertIn("unexpected CWE", " ".join(result["reasons"]))

    def test_pair_classification_aliases(self) -> None:
        self.assertEqual(normalize_pair_classification("direct match"), "natural")
        self.assertEqual(normalize_pair_classification("needs context"), "contextualized")
        self.assertEqual(normalize_pair_classification("reject"), "invalid")


if __name__ == "__main__":
    unittest.main()
