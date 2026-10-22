# standard libs
from datetime import datetime

# inception sdk
import inception_sdk.vault.core_api as core_api
import inception_sdk.vault.data_loader_api as data_loader_api
from inception_sdk.vault.test.common import UTC, TestPydanticModels


class TestAccountPlanAssocResource(
    TestPydanticModels.Base[data_loader_api.AccountPlanAssocResource]
):

    dictionary = dict(
        id="id",
        dependencies=["dependency_1"],
        account_plan_assoc_resource=dict(
            id="assoc_id",
            account_id="account_id",
            plan_id="plan_id",
            status="ACCOUNT_PLAN_ASSOC_STATUS_ACTIVE",
            create_timestamp="2020-01-01T00:00:00+00:00",
            start_timestamp="2020-01-02T00:00:00+00:00",
            end_timestamp="2020-01-03T00:00:00+00:00",
        ),
    )

    resource = data_loader_api.AccountPlanAssocResource(
        id="id",
        dependencies=["dependency_1"],
        account_plan_assoc_resource=core_api.AccountPlanAssoc(
            id="assoc_id",
            account_id="account_id",
            plan_id="plan_id",
            status=core_api.AccountPlanAssocStatus.ACCOUNT_PLAN_ASSOC_STATUS_ACTIVE,
            create_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
            start_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
            end_timestamp=datetime(2020, 1, 3, tzinfo=UTC),
        ),
    )


class TestPlanResource(TestPydanticModels.Base[data_loader_api.PlanResource]):

    dictionary = dict(
        id="id",
        dependencies=["dependency_1"],
        plan_resource=dict(
            id="plan_id",
            supervisor_contract_version_id="supervisor_contract_version_id",
            processing_group_id="processing_group_id",
            status="PLAN_STATUS_OPEN",
            create_timestamp="2020-01-01T00:00:00+00:00",
            opening_timestamp="2020-01-02T00:00:00+00:00",
            activation_completed_timestamp="2020-01-03T00:00:00+00:00",
            closing_timestamp="2020-01-04T00:00:00+00:00",
            closure_completed_timestamp="2020-01-05T00:00:00+00:00",
            details={"key": "value"},
        ),
    )

    resource = data_loader_api.PlanResource(
        id="id",
        dependencies=["dependency_1"],
        plan_resource=core_api.Plan(
            id="plan_id",
            supervisor_contract_version_id="supervisor_contract_version_id",
            processing_group_id="processing_group_id",
            status=core_api.PlanStatus.OPEN,
            create_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
            opening_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
            activation_completed_timestamp=datetime(2020, 1, 3, tzinfo=UTC),
            closing_timestamp=datetime(2020, 1, 4, tzinfo=UTC),
            closure_completed_timestamp=datetime(2020, 1, 5, tzinfo=UTC),
            details={"key": "value"},
        ),
    )


class TestResourceBatchRequest(TestPydanticModels.Base[data_loader_api.ResourceBatchRequest]):

    dictionary = dict(
        request_id="request_id",
        resource_batch=dict(
            id="batch_id",
            resources=[
                dict(
                    id="id",
                    dependencies=["abc"],
                    plan_resource=dict(
                        activation_completed_timestamp=None,
                        closing_timestamp=None,
                        closure_completed_timestamp=None,
                        create_timestamp=None,
                        details=None,
                        id="plan_id",
                        opening_timestamp=None,
                        processing_group_id=None,
                        supervisor_contract_version_id="supervisor_id",
                        status=core_api.PlanStatus.OPEN.value,
                    ),
                )
            ],
            tranche_id=None,
            metadata=None,
        ),
    )

    resource = data_loader_api.ResourceBatchRequest(
        request_id="request_id",
        resource_batch=data_loader_api.ResourceBatch(
            id="batch_id",
            resources=[
                data_loader_api.PlanResource(
                    id="id",
                    dependencies=["abc"],
                    plan_resource=core_api.Plan(
                        id="plan_id",
                        supervisor_contract_version_id="supervisor_id",
                        status=core_api.PlanStatus.OPEN,
                    ),
                )
            ],
        ),
    )


class TestResourceBatch(TestPydanticModels.Base[data_loader_api.ResourceBatch]):

    dictionary = dict(
        id="batch_id",
        resources=[
            dict(
                id="id_1",
                dependencies=["supervisor_1"],
                plan_resource=dict(
                    activation_completed_timestamp=None,
                    closing_timestamp=None,
                    closure_completed_timestamp=None,
                    create_timestamp=None,
                    details=None,
                    id="plan_1",
                    opening_timestamp=None,
                    processing_group_id=None,
                    supervisor_contract_version_id="supervisor_1",
                    status=core_api.PlanStatus.OPEN.value,
                ),
            ),
            dict(
                id="id_2",
                dependencies=["id_1"],
                account_plan_assoc_resource=dict(
                    account_id="account_1",
                    create_timestamp=None,
                    end_timestamp=None,
                    id="assoc_1",
                    plan_id="plan_1",
                    start_timestamp=None,
                    status=core_api.AccountPlanAssocStatus.ACCOUNT_PLAN_ASSOC_STATUS_ACTIVE.value,
                ),
            ),
        ],
        tranche_id=None,
        metadata=None,
    )

    resource = data_loader_api.ResourceBatch(
        id="batch_id",
        resources=[
            data_loader_api.PlanResource(
                id="id_1",
                dependencies=["supervisor_1"],
                plan_resource=core_api.Plan(
                    id="plan_1",
                    supervisor_contract_version_id="supervisor_1",
                    status=core_api.PlanStatus.OPEN,
                ),
            ),
            data_loader_api.AccountPlanAssocResource(
                id="id_2",
                dependencies=["id_1"],
                account_plan_assoc_resource=core_api.AccountPlanAssoc(
                    id="assoc_1",
                    account_id="account_1",
                    plan_id="plan_1",
                    status=core_api.AccountPlanAssocStatus.ACCOUNT_PLAN_ASSOC_STATUS_ACTIVE,
                ),
            ),
        ],
    )
