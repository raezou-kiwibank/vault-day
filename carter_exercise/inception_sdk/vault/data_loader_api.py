from __future__ import annotations

# standard libs
from typing import Union

# inception sdk
import inception_sdk.vault.core_api as core_api
from inception_sdk.vault.pydantic_types import VaultBaseModel


class DataLoaderResource(VaultBaseModel):
    id: str
    dependencies: list[str]


class ResourceBatch(VaultBaseModel):
    id: str
    resources: list[Union[AccountPlanAssocResource, PlanResource]]
    tranche_id: str | None = None
    metadata: dict[str, str] | None = None


class ResourceBatchRequest(VaultBaseModel):
    request_id: str
    resource_batch: ResourceBatch


class AccountPlanAssocResource(DataLoaderResource):
    account_plan_assoc_resource: core_api.AccountPlanAssoc


class PlanResource(DataLoaderResource):
    plan_resource: core_api.Plan
