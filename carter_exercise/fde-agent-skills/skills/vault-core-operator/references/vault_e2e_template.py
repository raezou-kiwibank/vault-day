import uuid
import json
import requests

# Disable SSL warnings for self-signed development certificates
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

class VaultE2EClient:
    """
    A canonical, reusable E2E API client for Vault Core.
    Handles dynamic JWT fetching, customer creation, contract uploading,
    v2 account openings, postings ingestion, and balances/live queries.
    """
    def __init__(self, base_url="https://core-api.core-development.tmachine.io", jwt_service_url="https://jwt-service.core-development.tmachine.io/token"):
        self.base_url = base_url
        self.jwt_service_url = jwt_service_url
        self.headers = {
            "Content-Type": "application/json"
        }

    def authenticate(self):
        """Fetch a fresh JWT token dynamically from the local JWT generator service."""
        print(f"-> Fetching JWT from {self.jwt_service_url}...")
        payload = {
            "kid": "default",
            "claims": {
                "scp": ["core:read", "core:write", "core:execute"]
            }
        }
        try:
            res = requests.post(self.jwt_service_url, json=payload, verify=False)
            res.raise_for_status()
            token = res.json()["token"]
            self.headers["Authorization"] = f"Bearer {token}"
            print("   ✅ Successfully authenticated.")
            return True
        except Exception as e:
            print(f"   ❌ Authentication failed: {e}")
            return False

    def make_request(self, method, endpoint, payload=None):
        """Standard HTTP request dispatch helper."""
        url = f"{self.base_url}{endpoint}"
        print(f"-> {method} {endpoint}")
        try:
            res = requests.request(method, url, headers=self.headers, json=payload, verify=False)
            print(f"   Response Status Code: {res.status_code}")
            return res
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Connection failed: {e}")
            return None

    def create_customer(self, first_name, last_name, title="Mr"):
        """Create a stakeholder customer."""
        payload = {
            "request_id": str(uuid.uuid4()),
            "customer": {
                "customer_details": {
                    "title": title,
                    "first_name": first_name,
                    "last_name": last_name
                }
            }
        }
        res = self.make_request("POST", "/v1/customers", payload)
        if res is not None and res.status_code in [200, 201]:
            return res.json()["id"]
        raise RuntimeError(f"Failed to create customer: {res.text if res else 'No Response'}")

    def create_product_version(self, product_id, display_name, code, denominations=["USD"], template_params=None, strategy="PRODUCT_VERSION_MIGRATION_STRATEGY_NEW_PRODUCT"):
        """
        Upload and compile a CLv4 Smart Contract.
        If the contract defines template parameters, they must be supplied in template_params dict
        (e.g., {"monthly_account_fee_application_hour": "0"}).
        """
        payload = {
            "request_id": str(uuid.uuid4()),
            "product_version": {
                "product_id": product_id,
                "display_name": display_name,
                "code": code,
                "supported_denominations": denominations
            },
            "migration_strategy": strategy,
            "is_internal": False
        }
        if template_params:
            payload["product_version"]["params"] = [
                {"name": k, "value": v} for k, v in template_params.items()
            ]
        res = self.make_request("POST", "/v1/product-versions", payload)
        if res is not None and res.status_code in [200, 201]:
            return res.json()["id"]
        raise RuntimeError(f"Failed to create product version: {res.text if res else 'No Response'}")

    def create_account(self, smart_contract_version_id, stakeholder_ids, parameter_overrides=None):
        """Open a v2 customer account (instance parameter overrides passed as string values)."""
        payload = {
            "request_id": str(uuid.uuid4()),
            "account": {
                "type": "ACCOUNT_TYPE_CUSTOMER",
                "smart_contract_version_id": str(smart_contract_version_id),  # Forced string coercion
                "status": "ACCOUNT_STATUS_OPEN",
                "stakeholder_ids": stakeholder_ids
            }
        }
        if parameter_overrides:
            payload["create_options"] = {
                "parameter_values": {
                    k: {"decimal_value": str(v)} for k, v in parameter_overrides.items()  # Forced string decimal coercion
                }
            }
        res = self.make_request("POST", "/v2/accounts", payload)
        if res is not None and res.status_code in [200, 201]:
            return res.json()["id"]
        raise RuntimeError(f"Failed to create account: {res.text if res else 'No Response'}")

    def post_posting_batch(self, posting_instructions, client_id="test-client"):
        """Submit an atomic Posting Instruction Batch to the ledger."""
        payload = {
            "request_id": str(uuid.uuid4()),
            "posting_instruction_batch": {
                "client_id": client_id,
                "client_batch_id": str(uuid.uuid4()),
                "posting_instructions": posting_instructions
            }
        }
        # Force string coercion for amount fields under each posting instruction
        for pi in posting_instructions:
            for inst_type, inst_data in pi.items():
                if isinstance(inst_data, dict) and "amount" in inst_data:
                    inst_data["amount"] = str(inst_data["amount"])
                # Handle nested transfer accounts
                if inst_type == "transfer" and "transfer" in pi:
                    pi["transfer"]["amount"] = str(pi["transfer"]["amount"])

        res = self.make_request("POST", "/v1/posting-instruction-batches", payload)
        if res is not None and res.status_code in [200, 201]:
            return res.json().get("posting_instruction_batch", {})
        raise RuntimeError(f"Failed to submit postings batch: {res.text if res else 'No Response'}")

    def get_balances(self, account_id, page_size=10):
        """Fetch current ledger balances using the correct v2 live balances endpoint and mandatory page_size."""
        res = self.make_request("GET", f"/v2/balances/live?account_id={account_id}&page_size={page_size}")
        if res is not None and res.status_code == 200:
            return res.json().get("balances", [])
        raise RuntimeError(f"Failed to fetch balances: {res.text if res else 'No Response'}")

    def declare_expected_parameter(self, param_id):
        """Declare a Parameter definition in Vault (safely handles 409 Conflict)."""
        payload = {
            "request_id": str(uuid.uuid4()),
            "parameter": {
                "id": param_id,
                "constraint": {
                    "decimal_constraint": {
                        "min_value": "0.00",
                        "max_value": ""
                    }
                }
            }
        }
        res = self.make_request("POST", "/v1/parameters", payload)
        if res is not None and res.status_code == 409:
            print(f"   ℹ️ Parameter '{param_id}' already exists in Vault.")
            return True
        elif res is not None and res.status_code in [200, 201]:
            return True
        raise RuntimeError(f"Failed to declare parameter: {res.text if res else 'No Response'}")
