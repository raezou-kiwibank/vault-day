# standard libs
import json
from datetime import datetime
from decimal import Decimal
from unittest import TestCase
from zoneinfo import ZoneInfo

# inception sdk
import inception_sdk.vault.core_api as core_api
from inception_sdk.vault.core_api import (
    AccountIdParameterValue,
    DatetimeParameterValue,
    DecimalParameterValue,
    EnumerationParameterValue,
    StringParameterValue,
    SubAccountStatus,
)
from inception_sdk.vault.pydantic_types import OneOfException
from inception_sdk.vault.test.common import UTC, TestPydanticModels


class TestEmptyStringConstraintParameter(TestPydanticModels.Base[core_api.ParameterResource]):
    dictionary = dict(
        id="id",
        constraint=dict(string_constraint={"min_length": 0, "max_length": 0}),
        metadata=dict(some="metadata"),
    )
    resource = core_api.ParameterResource(
        id="id",
        constraint=core_api.StringConstraint(string_constraint=core_api.StringConstraintValue()),
        metadata=dict(some="metadata"),
    )


class TestStringConstraintParameter(TestPydanticModels.Base[core_api.ParameterResource]):
    dictionary = dict(
        id="id",
        constraint=dict(string_constraint={"min_length": 1, "max_length": 10}),
        metadata=dict(some="metadata"),
    )
    resource = core_api.ParameterResource(
        id="id",
        constraint=core_api.StringConstraint(
            string_constraint=core_api.StringConstraintValue(min_length=1, max_length=10)
        ),
        metadata=dict(some="metadata"),
    )


class TestAccountConstraint(TestPydanticModels.Base[core_api.ParameterResource]):
    dictionary = dict(
        id="id",
        constraint=dict(account_constraint={}),
        metadata=dict(some="metadata"),
    )
    resource = core_api.ParameterResource(
        id="id",
        constraint=core_api.AccountConstraint(account_constraint=core_api.AccountConstraintValue()),
        metadata=dict(some="metadata"),
    )


class TestEmptyDecimalConstraintParameter(TestPydanticModels.Base[core_api.ParameterResource]):
    dictionary = dict(
        id="id",
        constraint=dict(decimal_constraint={"min_value": None, "max_value": None}),
        metadata=dict(some="metadata"),
    )
    resource = core_api.ParameterResource(
        id="id",
        constraint=core_api.DecimalConstraint(decimal_constraint=core_api.DecimalConstraintValue()),
        metadata=dict(some="metadata"),
    )

    def test_omitted_nullable_fields(self):
        # Core API includes None fields
        # pydantic will include None fields by default, which Core API accepts, but also
        # check that omitting the fields still validates OK
        self.assertEqual(
            core_api.ParameterResource.model_validate(
                dict(
                    id="id",
                    constraint=dict(decimal_constraint={}),
                    metadata=dict(some="metadata"),
                )
            ),
            core_api.ParameterResource(
                id="id",
                constraint=core_api.DecimalConstraint(
                    decimal_constraint=core_api.DecimalConstraintValue()
                ),
                metadata=dict(some="metadata"),
            ),
        )


class TestDecimalConstraintParameter(TestPydanticModels.Base[core_api.ParameterResource]):
    dictionary = dict(
        id="id",
        constraint=dict(decimal_constraint=dict(min_value="1.5", max_value="2.3")),
        metadata=dict(some="metadata"),
    )
    resource = core_api.ParameterResource(
        id="id",
        constraint=core_api.DecimalConstraint(
            decimal_constraint=core_api.DecimalConstraintValue(
                min_value=Decimal("1.5"),
                max_value=Decimal("2.3"),
            )
        ),
        metadata=dict(some="metadata"),
    )


class TestEmptyEnumConstraintParameter(TestCase):
    # There's no from/to dict symmetry given the expected exception, so we
    # don't use the standard base
    def test_parse_definition_with_empty_enum_constraint(self):
        with self.assertRaises(ValueError):
            core_api.ParameterResource.model_validate(
                dict(
                    id="id",
                    constraint=dict(enumeration_constraint=dict()),
                    metadata=dict(some="metadata"),
                )
            )


class TestEnumConstraintParameter(TestPydanticModels.Base[core_api.ParameterResource]):
    dictionary = dict(
        id="id",
        constraint=dict(enumeration_constraint=dict(permitted_values=["value_1", "value_2"])),
        metadata=dict(some="metadata"),
    )
    resource = core_api.ParameterResource(
        id="id",
        constraint=core_api.EnumerationConstraint(
            enumeration_constraint=core_api.EnumerationConstraintValue(
                permitted_values=["value_1", "value_2"]
            )
        ),
        metadata=dict(some="metadata"),
    )


class TestEmptyDatetimeConstraintParameter(TestPydanticModels.Base[core_api.ParameterResource]):

    dictionary = dict(
        id="id",
        constraint=dict(
            date_time_constraint=dict(
                precision=core_api.DatetimeConstraintPrecision.MINUTE.value,
                earliest=None,
                latest=None,
            )
        ),
        metadata=dict(some="metadata"),
    )

    resource = core_api.ParameterResource(
        id="id",
        constraint=core_api.DatetimeConstraint(
            date_time_constraint=core_api.DatetimeConstraintValue(
                # precision=core_api.DatetimeConstraintPrecision.MINUTE
            )
        ),
        metadata=dict(some="metadata"),
    )


class TestOmittedFieldsDatetimeConstraintParameter(
    TestPydanticModels.Base[core_api.ParameterResource]
):

    dictionary = dict(
        id="id",
        constraint=dict(
            date_time_constraint=dict(
                precision=core_api.DatetimeConstraintPrecision.MINUTE.value,
                earliest=None,
                latest=None,
            )
        ),
        metadata=dict(some="metadata"),
    )

    resource = core_api.ParameterResource(
        id="id",
        constraint=core_api.DatetimeConstraint(
            date_time_constraint=core_api.DatetimeConstraintValue()
        ),
        metadata=dict(some="metadata"),
    )


class TestPrecisionOnlyDateTimeConstraintParameter(
    TestPydanticModels.Base[core_api.ParameterResource]
):
    dictionary = dict(
        id="id",
        constraint=dict(date_time_constraint=dict(precision="DAY", earliest=None, latest=None)),
        metadata=dict(some="metadata"),
    )
    resource = core_api.ParameterResource(
        id="id",
        constraint=core_api.DatetimeConstraint(
            date_time_constraint=core_api.DatetimeConstraintValue(
                precision=core_api.DatetimeConstraintPrecision.DAY
            )
        ),
        metadata=dict(some="metadata"),
    )


class TestFullDateTimeConstraintParameter(TestPydanticModels.Base[core_api.ParameterResource]):
    dictionary = dict(
        id="id",
        constraint=dict(
            date_time_constraint=dict(
                precision="DAY",
                earliest="2020-01-01T00:00:00+00:00",
                latest="2024-12-31T23:59:59+00:00",
            )
        ),
        metadata=dict(some="metadata"),
    )
    resource = core_api.ParameterResource(
        id="id",
        constraint=core_api.DatetimeConstraint(
            date_time_constraint=core_api.DatetimeConstraintValue(
                precision=core_api.DatetimeConstraintPrecision.DAY,
                earliest=datetime(2020, 1, 1, tzinfo=UTC),
                latest=datetime(2024, 12, 31, 23, 59, 59, tzinfo=UTC),
            )
        ),
        metadata=dict(some="metadata"),
    )


class TestParameterParsingErrors(TestCase):
    def test_parse_definition_with_no_constraint(self):
        with self.assertRaises(ValueError):
            core_api.ParameterResource.model_validate(
                dict(
                    id="id",
                    metadata=dict(some="metadata"),
                )
            )

    def test_parse_definition_with_empty_definition(self):
        with self.assertRaises(ValueError):
            core_api.ParameterResource.model_validate(dict())

    def test_parse_definition_with_no_definition(self):
        with self.assertRaises(ValueError):
            core_api.ParameterResource.model_validate(None)


class TestBatchGetParameterResourceV1ResponseBody(
    TestPydanticModels.Base[core_api.BatchGetParameterResourceV1ResponseBody]
):
    dictionary = dict(
        parameters=dict(
            param_1=dict(
                id="param_1",
                constraint=dict(account_constraint={}),
                metadata=dict(some="metadata"),
            ),
            param_2=dict(
                id="param_2",
                constraint=dict(string_constraint={"min_length": 0, "max_length": 0}),
                metadata=dict(some="metadata"),
            ),
        )
    )
    resource = core_api.BatchGetParameterResourceV1ResponseBody(
        parameters=dict(
            param_1=core_api.ParameterResource(
                id="param_1",
                constraint=core_api.AccountConstraint(
                    account_constraint=core_api.AccountConstraintValue()
                ),
                metadata=dict(some="metadata"),
            ),
            param_2=core_api.ParameterResource(
                id="param_2",
                constraint=core_api.StringConstraint(
                    string_constraint=core_api.StringConstraintValue()
                ),
                metadata=dict(some="metadata"),
            ),
        )
    )


class TestCreateAccountV2Response(TestPydanticModels.Base[core_api.CreateAccountV2Response]):
    dictionary = dict(
        id="01440771331881091463",
        type="ACCOUNT_TYPE_CUSTOMER",
        smart_contract_version_id="value1",
        pending_smart_contract_version_id="value1",
        stakeholder_ids=["value1", "value2"],
        alias="value1",
        status="ACCOUNT_STATUS_PENDING",
        vault_create_timestamp="2020-01-01T00:00:00+00:00",
        source_create_timestamp="2020-01-02T00:00:00+00:00",
        source_open_timestamp="2020-01-03T00:00:00+00:00",
        source_close_timestamp="2020-01-04T00:00:00+00:00",
        update_timestamp="2020-01-05T00:00:00+00:00",
        activation_timestamp="2020-01-06T00:00:00+00:00",
        permitted_denominations=["value1", "value2"],
        details={"KEY": "value1"},
        t_side="T_SIDE_ASSET",
        contract_update_timestamp="2020-01-07T00:00:00+00:00",
        processing_group_id="value1",
        tranche_id="",
        processing_label="",
        parameter_value_hierarchy_node_id="",
        create_options_side_effects=None,
    )
    resource = core_api.CreateAccountV2Response(
        id="01440771331881091463",
        type=core_api.AccountV2Type.ACCOUNT_TYPE_CUSTOMER,
        smart_contract_version_id="value1",
        pending_smart_contract_version_id="value1",
        stakeholder_ids=["value1", "value2"],
        alias="value1",
        status=core_api.AccountV2Status.ACCOUNT_STATUS_PENDING,
        vault_create_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
        source_create_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
        source_open_timestamp=datetime(2020, 1, 3, tzinfo=UTC),
        source_close_timestamp=datetime(2020, 1, 4, tzinfo=UTC),
        update_timestamp=datetime(2020, 1, 5, tzinfo=UTC),
        activation_timestamp=datetime(2020, 1, 6, tzinfo=UTC),
        permitted_denominations=["value1", "value2"],
        details={"KEY": "value1"},
        t_side=core_api.AccountV2TSide.T_SIDE_ASSET,
        contract_update_timestamp=datetime(2020, 1, 7, tzinfo=UTC),
        processing_group_id="value1",
        tranche_id="",
        processing_label="",
        parameter_value_hierarchy_node_id="",
    )


class TestCreateAccountV2ResponseNullableFields(
    TestPydanticModels.Base[core_api.CreateAccountV2Response]
):
    dictionary = dict(
        id="01440771331881091463",
        type="ACCOUNT_TYPE_CUSTOMER",
        smart_contract_version_id="value1",
        pending_smart_contract_version_id="value1",
        stakeholder_ids=["value1", "value2"],
        alias="value1",
        status="ACCOUNT_STATUS_PENDING",
        vault_create_timestamp="2020-01-01T00:00:00+00:00",
        source_create_timestamp="2020-01-02T00:00:00+00:00",
        source_open_timestamp=None,
        source_close_timestamp=None,
        update_timestamp=None,
        activation_timestamp=None,
        permitted_denominations=["value1", "value2"],
        details={"KEY": "value1"},
        t_side="T_SIDE_ASSET",
        contract_update_timestamp=None,
        processing_group_id="value1",
        tranche_id="",
        processing_label="",
        parameter_value_hierarchy_node_id=None,
        create_options_side_effects=None,
    )
    resource = core_api.CreateAccountV2Response(
        id="01440771331881091463",
        type=core_api.AccountV2Type.ACCOUNT_TYPE_CUSTOMER,
        smart_contract_version_id="value1",
        pending_smart_contract_version_id="value1",
        stakeholder_ids=["value1", "value2"],
        alias="value1",
        status=core_api.AccountV2Status.ACCOUNT_STATUS_PENDING,
        vault_create_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
        source_create_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
        source_open_timestamp=None,
        source_close_timestamp=None,
        update_timestamp=None,
        activation_timestamp=None,
        permitted_denominations=["value1", "value2"],
        details={"KEY": "value1"},
        t_side=core_api.AccountV2TSide.T_SIDE_ASSET,
        contract_update_timestamp=None,
        processing_group_id="value1",
        tranche_id="",
        processing_label="",
        parameter_value_hierarchy_node_id=None,
    )


class TestProcessingGroup(TestPydanticModels.Base[core_api.ProcessingGroup]):
    dictionary = dict(
        id="DEFAULT",
        timezone="Europe/London",
        status="PROCESSING_GROUP_STATUS_ACTIVE",
        create_timestamp="2020-01-01T00:00:00+00:00",
        update_timestamp="2020-01-02T00:00:00+00:00",
        minimum_observation_timestamp="2020-01-03T00:00:00+00:00",
    )
    resource = core_api.ProcessingGroup(
        id="DEFAULT",
        timezone=ZoneInfo("Europe/London"),
        status=core_api.ProcessingGroupStatus.ACTIVE,
        create_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
        update_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
        minimum_observation_timestamp=datetime(2020, 1, 3, tzinfo=UTC),
    )


class TestProcessingGroupNullableFields(TestPydanticModels.Base[core_api.ProcessingGroup]):
    dictionary = dict(
        id="DEFAULT",
        timezone="",
        status="PROCESSING_GROUP_STATUS_ACTIVE",
        create_timestamp="2020-01-01T00:00:00+00:00",
        update_timestamp=None,
        minimum_observation_timestamp=None,
    )
    resource = core_api.ProcessingGroup(
        id="DEFAULT",
        timezone=None,
        status=core_api.ProcessingGroupStatus.ACTIVE,
        create_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
    )


class TestProcessingGroupUpdate(TestPydanticModels.Base[core_api.ProcessingGroupUpdate]):
    dictionary = dict(
        timezone="UTC",
        status="PROCESSING_GROUP_STATUS_ACTIVE",
    )
    resource = core_api.ProcessingGroupUpdate(
        timezone=UTC,
        status=core_api.ProcessingGroupStatus.ACTIVE,
    )


class TestProcessingGroupUpdateNullableFields(
    TestPydanticModels.Base[core_api.ProcessingGroupUpdate]
):
    dictionary = dict(
        timezone="",
        status="PROCESSING_GROUP_STATUS_ACTIVE",
    )
    resource = core_api.ProcessingGroupUpdate(
        timezone=None,
        status=core_api.ProcessingGroupStatus.ACTIVE,
    )


class TestUpdateProcessingGroupRequestBody(TestCase):
    # Because of defaulting there's no from/to symmetry, so we resort to
    # writing these tests manually
    resource = core_api.UpdateProcessingGroupRequestBody(
        request_id="request_id",
        update_mask=core_api.UpdateMask(paths=["path_1", "path_2"]),
        processing_group=core_api.ProcessingGroupUpdate(
            timezone=UTC,
            status=core_api.ProcessingGroupStatus.PAUSED,
        ),
        minimum_observation_timestamp_update_options=(
            core_api.MinimumObservationTimestampUpdateOptions(
                schedules_observe_balances_at_unpause_time=True
            )
        ),
    )

    def test_update_processing_group_request_body_to_dict(self):
        self.assertEquals(
            self.resource.model_dump(),
            dict(
                request_id="request_id",
                update_mask={
                    "paths": ["path_1", "path_2"],
                },
                processing_group={"timezone": "UTC", "status": "PROCESSING_GROUP_STATUS_PAUSED"},
                minimum_observation_timestamp_update_options={
                    "schedules_observe_balances_at_unpause_time": True
                },
            ),
        )


class TestCreateProcessingGroup(TestCase):
    # CreateProcessingGroup is for requests only and we want to check that the ZoneInfo
    # gets dumped to JSON as expected, so these tests don't use the standard test class.
    def test_dump_to_json(self):
        self.assertEqual(
            core_api.CreateProcessingGroup(
                id="id",
                timezone=UTC,
                description="description",
            ).model_dump_json(),
            json.dumps(
                dict(
                    id="id",
                    timezone="UTC",
                    description="description",
                ),
                # this removes whitespace
                separators=(",", ":"),
            ),
        )

    def test_dump_to_json_with_defaults(self):
        self.assertEqual(
            core_api.CreateProcessingGroup(
                id="id",
                timezone=UTC,
            ).model_dump_json(),
            json.dumps(
                dict(
                    id="id",
                    timezone="UTC",
                    description=None,
                ),
                # this removes whitespace
                separators=(",", ":"),
            ),
        )


class TestStringRepresentationsOfParameterValues(TestCase):

    def test_string_parameter_value(self):
        self.assertEquals(str(StringParameterValue(string_value="string")), "string")

    def test_decimal_parameter_value(self):
        self.assertEquals(str(DecimalParameterValue(decimal_value=Decimal("1.2"))), "1.2")

    def test_datetime_parameter_value(self):
        self.assertEquals(
            str(
                DatetimeParameterValue(date_time_value=datetime(2024, 1, 26, 12, 30, tzinfo=UTC)),
            ),
            "2024-01-26T12:30:00+00:00",
        )

    def test_enumeration_parameter_value(self):
        self.assertEquals(str(EnumerationParameterValue(enumeration_value="red")), "red")

    def test_account_id_parameter_value(self):
        self.assertEquals(str(AccountIdParameterValue(account_id_value="12345")), "12345")


class TestCreateAccountFlag(TestPydanticModels.Base[core_api.CreateFlagV1CreateAccountFlag]):
    dictionary = dict(
        flag_definition_id="flag_definition_id",
        description="description",
        value="FLAG_VALUE_ON",
        effective_timestamp="2020-01-01T00:00:00+00:00",
        expiry_timestamp="2020-01-02T00:00:00+00:00",
        account_id="account_id",
        is_backdated=True,
    )
    resource = core_api.CreateFlagV1CreateAccountFlag(
        flag_definition_id="flag_definition_id",
        description="description",
        value=core_api.FlagV1FlagValue.FLAG_VALUE_ON,
        effective_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
        expiry_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
        account_id="account_id",
        is_backdated=True,
    )


class TestCreateCustomerFlag(TestPydanticModels.Base[core_api.CreateFlagV1CreateCustomerFlag]):
    dictionary = dict(
        flag_definition_id="flag_definition_id",
        description="description",
        value="FLAG_VALUE_ON",
        effective_timestamp="2020-01-01T00:00:00+00:00",
        expiry_timestamp="2020-01-02T00:00:00+00:00",
        customer_id="customer_id",
        is_backdated=True,
    )
    resource = core_api.CreateFlagV1CreateCustomerFlag(
        flag_definition_id="flag_definition_id",
        description="description",
        value=core_api.FlagV1FlagValue.FLAG_VALUE_ON,
        effective_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
        expiry_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
        customer_id="customer_id",
        is_backdated=True,
    )


class TestCreatePaymentDeviceFlag(
    TestPydanticModels.Base[core_api.CreateFlagV1CreatePaymentDeviceId]
):
    dictionary = dict(
        flag_definition_id="flag_definition_id",
        description="description",
        value="FLAG_VALUE_ON",
        effective_timestamp="2020-01-01T00:00:00+00:00",
        expiry_timestamp="2020-01-02T00:00:00+00:00",
        payment_device_id="payment_device_id",
        is_backdated=True,
    )
    resource = core_api.CreateFlagV1CreatePaymentDeviceId(
        flag_definition_id="flag_definition_id",
        description="description",
        value=core_api.FlagV1FlagValue.FLAG_VALUE_ON,
        effective_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
        expiry_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
        payment_device_id="payment_device_id",
        is_backdated=True,
    )


class TestGenericFlagNullableFields(TestPydanticModels.Base[core_api.CreateFlagV1Flag]):
    dictionary = dict(
        flag_definition_id="flag_definition_id",
        description="description",
        value="FLAG_VALUE_ON",
        effective_timestamp=None,
        expiry_timestamp=None,
        is_backdated=None,
    )
    resource = core_api.CreateFlagV1Flag(
        flag_definition_id="flag_definition_id",
        description="description",
        value=core_api.FlagV1FlagValue.FLAG_VALUE_ON,
        effective_timestamp=None,
        expiry_timestamp=None,
        is_backdated=None,
    )


class TestCreateFlagRequestBody(TestPydanticModels.Base[core_api.CreateFlagV1RequestBody]):
    dictionary = dict(
        request_id="request_id",
        flag=dict(
            flag_definition_id="flag_definition_id",
            description="description",
            value="FLAG_VALUE_ON",
            effective_timestamp="2020-01-01T00:00:00+00:00",
            expiry_timestamp="2020-01-02T00:00:00+00:00",
            is_backdated=True,
            account_id="account_id",
        ),
    )
    resource = core_api.CreateFlagV1RequestBody(
        request_id="request_id",
        flag=core_api.CreateFlagV1CreateAccountFlag(
            flag_definition_id="flag_definition_id",
            description="description",
            value=core_api.FlagV1FlagValue.FLAG_VALUE_ON,
            effective_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
            expiry_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
            is_backdated=True,
            account_id="account_id",
        ),
    )


class TestAccountFlag(TestPydanticModels.Base[core_api.FlagV1AccountFlag]):
    dictionary = dict(
        flag_definition_id="flag_definition_id",
        id="id",
        description="description",
        value="FLAG_VALUE_ON",
        effective_timestamp="2020-01-01T00:00:00+00:00",
        expiry_timestamp="2020-01-02T00:00:00+00:00",
        account_id="account_id",
        is_backdated=True,
    )
    resource = core_api.FlagV1AccountFlag(
        flag_definition_id="flag_definition_id",
        id="id",
        description="description",
        value=core_api.FlagV1FlagValue.FLAG_VALUE_ON,
        effective_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
        expiry_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
        account_id="account_id",
        is_backdated=True,
    )


class TestCustomerFlag(TestPydanticModels.Base[core_api.FlagV1CustomerFlag]):
    dictionary = dict(
        flag_definition_id="flag_definition_id",
        id="id",
        description="description",
        value="FLAG_VALUE_ON",
        effective_timestamp="2020-01-01T00:00:00+00:00",
        expiry_timestamp="2020-01-02T00:00:00+00:00",
        customer_id="customer_id",
        is_backdated=True,
    )
    resource = core_api.FlagV1CustomerFlag(
        flag_definition_id="flag_definition_id",
        id="id",
        description="description",
        value=core_api.FlagV1FlagValue.FLAG_VALUE_ON,
        effective_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
        expiry_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
        customer_id="customer_id",
        is_backdated=True,
    )


class TestPaymentDeviceFlag(TestPydanticModels.Base[core_api.FlagV1PaymentDeviceFlag]):
    dictionary = dict(
        flag_definition_id="flag_definition_id",
        id="id",
        description="description",
        value="FLAG_VALUE_ON",
        effective_timestamp="2020-01-01T00:00:00+00:00",
        expiry_timestamp="2020-01-02T00:00:00+00:00",
        payment_device_id="payment_device_id",
        is_backdated=True,
    )
    resource = core_api.FlagV1PaymentDeviceFlag(
        flag_definition_id="flag_definition_id",
        id="id",
        description="description",
        value=core_api.FlagV1FlagValue.FLAG_VALUE_ON,
        effective_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
        expiry_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
        payment_device_id="payment_device_id",
        is_backdated=True,
    )


class TestAccountPlanAssoc(TestPydanticModels.Base[core_api.AccountPlanAssoc]):

    dictionary = dict(
        id="id",
        account_id="account_id",
        plan_id="plan_id",
        status="ACCOUNT_PLAN_ASSOC_STATUS_ACTIVE",
        create_timestamp="2020-01-01T00:00:00+00:00",
        start_timestamp="2020-01-02T00:00:00+00:00",
        end_timestamp="2020-01-03T00:00:00+00:00",
    )

    resource = core_api.AccountPlanAssoc(
        id="id",
        account_id="account_id",
        plan_id="plan_id",
        status=core_api.AccountPlanAssocStatus.ACCOUNT_PLAN_ASSOC_STATUS_ACTIVE,
        create_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
        start_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
        end_timestamp=datetime(2020, 1, 3, tzinfo=UTC),
    )


class TestAccountPlanAssocNullableFields(TestPydanticModels.Base[core_api.AccountPlanAssoc]):

    dictionary = dict(
        id="id",
        account_id="account_id",
        plan_id="plan_id",
        status="ACCOUNT_PLAN_ASSOC_STATUS_ACTIVE",
        create_timestamp=None,
        start_timestamp=None,
        end_timestamp=None,
    )

    resource = core_api.AccountPlanAssoc(
        id="id",
        account_id="account_id",
        plan_id="plan_id",
        status=core_api.AccountPlanAssocStatus.ACCOUNT_PLAN_ASSOC_STATUS_ACTIVE,
        create_timestamp=None,
        start_timestamp=None,
        end_timestamp=None,
    )


class TestCustomerAccountsV2(TestPydanticModels.Base[core_api.CustomerAccountRequestBody]):

    dictionary = dict(
        status="ACCOUNT_STATUS_OPEN",
        smart_contract_version_id="1",
        stakeholder_ids=["stakeholder_1", "stakeholder_2"],
        type="ACCOUNT_TYPE_CUSTOMER",
        id="id",
        parameter_value_hierarchy_node_id=None,
        alias="alias",
        details={"key": "value"},
        processing_group_id="processing_group",
        permitted_denominations=["USD"],
        activation_timestamp="2020-01-06T00:00:00+00:00",
    )

    resource = core_api.CustomerAccountRequestBody(
        smart_contract_version_id="1",
        status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
        stakeholder_ids=["stakeholder_1", "stakeholder_2"],
        id="id",
        alias="alias",
        details={"key": "value"},
        processing_group_id="processing_group",
        permitted_denominations=["USD"],
        activation_timestamp=datetime(2020, 1, 6, tzinfo=UTC),
    )


class TestCustomerAccountsOmittedFieldsV2(
    TestPydanticModels.Base[core_api.CustomerAccountRequestBody]
):

    dictionary = dict(
        status="ACCOUNT_STATUS_OPEN",
        smart_contract_version_id="1",
        stakeholder_ids=["stakeholder_1", "stakeholder_2"],
        type="ACCOUNT_TYPE_CUSTOMER",
        id=None,
        parameter_value_hierarchy_node_id=None,
        alias=None,
        details=None,
        processing_group_id=None,
        permitted_denominations=None,
        activation_timestamp=None,
    )

    resource = core_api.CustomerAccountRequestBody(
        smart_contract_version_id="1",
        status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
        stakeholder_ids=["stakeholder_1", "stakeholder_2"],
    )


class TestInternalAccounts(TestPydanticModels.Base[core_api.InternalAccountRequestBody]):

    dictionary = dict(
        t_side="T_SIDE_LIABILITY",
        type="ACCOUNT_TYPE_INTERNAL",
        status="ACCOUNT_STATUS_OPEN",
        id="id",
        alias="alias",
        details={"key": "value"},
        processing_group_id="processing_group",
        processing_label="processing_label",
    )

    resource = core_api.InternalAccountRequestBody(
        status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
        id="id",
        alias="alias",
        details={"key": "value"},
        processing_group_id="processing_group",
        processing_label="processing_label",
    )


class TestInternalAccountsOmittedFieldsV2(
    TestPydanticModels.Base[core_api.InternalAccountRequestBody]
):

    dictionary = dict(
        t_side="T_SIDE_LIABILITY",
        status="ACCOUNT_STATUS_OPEN",
        type="ACCOUNT_TYPE_INTERNAL",
        id=None,
        alias=None,
        details=None,
        processing_group_id=None,
        processing_label=None,
    )

    resource = core_api.InternalAccountRequestBody(
        status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
    )


class CreateAccountV2RequestBody(TestPydanticModels.Base[core_api.CreateAccountV2RequestBody]):

    dictionary = dict(
        request_id="request_id",
        account=dict(
            type="ACCOUNT_TYPE_CUSTOMER",
            smart_contract_version_id="1",
            status="ACCOUNT_STATUS_OPEN",
            activation_timestamp="2020-01-06T00:00:00+00:00",
            stakeholder_ids=["stakeholder_1", "stakeholder_2"],
            id=None,
            parameter_value_hierarchy_node_id=None,
            alias=None,
            details=None,
            processing_group_id=None,
            permitted_denominations=None,
        ),
        create_options=dict(
            parameter_values={"test": dict(string_value="bla")},
            sub_accounts=[
                {
                    "request_id": None,
                    "sub_account": {
                        "id": "sub-account-id",
                        "type": "sub-account-type",
                        "account_id": "account-id",
                        "status": "SUB_ACCOUNT_STATUS_OPEN",
                        "details": None,
                        "name": None,
                    },
                }
            ],
        ),
    )

    resource = core_api.CreateAccountV2RequestBody(
        request_id="request_id",
        account=core_api.CustomerAccountRequestBody(
            smart_contract_version_id="1",
            status=core_api.AccountV2Status.ACCOUNT_STATUS_OPEN,
            activation_timestamp=datetime(2020, 1, 6, tzinfo=UTC),
            stakeholder_ids=["stakeholder_1", "stakeholder_2"],
        ),
        create_options=core_api.CreateOptions(
            parameter_values={"test": core_api.StringParameterValue(string_value="bla")},
            sub_accounts=[
                core_api.CreateSubAccountRequest(
                    sub_account=core_api.SubAccountCreateSubAccount(
                        id="sub-account-id",
                        type="sub-account-type",
                        account_id="account-id",
                        status=SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                    ),
                ),
            ],
        ),
    )


class TestUpdateAccountV2RequestBody(TestPydanticModels.Base[core_api.UpdateAccountV2RequestBody]):

    dictionary = dict(
        request_id="request_id",
        account=dict(
            smart_contract_version_id="1",
            parameter_value_hierarchy_node_id=None,
            processing_label=None,
            status=None,
            stakeholder_ids=None,
            alias=None,
            details=None,
        ),
        update_mask=dict(paths=["smart_contract_version_id"]),
    )

    resource = core_api.UpdateAccountV2RequestBody(
        request_id="request_id",
        account=core_api.UpdateAccountV2Account(
            smart_contract_version_id="1",
        ),
        update_mask=core_api.UpdateMask(paths=["smart_contract_version_id"]),
    )


class TestUpdateAccountV2RequestBodyOneOf(TestCase):
    def test_validate_raises_if_one_of_fails(self):
        with self.assertRaises(OneOfException):
            core_api.UpdateAccountV2RequestBody.model_validate(
                dict(
                    request_id="request_id",
                    account=dict(
                        smart_contract_version_id="1",
                        status="ACCOUNT_STATUS_OPEN",
                        stakeholder_ids=None,
                        alias=None,
                        details=None,
                    ),
                    update_mask=dict(paths=["smart_contract_version_id"]),
                )
            )


class TestPlan(TestPydanticModels.Base[core_api.Plan]):

    dictionary = dict(
        id="id",
        supervisor_contract_version_id="supervisor_contract_version_id",
        processing_group_id="processing_group_id",
        status="PLAN_STATUS_OPEN",
        create_timestamp="2020-01-01T00:00:00+00:00",
        opening_timestamp="2020-01-02T00:00:00+00:00",
        activation_completed_timestamp="2020-01-03T00:00:00+00:00",
        closing_timestamp="2020-01-04T00:00:00+00:00",
        closure_completed_timestamp="2020-01-05T00:00:00+00:00",
        details={"key": "value"},
    )

    resource = core_api.Plan(
        id="id",
        supervisor_contract_version_id="supervisor_contract_version_id",
        processing_group_id="processing_group_id",
        status=core_api.PlanStatus.OPEN,
        create_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
        opening_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
        activation_completed_timestamp=datetime(2020, 1, 3, tzinfo=UTC),
        closing_timestamp=datetime(2020, 1, 4, tzinfo=UTC),
        closure_completed_timestamp=datetime(2020, 1, 5, tzinfo=UTC),
        details={"key": "value"},
    )


class TestPlanNullableFields(TestPydanticModels.Base[core_api.Plan]):

    dictionary = dict(
        id="id",
        supervisor_contract_version_id="supervisor_contract_version_id",
        processing_group_id="processing_group_id",
        status="PLAN_STATUS_OPEN",
        create_timestamp=None,
        opening_timestamp=None,
        activation_completed_timestamp=None,
        closing_timestamp=None,
        closure_completed_timestamp=None,
        details=None,
    )

    resource = core_api.Plan(
        id="id",
        supervisor_contract_version_id="supervisor_contract_version_id",
        processing_group_id="processing_group_id",
        status=core_api.PlanStatus.OPEN,
        create_timestamp=None,
        opening_timestamp=None,
        activation_completed_timestamp=None,
        closing_timestamp=None,
        closure_completed_timestamp=None,
        details=None,
    )


class TestStringParameterValue(TestPydanticModels.Base[core_api.StringParameterValue]):

    dictionary = dict(string_value="my_string_value")
    resource = core_api.StringParameterValue(string_value="my_string_value")


class TestDecimalParameterValue(TestPydanticModels.Base[core_api.DecimalParameterValue]):

    dictionary = dict(decimal_value="1.23")
    resource = core_api.DecimalParameterValue(decimal_value=Decimal("1.23"))


class TestEnumerationParameterValue(TestPydanticModels.Base[core_api.EnumerationParameterValue]):

    dictionary = dict(enumeration_value="my_enum_value")
    resource = core_api.EnumerationParameterValue(enumeration_value="my_enum_value")


class TestDatetimeParameterValue(TestPydanticModels.Base[core_api.DatetimeParameterValue]):

    dictionary = dict(date_time_value="2020-01-01T00:00:00+00:00")
    resource = core_api.DatetimeParameterValue(date_time_value=datetime(2020, 1, 1, tzinfo=UTC))


class TestDatetimeParameterValueValidation(TestCase):

    def test_datetime_with_seconds_raises_error(self):
        with self.assertRaises(ValueError):
            DatetimeParameterValue(date_time_value=datetime(year=2020, month=1, day=2, second=5))

    def test_datetime_with_microseconds_raises_error(self):
        with self.assertRaises(ValueError):
            DatetimeParameterValue(
                date_time_value=datetime(year=2020, month=1, day=2, microsecond=5)
            )

    def test_datetime_with_seconds_and_microseconds_raises_error(self):
        with self.assertRaises(ValueError):
            DatetimeParameterValue(
                date_time_value=datetime(year=2020, month=1, day=2, second=1, microsecond=1)
            )


class TestAccountIdParameterValue(TestPydanticModels.Base[core_api.AccountIdParameterValue]):

    dictionary = dict(account_id_value="my_account_id_value")
    resource = core_api.AccountIdParameterValue(account_id_value="my_account_id_value")


class TestUpdateParameterValueV1RequestBody(
    TestPydanticModels.Base[core_api.UpdateParameterValueV1RequestBody]
):

    dictionary = dict(
        request_id="request_id",
        parameter_value=dict(
            id="parameter_value_id",
            effective_to_timestamp="2020-01-01T00:00:00+00:00",
            is_cancelled=None,
        ),
        is_cancelled_update_options=None,
        update_mask=dict(paths=["effective_to_timestamp"]),
    )

    resource = core_api.UpdateParameterValueV1RequestBody(
        request_id="request_id",
        parameter_value=core_api.UpdateParameterValueV1ParameterValue(
            id="parameter_value_id", effective_to_timestamp=datetime(2020, 1, 1, tzinfo=UTC)
        ),
        update_mask=core_api.UpdateMask(paths=["effective_to_timestamp"]),
    )


class TestUpdateParameterValueV1RequestBodyNoId(
    TestPydanticModels.Base[core_api.UpdateParameterValueV1RequestBody]
):

    dictionary = dict(
        request_id="request_id",
        parameter_value=dict(
            id=None,
            effective_to_timestamp="2020-01-01T00:00:00+00:00",
            is_cancelled=None,
        ),
        is_cancelled_update_options=None,
        update_mask=dict(paths=["effective_to_timestamp"]),
    )

    resource = core_api.UpdateParameterValueV1RequestBody(
        request_id="request_id",
        parameter_value=core_api.UpdateParameterValueV1ParameterValue(
            id=None, effective_to_timestamp=datetime(2020, 1, 1, tzinfo=UTC)
        ),
        update_mask=core_api.UpdateMask(paths=["effective_to_timestamp"]),
    )


class TestUpdateParameterValueV1RequestBodyIsCancelled(
    TestPydanticModels.Base[core_api.UpdateParameterValueV1RequestBody]
):

    dictionary = dict(
        request_id="request_id",
        parameter_value=dict(
            id="parameter_value_id", effective_to_timestamp=None, is_cancelled=True
        ),
        is_cancelled_update_options=dict(skip_pre_parameter_change_hook=True),
        update_mask=dict(paths=["is_cancelled"]),
    )

    resource = core_api.UpdateParameterValueV1RequestBody(
        request_id="request_id",
        parameter_value=core_api.UpdateParameterValueV1ParameterValue(
            id="parameter_value_id",
            is_cancelled=True,
        ),
        is_cancelled_update_options=core_api.IsCancelledUpdateOptions(
            skip_pre_parameter_change_hook=True
        ),
        update_mask=core_api.UpdateMask(paths=["is_cancelled"]),
    )


class TestParameterValueResource(TestPydanticModels.Base[core_api.ParameterValueResource]):
    dictionary = dict(
        id="request_id",
        parameter_id="parameter_id_1",
        create_timestamp="2020-01-01T00:00:00+00:00",
        update_timestamp="2020-01-01T00:00:00+00:00",
        effective_from_timestamp="2024-01-01T00:00:00+00:00",
        effective_to_timestamp="2040-01-01T00:00:00+00:00",
        is_cancelled=True,
        is_backdated=True,
        value=dict(string_value="string"),
        cancel_timestamp="2025-01-01T00:00:00+00:00",
    )
    resource = core_api.ParameterValueResource(
        id="request_id",
        parameter_id="parameter_id_1",
        create_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
        update_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
        effective_from_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        effective_to_timestamp=datetime(2040, 1, 1, tzinfo=UTC),
        is_cancelled=True,
        is_backdated=True,
        value=core_api.StringParameterValue(string_value="string"),
        cancel_timestamp=datetime(2025, 1, 1, tzinfo=UTC),
    )


class TestValidateCreateParameterValuesV1(TestCase):

    def test_overloaded_create_parameter_value_1(self):
        with self.assertRaises(OneOfException):
            core_api.CreateParameterValueV1ParameterValue(
                parameter_id="parameter_id_str",
                value=StringParameterValue(string_value="new_value"),
                account_id="account_id_1",
                global_=True,
                parameter_value_hierarchy_node_id="parameter_value_hierarchy_node_id_1",
            )

    def test_overloaded_create_parameter_value_2(self):
        with self.assertRaises(OneOfException):
            core_api.CreateParameterValueV1ParameterValue(
                parameter_id="parameter_id_str",
                value=StringParameterValue(string_value="new_value"),
                account_id="account_id_1",
                global_=True,
            )

    def test_overloaded_create_parameter_value_3(self):
        with self.assertRaises(OneOfException):
            core_api.CreateParameterValueV1ParameterValue(
                parameter_id="parameter_id_str",
                value=StringParameterValue(string_value="new_value"),
                account_id="account_id_1",
                parameter_value_hierarchy_node_id="parameter_value_hierarchy_node_id_1",
            )

    def test_overloaded_create_parameter_value_4(self):
        with self.assertRaises(OneOfException):
            core_api.CreateParameterValueV1ParameterValue(
                parameter_id="parameter_id_str",
                value=StringParameterValue(string_value="new_value"),
                global_=True,
                parameter_value_hierarchy_node_id="parameter_value_hierarchy_node_id_1",
            )


class TestCreateParameterValueHierarchyNode(
    TestPydanticModels.Base[core_api.CreateParameterValueHierarchyNode]
):
    dictionary = {
        "id": "parameter_value_hierarchy_node_id",
        "name": "parameter_value_hierarchy_node_name",
        "parent_id": "parameter_value_hierarchy_node_parent_id",
        "metadata": {"some_key": "some-value"},
    }
    resource = core_api.CreateParameterValueHierarchyNode(
        id="parameter_value_hierarchy_node_id",
        name="parameter_value_hierarchy_node_name",
        parent_id="parameter_value_hierarchy_node_parent_id",
        metadata={"some_key": "some-value"},
    )


class TestCreateParameterValueHierarchyNodeRequestBody(
    TestPydanticModels.Base[core_api.CreateParameterValueHierarchyNodeRequestBody]
):

    dictionary = {
        "request_id": "request-id-1",
        "parameter_value_hierarchy_node": {
            "id": "parameter_value_hierarchy_node_id",
            "name": "parameter_value_hierarchy_node_name",
            "parent_id": "parameter_value_hierarchy_node_parent_id",
            "metadata": {"some_key": "some-value"},
        },
    }

    resource = core_api.CreateParameterValueHierarchyNodeRequestBody(
        request_id="request-id-1",
        parameter_value_hierarchy_node=core_api.CreateParameterValueHierarchyNode(
            id="parameter_value_hierarchy_node_id",
            name="parameter_value_hierarchy_node_name",
            parent_id="parameter_value_hierarchy_node_parent_id",
            metadata={"some_key": "some-value"},
        ),
    )


class TestPostingInstruction(TestPydanticModels.Base[core_api.PostingInstruction]):
    dictionary = {
        "client_transaction_id": "txn-1",
        "value_timestamp": "2025-01-01T00:00:00+00:00",
        "booking_timestamp": "2025-01-01T00:00:00+00:00",
        "instruction_details": None,
        "transaction_code": None,
        "override": None,
        "inbound_hard_settlement": {
            "amount": "1.00",
            "denomination": "GBP",
            "internal_account_id": "contra-acc",
            "internal_account_processing_label": None,
            "target_account": {"account_id": "account-1", "payment_device_token": None},
            "advice": False,
            "asset": None,
            "target_account_address": None,
            "target_sub_account_id": None,
        },
        "custom_instruction": None,
        "authorisation_adjustment": None,
        "inbound_authorisation": None,
        "outbound_hard_settlement": None,
        "outbound_authorisation": None,
        "release": None,
        "settlement": None,
        "transfer": None,
    }

    resource = core_api.PostingInstruction(
        client_transaction_id="txn-1",
        value_timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        booking_timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        instruction_details=None,
        transaction_code=None,
        override=None,
        inbound_hard_settlement=core_api.InboundHardSettlement(
            amount=Decimal("1.00"),
            denomination="GBP",
            internal_account_id="contra-acc",
            target_account=core_api.TargetAccount(account_id="account-1"),
        ),
    )

    def test_adjustment_amount_rejects_both_fields_populated(self):
        with self.assertRaises(OneOfException):
            core_api.PostingInstruction(
                client_transaction_id="txn-2",
                value_timestamp=datetime(2025, 1, 1, tzinfo=UTC),
                booking_timestamp=datetime(2025, 1, 1, tzinfo=UTC),
                instruction_details=None,
                transaction_code=None,
                override=None,
                authorisation_adjustment=core_api.AuthorisationAdjustment(
                    adjustment_amount=core_api.AdjustmentAmount(
                        amount=Decimal("10"),
                        replacement_amount=Decimal("20"),
                    ),
                ),
            )

    def test_target_account_rejects_both_fields_populated(self):
        with self.assertRaises(OneOfException):
            core_api.PostingInstruction(
                client_transaction_id="txn-3",
                value_timestamp=datetime(2025, 1, 1, tzinfo=UTC),
                booking_timestamp=datetime(2025, 1, 1, tzinfo=UTC),
                instruction_details=None,
                transaction_code=None,
                override=None,
                outbound_authorisation=core_api.OutboundAuthorisation(
                    amount=Decimal("1.00"),
                    denomination="GBP",
                    internal_account_id="contra-acc",
                    target_account=core_api.TargetAccount(
                        account_id="account-1",
                        payment_device_token="token",
                    ),
                ),
            )

    def test_internal_account_id_and_label_cannot_both_be_populated(self):
        with self.assertRaises(OneOfException):
            core_api.PostingInstruction(
                client_transaction_id="txn-3",
                value_timestamp=datetime(2025, 1, 1, tzinfo=UTC),
                booking_timestamp=datetime(2025, 1, 1, tzinfo=UTC),
                instruction_details=None,
                transaction_code=None,
                override=None,
                outbound_authorisation=core_api.OutboundAuthorisation(
                    amount=Decimal("1.00"),
                    denomination="GBP",
                    internal_account_id="contra-acc",
                    internal_account_processing_label="contra-label",
                    target_account=core_api.TargetAccount(
                        account_id="account-1",
                    ),
                ),
            )


class TestAuthorisationAndSettlementValidation(TestCase):
    def test_outbound_authorisation_raises_if_target_sub_account_id_populated_without_account_id(
        self,
    ):
        with self.assertRaises(ValueError) as ctx:
            core_api.OutboundAuthorisation(
                amount=Decimal("1.00"),
                denomination="GBP",
                internal_account_id="contra-acc",
                target_account=core_api.TargetAccount(payment_device_token="token"),
                target_sub_account_id="sub_acc_1",
            )
        self.assertIn(
            "target_account's account_id must be set if `target_sub_account_id` is not None",
            str(ctx.exception),
        )

    def test_inbound_authorisation_raises_if_target_sub_account_id_populated_without_account_id(
        self,
    ):
        with self.assertRaises(ValueError) as ctx:
            core_api.InboundAuthorisation(
                amount=Decimal("1.00"),
                denomination="GBP",
                internal_account_id="contra-acc",
                target_account=core_api.TargetAccount(payment_device_token="token"),
                target_sub_account_id="sub_acc_1",
            )
        self.assertIn(
            "target_account's account_id must be set if `target_sub_account_id` is not None",
            str(ctx.exception),
        )

    def test_outbound_authorisation_valid_with_both_account_id_and_sub_account_id(self):
        core_api.OutboundAuthorisation(
            amount=Decimal("1.00"),
            denomination="GBP",
            internal_account_id="contra-acc",
            target_account=core_api.TargetAccount(account_id="account-1"),
            target_sub_account_id="sub_acc_1",
        )

    def test_inbound_authorisation_valid_with_both_account_id_and_sub_account_id(self):
        core_api.InboundAuthorisation(
            amount=Decimal("1.00"),
            denomination="GBP",
            internal_account_id="contra-acc",
            target_account=core_api.TargetAccount(account_id="account-1"),
            target_sub_account_id="sub_acc_1",
        )


class TestTransferValidation(TestCase):
    def test_raises_if_creditor_target_sub_account_id_populated_without_address(self):
        with self.assertRaises(ValueError) as ctx:
            core_api.Transfer(
                amount=Decimal("10.00"),
                creditor_target_account=core_api.TargetAccount(account_id="creditor-acc"),
                debtor_target_account=core_api.TargetAccount(account_id="debtor-acc"),
                denomination="GBP",
                creditor_target_sub_account_id="sub_acc_1",
            )
        self.assertIn("creditor_target_account_address", str(ctx.exception))

    def test_raises_if_creditor_target_account_address_populated_without_sub_account_id(self):
        with self.assertRaises(ValueError) as ctx:
            core_api.Transfer(
                amount=Decimal("10.00"),
                creditor_target_account=core_api.TargetAccount(account_id="creditor-acc"),
                debtor_target_account=core_api.TargetAccount(account_id="debtor-acc"),
                denomination="GBP",
                creditor_target_account_address="address_1",
            )
        self.assertIn("creditor_target_account_address", str(ctx.exception))

    def test_raises_if_debtor_target_sub_account_id_populated_without_address(self):
        with self.assertRaises(ValueError) as ctx:
            core_api.Transfer(
                amount=Decimal("10.00"),
                creditor_target_account=core_api.TargetAccount(account_id="creditor-acc"),
                debtor_target_account=core_api.TargetAccount(account_id="debtor-acc"),
                denomination="GBP",
                debtor_target_sub_account_id="sub_acc_1",
            )
        self.assertIn("debtor_target_account_address", str(ctx.exception))

    def test_raises_if_debtor_target_account_address_populated_without_sub_account_id(self):
        with self.assertRaises(ValueError) as ctx:
            core_api.Transfer(
                amount=Decimal("10.00"),
                creditor_target_account=core_api.TargetAccount(account_id="creditor-acc"),
                debtor_target_account=core_api.TargetAccount(account_id="debtor-acc"),
                denomination="GBP",
                debtor_target_account_address="address_1",
            )
        self.assertIn("debtor_target_account_address", str(ctx.exception))

    def test_no_error_if_both_populated_or_neither_populated(self):
        # neither creditor nor the debtor target sub-accounts nor their target addresses
        # are populated
        core_api.Transfer(
            amount=Decimal("10.00"),
            creditor_target_account=core_api.TargetAccount(account_id="creditor-acc"),
            debtor_target_account=core_api.TargetAccount(account_id="debtor-acc"),
            denomination="GBP",
        )
        # both the creditor and debtor's sub-account id and target addresses are populated
        core_api.Transfer(
            amount=Decimal("10.00"),
            creditor_target_account=core_api.TargetAccount(account_id="creditor-acc"),
            debtor_target_account=core_api.TargetAccount(account_id="debtor-acc"),
            denomination="GBP",
            debtor_target_sub_account_id="sub_acc_d",
            debtor_target_account_address="addr_d",
            creditor_target_sub_account_id="sub_acc_c",
            creditor_target_account_address="addr_c",
        )


class TestPostingInstructionBatch(TestPydanticModels.Base[core_api.PostingInstructionBatch]):
    dictionary = {
        "client_id": "client-id",
        "client_batch_id": "client-batch-id",
        "batch_details": {"key": "value"},
        "value_timestamp": None,
        "booking_timestamp": None,
        "posting_instructions": [
            {
                "client_transaction_id": "txn-1",
                "value_timestamp": "2025-01-01T00:00:00+00:00",
                "booking_timestamp": "2025-01-01T00:00:00+00:00",
                "instruction_details": None,
                "transaction_code": None,
                "override": None,
                "authorisation_adjustment": None,
                "custom_instruction": {
                    "postings": [
                        {
                            "amount": "1",
                            "account_id": "account-1",
                            "credit": False,
                            "denomination": "GBP",
                            "phase": "POSTING_PHASE_COMMITTED",
                            "account_address": "DEFAULT",
                            "asset": "COMMERCIAL_BANK_MONEY",
                            "internal_account_processing_label": "",
                            "sub_account_id": "sub_account_1",
                        },
                        {
                            "amount": "1",
                            "account_id": "account-2",
                            "credit": True,
                            "denomination": "GBP",
                            "phase": "POSTING_PHASE_COMMITTED",
                            "account_address": "DEFAULT",
                            "asset": "COMMERCIAL_BANK_MONEY",
                            "internal_account_processing_label": "",
                            "sub_account_id": "sub_account_2",
                        },
                    ]
                },
                "inbound_authorisation": None,
                "inbound_hard_settlement": None,
                "outbound_authorisation": None,
                "outbound_hard_settlement": None,
                "release": None,
                "settlement": None,
                "transfer": None,
            }
        ],
    }

    resource = core_api.PostingInstructionBatch(
        client_id="client-id",
        client_batch_id="client-batch-id",
        batch_details={"key": "value"},
        value_timestamp=None,
        booking_timestamp=None,
        posting_instructions=[
            core_api.PostingInstruction(
                client_transaction_id="txn-1",
                value_timestamp=datetime(2025, 1, 1, tzinfo=UTC),
                booking_timestamp=datetime(2025, 1, 1, tzinfo=UTC),
                instruction_details=None,
                transaction_code=None,
                override=None,
                custom_instruction=core_api.CustomInstruction(
                    postings=[
                        core_api.Posting(
                            amount="1",
                            account_id="account-1",
                            credit=False,
                            denomination="GBP",
                            phase=core_api.PostingPhase.COMMITTED,
                            account_address="DEFAULT",
                            asset="COMMERCIAL_BANK_MONEY",
                            internal_account_processing_label="",
                            sub_account_id="sub_account_1",
                        ),
                        core_api.Posting(
                            amount="1",
                            account_id="account-2",
                            credit=True,
                            denomination="GBP",
                            phase=core_api.PostingPhase.COMMITTED,
                            account_address="DEFAULT",
                            asset="COMMERCIAL_BANK_MONEY",
                            internal_account_processing_label="",
                            sub_account_id="sub_account_2",
                        ),
                    ]
                ),
            )
        ],
    )


class TestCreatePostingInstructionBatchRequest(
    TestPydanticModels.Base[core_api.CreatePostingInstructionBatchRequest]
):
    resource = core_api.CreatePostingInstructionBatchRequest(
        request_id="request-id",
        dry_run=False,
        shard_key="optional-key",
        posting_instruction_batch=core_api.PostingInstructionBatch(
            client_id="client-id",
            client_batch_id="client-batch-id",
            batch_details={"key": "value"},
            value_timestamp=None,
            booking_timestamp=None,
            posting_instructions=[
                core_api.PostingInstruction(
                    client_transaction_id="txn-1",
                    value_timestamp=datetime(2025, 1, 1, tzinfo=UTC),
                    booking_timestamp=datetime(2025, 1, 1, tzinfo=UTC),
                    instruction_details=None,
                    transaction_code=None,
                    override=None,
                    inbound_hard_settlement=core_api.InboundHardSettlement(
                        amount=Decimal("1.00"),
                        denomination="GBP",
                        internal_account_id="contra-acc",
                        target_account=core_api.TargetAccount(account_id="account-1"),
                    ),
                )
            ],
        ),
    )
    dictionary = dict(
        request_id="request-id",
        dry_run=False,
        shard_key="optional-key",
        posting_instruction_batch=dict(
            client_id="client-id",
            client_batch_id="client-batch-id",
            batch_details={"key": "value"},
            value_timestamp=None,
            booking_timestamp=None,
            posting_instructions=[
                dict(
                    client_transaction_id="txn-1",
                    value_timestamp="2025-01-01T00:00:00+00:00",
                    booking_timestamp="2025-01-01T00:00:00+00:00",
                    instruction_details=None,
                    transaction_code=None,
                    override=None,
                    inbound_hard_settlement=dict(
                        advice=False,
                        asset=None,
                        amount="1.00",
                        denomination="GBP",
                        internal_account_id="contra-acc",
                        internal_account_processing_label=None,
                        target_account=dict(account_id="account-1", payment_device_token=None),
                        target_account_address=None,
                        target_sub_account_id=None,
                    ),
                    outbound_hard_settlement=None,
                    outbound_authorisation=None,
                    inbound_authorisation=None,
                    transfer=None,
                    custom_instruction=None,
                    authorisation_adjustment=None,
                    release=None,
                    settlement=None,
                )
            ],
        ),
    )


class TestCommittedPostingInstruction(
    TestPydanticModels.Base[core_api.CommittedPostingInstruction]
):
    # the example isn't functionally realistic (e.g. committed postings + violations)
    # but it allows us to test the parsing since this depends solely on individual attribute values
    resource = core_api.CommittedPostingInstruction(
        id="some-id",
        posting_instruction_batch_id="batch-id",
        client_transaction_id="txn-does-not-exist",
        instruction_details={"a": "b"},
        value_timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        booking_timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        booking_localised_date_time=None,
        enrichments={"account_a": {"c": "d"}},
        insertion_timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        source_insertion_timestamp=datetime(2025, 1, 1, tzinfo=UTC),
        committed_postings=[
            core_api.Posting(
                credit=True,
                amount="1",
                denomination="GBP",
                account_id="account_a",
                account_address="DEFAULT",
                asset="COMMERCIAL_BANK_MONEY",
                phase=core_api.PostingPhase.COMMITTED,
                internal_account_processing_label="",
                sub_account_id="sub_account_id",
            )
        ],
        posting_violations=[
            core_api.PostingViolation(
                type=core_api.PostingViolationType.CLIENT_TRANSACTION_DOES_NOT_EXIST
            )
        ],
        account_violations=[
            core_api.AccountViolation(
                account_id="account_a",
                type=core_api.AccountViolationType.ACCOUNT_NOT_PRESENT,
            )
        ],
        restriction_violations=[
            core_api.RestrictionViolation(
                restriction_set_id="123",
                account_id="account_a",
                type=core_api.RestrictionViolationType.LIMIT_CREDITS,
            )
        ],
        contract_violations=[
            core_api.ContractViolation(
                account_id="account_a",
                type=core_api.ContractViolationType.TC_BREACH,
                violation_type=core_api.ContractExecutionViolationType.TC_BREACH,
            ),
        ],
    )
    dictionary = dict(
        id="some-id",
        posting_instruction_batch_id="batch-id",
        client_transaction_id="txn-does-not-exist",
        instruction_details={"a": "b"},
        value_timestamp="2025-01-01T00:00:00+00:00",
        booking_timestamp="2025-01-01T00:00:00+00:00",
        booking_localised_date_time=None,
        enrichments={"account_a": {"c": "d"}},
        insertion_timestamp="2025-01-01T00:00:00+00:00",
        source_insertion_timestamp="2025-01-01T00:00:00+00:00",
        committed_postings=[
            dict(
                credit=True,
                amount="1",
                denomination="GBP",
                account_id="account_a",
                account_address="DEFAULT",
                asset="COMMERCIAL_BANK_MONEY",
                phase="POSTING_PHASE_COMMITTED",
                internal_account_processing_label="",
                sub_account_id="sub_account_id",
            )
        ],
        posting_violations=[dict(type="POSTING_VIOLATION_CLIENT_TRANSACTION_DOES_NOT_EXIST")],
        account_violations=[
            dict(
                type="ACCOUNT_VIOLATION_ACCOUNT_NOT_PRESENT",
                payment_device_token="",
                account_id="account_a",
                internal_account_processing_label="",
                sub_account_id="",
            )
        ],
        restriction_violations=[
            dict(
                restriction_set_id="123",
                account_id="account_a",
                type="RESTRICTION_VIOLATION_TYPE_LIMIT_CREDITS",
                customer_id="",
                payment_device_id="",
                requires_review=False,
            )
        ],
        contract_violations=[
            dict(
                account_id="account_a",
                plan_id="",
                reason="",
                sub_account_id="",
                type="CONTRACT_VIOLATION_BREACH_TERMS_AND_CONDITIONS",
                violation_type="CONTRACT_EXECUTION_VIOLATION_BREACH_TERMS_AND_CONDITIONS",
            )
        ],
    )


class TestAccountViolationSubAccountsNotPresent(TestPydanticModels.Base[core_api.AccountViolation]):
    dictionary = dict(
        account_id="account_a",
        payment_device_token="token",
        type="ACCOUNT_VIOLATION_SUB_ACCOUNT_NOT_PRESENT",
        internal_account_processing_label="label",
        sub_account_id="sub_account_a",
    )
    resource = core_api.AccountViolation(
        account_id="account_a",
        payment_device_token="token",
        type=core_api.AccountViolationType.SUB_ACCOUNT_NOT_PRESENT,
        internal_account_processing_label="label",
        sub_account_id="sub_account_a",
    )


class TestAccountViolationValueOrBookingTimestampBeforeSubAccountActivation(
    TestPydanticModels.Base[core_api.AccountViolation]
):
    dictionary = dict(
        account_id="account_a",
        payment_device_token="token",
        type="ACCOUNT_VIOLATION_VALUE_OR_BOOKING_TIMESTAMP_BEFORE_SUB_ACCOUNT_ACTIVATION",
        internal_account_processing_label="label",
        sub_account_id="sub_account_a",
    )
    resource = core_api.AccountViolation(
        account_id="account_a",
        payment_device_token="token",
        type=core_api.AccountViolationType.VALUE_OR_BOOKING_TIMESTAMP_BEFORE_SUB_ACCOUNT_ACTIVATION,
        internal_account_processing_label="label",
        sub_account_id="sub_account_a",
    )


class TestAccountViolationAddressNotPermitted(TestPydanticModels.Base[core_api.AccountViolation]):
    dictionary = dict(
        account_id="account_a",
        payment_device_token="token",
        type="ACCOUNT_VIOLATION_ADDRESS_NOT_PERMITTED",
        internal_account_processing_label="label",
        sub_account_id="sub_account_a",
    )
    resource = core_api.AccountViolation(
        account_id="account_a",
        payment_device_token="token",
        type=core_api.AccountViolationType.ADDRESS_NOT_PERMITTED,
        internal_account_processing_label="label",
        sub_account_id="sub_account_a",
    )


class TestAccountViolationSubAccountsInvalid(TestPydanticModels.Base[core_api.AccountViolation]):
    dictionary = dict(
        account_id="account_a",
        payment_device_token="token",
        type="ACCOUNT_VIOLATION_SUB_ACCOUNT_STATUS_INVALID",
        internal_account_processing_label="label",
        sub_account_id="sub_account_a",
    )
    resource = core_api.AccountViolation(
        account_id="account_a",
        payment_device_token="token",
        type=core_api.AccountViolationType.SUB_ACCOUNT_STATUS_INVALID,
        internal_account_processing_label="label",
        sub_account_id="sub_account_a",
    )


class TestPosting(TestPydanticModels.Base[core_api.Posting]):

    dictionary = dict(
        credit=True,
        amount="1.00",
        denomination="USD",
        account_id="account_id",
        account_address="address",
        asset="asset",
        phase="POSTING_PHASE_COMMITTED",
        internal_account_processing_label="label",
        sub_account_id="sub_account_id",
    )
    resource = core_api.Posting(
        credit=True,
        amount="1.00",
        denomination="USD",
        account_id="account_id",
        account_address="address",
        asset="asset",
        phase=core_api.PostingPhase.COMMITTED,
        internal_account_processing_label="label",
        sub_account_id="sub_account_id",
    )


class TestPostingWithoutDefaults(TestPydanticModels.Base[core_api.Posting]):

    dictionary = dict(
        credit=True,
        amount="1.00",
        denomination="USD",
        account_id="account_id",
        account_address="address",
        asset="asset",
        phase="POSTING_PHASE_COMMITTED",
        internal_account_processing_label="",
        sub_account_id="sub_account_id",
    )
    resource = core_api.Posting(
        credit=True,
        amount="1.00",
        denomination="USD",
        account_id="account_id",
        account_address="address",
        asset="asset",
        phase=core_api.PostingPhase.COMMITTED,
        sub_account_id="sub_account_id",
    )


class TestListPostingInstructionBatchesRequest(
    TestPydanticModels.Base[core_api.ListPostingInstructionBatchesRequest]
):
    resource = core_api.ListPostingInstructionBatchesRequest(
        page_size=20,
        page_token="token",
        order_by_direction=core_api.OrderByDirection.ASC,
        account_ids=["a", "b"],
        client_batch_ids=["batch-1"],
        client_transaction_ids=None,
        payment_device_tokens=None,
        start_time=datetime(2025, 1, 1, tzinfo=UTC),
        end_time=datetime(2025, 1, 2, tzinfo=UTC),
    )
    dictionary = dict(
        page_size=20,
        page_token="token",
        order_by_direction="ORDER_BY_ASC",
        account_ids=["a", "b"],
        client_batch_ids=["batch-1"],
        client_transaction_ids=None,
        payment_device_tokens=None,
        start_time="2025-01-01T00:00:00+00:00",
        end_time="2025-01-02T00:00:00+00:00",
    )


class TestAdjustment(TestPydanticModels.Base[core_api.Adjustment]):
    resource = core_api.Adjustment(
        id="some-id",
        schedule_job_id="sched-job-id",
        resource_adjustment_count=1,
        account_id="acc-1",
        status=core_api.AdjustmentStatus.COMPLETED,
        create_timestamp=datetime(2025, 1, 1, 2, tzinfo=UTC),
        update_timestamp=datetime(2025, 1, 1, 3, tzinfo=UTC),
        previous_watermark_timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        timeline_start_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        timeline_end_timestamp=datetime(2025, 1, 1, 1, tzinfo=UTC),
    )
    dictionary = dict(
        id="some-id",
        schedule_job_id="sched-job-id",
        resource_adjustment_count=1,
        account_id="acc-1",
        correction_posting_instruction_batch_ids=None,
        error=None,
        status="STATUS_COMPLETED",
        create_timestamp="2025-01-01T02:00:00+00:00",
        update_timestamp="2025-01-01T03:00:00+00:00",
        previous_watermark_timestamp="2024-12-31T00:00:00+00:00",
        timeline_start_timestamp="2024-01-01T00:00:00+00:00",
        timeline_end_timestamp="2025-01-01T01:00:00+00:00",
    )


class TestListAdjustmentsRequest(TestPydanticModels.Base[core_api.ListAdjustmentsRequest]):
    dictionary = dict(
        page_size=5,
        page_token="token1",
        account_ids=["acc-id-1", "acc-id-2"],
        schedule_job_ids=None,
    )
    resource = core_api.ListAdjustmentsRequest(
        page_size=5,
        page_token="token1",
        account_ids=["acc-id-1", "acc-id-2"],
        schedule_job_ids=None,
    )

    def test_list_request_accepts_schedule_job_ids(self):
        request = core_api.ListAdjustmentsRequest(
            page_size=20,
            schedule_job_ids=["some-res-id"],
        )
        self.assertEqual(request.page_size, 20)
        assert request.schedule_job_ids is not None
        self.assertIn("some-res-id", request.schedule_job_ids)

    def test_list_request_raise_error_if_both_filters_specified(self):
        with self.assertRaises(OneOfException):
            core_api.ListAdjustmentsRequest(
                page_size=20,
                account_ids=["some-res-id"],
                schedule_job_ids=["some-other-id"],
            )


class TestListAdjustmentsResponse(TestPydanticModels.Base[core_api.ListAdjustmentsResponse]):
    dictionary = dict(
        adjustments=[
            {
                "id": "adj-id-1",
                "schedule_job_id": "sched-job-id",
                "resource_adjustment_count": 2,
                "account_id": "acc-id",
                "status": "STATUS_PENDING",
                "error": {
                    "message": "Something went wrong",
                    "code": "ALREADY_EXISTS",
                    "details": {"id": "exists"},
                },
                "create_timestamp": "2020-01-01T00:00:00+00:00",
                "update_timestamp": "2020-01-02T00:00:00+00:00",
                "previous_watermark_timestamp": None,
                "timeline_start_timestamp": None,
                "timeline_end_timestamp": "2020-01-03T00:00:00+00:00",
                "correction_posting_instruction_batch_ids": None,
            }
        ],
        previous_page_token="prev-token",
        next_page_token="next-token",
    )
    resource = core_api.ListAdjustmentsResponse(
        adjustments=[
            core_api.Adjustment(
                id="adj-id-1",
                schedule_job_id="sched-job-id",
                resource_adjustment_count=2,
                account_id="acc-id",
                status=core_api.AdjustmentStatus.PENDING,
                error=core_api.AdjustmentError(
                    message="Something went wrong",
                    code=core_api.ErrorCode.ALREADY_EXISTS,
                    details={"id": "exists"},
                ),
                create_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
                update_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
                previous_watermark_timestamp=None,
                timeline_start_timestamp=None,
                timeline_end_timestamp=datetime(2020, 1, 3, tzinfo=UTC),
                correction_posting_instruction_batch_ids=None,
            )
        ],
        previous_page_token="prev-token",
        next_page_token="next-token",
    )


class TestBulkRetryAdjustmentsRequest(
    TestPydanticModels.Base[core_api.BulkRetryAdjustmentsRequest]
):
    dictionary = dict(
        retry_requests=[
            {
                "request_id": "some-uuid",
                "id": "acc-id-1",
            },
            {
                "request_id": "some-other-uuid",
                "id": "acc-id-2",
            },
        ]
    )
    resource = core_api.BulkRetryAdjustmentsRequest(
        retry_requests=[
            core_api.AdjustmentsRetryRequest(request_id="some-uuid", id="acc-id-1"),
            core_api.AdjustmentsRetryRequest(request_id="some-other-uuid", id="acc-id-2"),
        ]
    )


class TestBulkRetryAdjustmentsResponse(
    TestPydanticModels.Base[core_api.BulkRetryAdjustmentsResponse]
):
    dictionary = dict(
        errors={
            "adj-id-1": {
                "message": "Something went wrong",
                "code": "INVALID_ARGUMENT",
                "details": {"field": "missing"},
            }
        }
    )
    resource = core_api.BulkRetryAdjustmentsResponse(
        errors={
            "adj-id-1": core_api.AdjustmentError(
                message="Something went wrong",
                code=core_api.ErrorCode.INVALID_ARGUMENT,
                details={"field": "missing"},
            )
        }
    )


class TestBatchGetAdjustmentsRequest(TestPydanticModels.Base[core_api.BatchGetAdjustmentsRequest]):
    dictionary = dict(ids=["A1", "A2", "A3"])
    resource = core_api.BatchGetAdjustmentsRequest(ids=["A1", "A2", "A3"])


class TestBatchGetAdjustmentsResponse(
    TestPydanticModels.Base[core_api.BatchGetAdjustmentsResponse]
):
    dictionary = dict(
        adjustments={
            "adj-id-1": {
                "id": "adj-id-1",
                "schedule_job_id": "sched-job-id",
                "resource_adjustment_count": 2,
                "account_id": "acc-id",
                "status": "STATUS_COMPLETED",
                "error": None,
                "create_timestamp": "2020-01-01T00:00:00+00:00",
                "update_timestamp": "2020-01-02T00:00:00+00:00",
                "previous_watermark_timestamp": None,
                "timeline_start_timestamp": None,
                "timeline_end_timestamp": "2020-01-03T00:00:00+00:00",
                "correction_posting_instruction_batch_ids": None,
            }
        }
    )
    resource = core_api.BatchGetAdjustmentsResponse(
        adjustments={
            "adj-id-1": core_api.Adjustment(
                id="adj-id-1",
                schedule_job_id="sched-job-id",
                resource_adjustment_count=2,
                account_id="acc-id",
                status=core_api.AdjustmentStatus.COMPLETED,
                error=None,
                create_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
                update_timestamp=datetime(2020, 1, 2, tzinfo=UTC),
                previous_watermark_timestamp=None,
                timeline_start_timestamp=None,
                timeline_end_timestamp=datetime(2020, 1, 3, tzinfo=UTC),
                correction_posting_instruction_batch_ids=None,
            )
        }
    )


class TestBatchGetProductsResponse(TestPydanticModels.Base[core_api.BatchGetProductsResponse]):
    dictionary = {
        "products": {
            "product_1": {
                "id": "product_1",
                "display_name": "display",
                "is_internal": True,
                "current_version_id": "1",
            },
            "product_2": {
                "id": "product_2",
                "display_name": "display",
                "is_internal": False,
                "current_version_id": "2",
            },
        }
    }
    resource = core_api.BatchGetProductsResponse(
        products={
            "product_1": core_api.Product(
                id="product_1", display_name="display", is_internal=True, current_version_id="1"
            ),
            "product_2": core_api.Product(
                id="product_2", display_name="display", is_internal=False, current_version_id="2"
            ),
        }
    )


class TestProductVersion(TestPydanticModels.Base[core_api.ProductVersion]):
    dictionary = {
        "id": "fixed_term_deposit_v1_0_0",
        "product_id": "fixed_term_deposit",
        "display_name": "Fixed Term Deposit Product v1.0.0",
        "display_version_number": {
            "major": 1,
            "minor": 0,
            "patch": 0,
            "label": "Release Candidate",
        },
        "description": "A product for a fixed term deposit account.",
        "summary": "High-level summary of the product version.",
        "tags": ["savings", "term_deposit"],
        "core_tags": [
            "PRODUCT_VERSION_CORE_TAG_FIXED_TERM_DEPOSIT",
            "PRODUCT_VERSION_CORE_TAG_DEPOSIT",
        ],
        "is_current": True,
        "code": "print('Fixed Term Deposit Contract Code')",
        "params": [
            {
                "name": "interest_rate",
                "display_name": "Annual Interest Rate",
                "description": "The interest rate applied to the deposit.",
                "value": "0.035",
                "default_value": "0.03",
                "effective_timestamp": "2025-01-01T00:00:00+00:00",
                "level": "LEVEL_PRODUCT",
                "update_permission": "UPDATE_PERMISSION_FIXED",
                "derived": False,
                "is_optional": False,
                "denomination": None,
                "account": None,
                "date": None,
                "str": None,
                "values": None,
                "number": {
                    "value_type": "NUMBER_FIELD_DISPLAY_STYLE_PERCENTAGE",
                    "min_value": "0.005",
                    "max_value": "0.10",
                    "step": "0.0001",
                },
            },
            {
                "name": "term_length",
                "display_name": "Deposit Term (Months)",
                "description": "The duration of the deposit in months.",
                "value": "12",
                "default_value": "6",
                "effective_timestamp": "2024-03-20T10:00:00+00:00",
                "level": "LEVEL_INSTANCE",
                "update_permission": "UPDATE_PERMISSION_CUSTOMER_EDITABLE",
                "derived": False,
                "is_optional": False,
                "denomination": None,
                "number": None,
                "account": None,
                "date": None,
                "str": None,
                "values": {
                    "value_choices": [
                        {"value": "6", "display_name": "6 Months"},
                        {"value": "12", "display_name": "12 Months"},
                        {"value": "24", "display_name": "24 Months"},
                    ]
                },
            },
        ],
        "address_details": [
            {
                "address_name": "DEFAULT",
                "description": "The default account address for balances.",
                "tags": ["account_balances"],
            }
        ],
        "attributes": [
            {
                "name": "customer_segment",
                "data_type": {
                    "string_type": {},
                    "decimal_type": None,
                    "datetime_type": None,
                },
            }
        ],
        "contracts_language_api_version": {"major": 4, "minor": 1, "patch": 0, "label": ""},
        "contract_module_details": {
            "alias_to_shared_function_details": {
                "key": {
                    "shared_functions": [
                        {
                            "name": "share_func_1",
                            "args": [
                                {
                                    "name": "name",
                                    "type": "string",
                                }
                            ],
                            "return_type": "string",
                        }
                    ],
                }
            }
        },
        "expected_parameters": [
            {
                "parameter_id": "INTEREST_RATE",
                "is_optional": False,
                "triggers_pre_parameter_change_hook": False,
                "triggers_post_parameter_change_hook": True,
            }
        ],
        "high_volume_eligibility": {"ledger": False},
        "notification_types": ["ACCRUE_INTEREST_NOTIFICATION"],
        "parameter_id_by_instance_parameter_name": {
            "interest_rate": "INTEREST_RATE",
            "term_length": "TERM_LENGTH",
        },
        "adjustments_versioning_policy": "ADJUSTMENTS_VERSIONING_POLICY_LATEST",
        "adjustments_patch_version_id": "fixed_term_deposit_v0_1_0_patch",
        "supported_denominations": ["GBP", "USD"],
        "tside": "TSIDE_LIABILITY",
        "create_timestamp": "2024-03-20T10:00:00+00:00",
    }

    resource = core_api.ProductVersion(
        id="fixed_term_deposit_v1_0_0",
        product_id="fixed_term_deposit",
        display_name="Fixed Term Deposit Product v1.0.0",
        display_version_number=core_api.SemanticVersion(
            major=1, minor=0, patch=0, label="Release Candidate"
        ),
        description="A product for a fixed term deposit account.",
        summary="High-level summary of the product version.",
        tags=["savings", "term_deposit"],
        core_tags=[
            core_api.ProductVersionCoreTag.FIXED_TERM_DEPOSIT,
            core_api.ProductVersionCoreTag.DEPOSIT,
        ],
        is_current=True,
        code="print('Fixed Term Deposit Contract Code')",
        params=[
            core_api.ProductVersionParameter(
                name="interest_rate",
                display_name="Annual Interest Rate",
                description="The interest rate applied to the deposit.",
                value="0.035",
                default_value="0.03",
                effective_timestamp=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
                level=core_api.ProductVersionParameterLevel.PRODUCT,
                update_permission=core_api.ProductVersionParameterUpdatePermission.FIXED,
                derived=False,
                is_optional=False,
                number=core_api.ParamNumberField(
                    value_type=core_api.NumberValueType.PERCENTAGE,
                    min_value=Decimal("0.005"),
                    max_value=Decimal("0.10"),
                    step=Decimal("0.0001"),
                ),
                account=None,
                values=None,
                denomination=None,
                date=None,
                str_=None,
            ),
            core_api.ProductVersionParameter(
                name="term_length",
                display_name="Deposit Term (Months)",
                description="The duration of the deposit in months.",
                value="12",
                default_value="6",
                effective_timestamp=datetime(2024, 3, 20, 10, 0, 0, tzinfo=UTC),
                level=core_api.ProductVersionParameterLevel.INSTANCE,
                update_permission=core_api.ProductVersionParameterUpdatePermission.CUSTOMER_EDITABLE,  # noqa: E501
                derived=False,
                is_optional=False,
                number=None,
                account=None,
                denomination=None,
                date=None,
                str_=None,
                values=core_api.ParamValueChoiceField(
                    value_choices=[
                        core_api.ValueChoice(value="6", display_name="6 Months"),
                        core_api.ValueChoice(value="12", display_name="12 Months"),
                        core_api.ValueChoice(value="24", display_name="24 Months"),
                    ]
                ),
            ),
        ],
        address_details=[
            core_api.ProductVersionAddressDetails(
                address_name="DEFAULT",
                description="The default account address for balances.",
                tags=["account_balances"],
            )
        ],
        attributes=[
            core_api.ProductVersionAttribute(
                name="customer_segment",
                data_type=core_api.AttributeType(
                    string_type=core_api.AttributeStringType(),
                ),
            )
        ],
        contracts_language_api_version=core_api.SemanticVersion(
            major=4, minor=1, patch=0, label=""
        ),
        contract_module_details=core_api.ContractModuleDetails(
            alias_to_shared_function_details={
                "key": core_api.SharedFunctionDetails(
                    shared_functions=[
                        core_api.SharedFunction(
                            name="share_func_1",
                            args=[
                                core_api.SharedFunctionArgs(
                                    name="name",
                                    type="string",
                                )
                            ],
                            return_type="string",
                        ),
                    ]
                )
            }
        ),
        expected_parameters=[
            core_api.ExpectedParameter(
                parameter_id="INTEREST_RATE",
                is_optional=False,
                triggers_pre_parameter_change_hook=False,
                triggers_post_parameter_change_hook=True,
            )
        ],
        high_volume_eligibility=core_api.HighVolumeEligibility(ledger=False),
        notification_types=["ACCRUE_INTEREST_NOTIFICATION"],
        parameter_id_by_instance_parameter_name={
            "interest_rate": "INTEREST_RATE",
            "term_length": "TERM_LENGTH",
        },
        adjustments_versioning_policy=core_api.AdjustmentsVersioningPolicy.LATEST,
        adjustments_patch_version_id="fixed_term_deposit_v0_1_0_patch",
        supported_denominations=["GBP", "USD"],
        tside=core_api.Tside.LIABILITY,
        create_timestamp=datetime(2024, 3, 20, 10, 0, 0, tzinfo=UTC),
    )


class TestProductVersionTemplateLevelParameterOneOf(TestCase):
    def test_validate_raises_if_one_of_fails(self):
        with self.assertRaises(OneOfException):
            core_api.ProductVersionParameter.model_validate(
                dict(
                    name="name",
                    values=[dict(value="val", display_name="display")],
                    str={},
                )
            )


class TestAttributeTypeOneOf(TestCase):
    def test_validate_raises_if_one_of_fails(self):
        with self.assertRaises(OneOfException):
            core_api.AttributeType.model_validate(
                dict(
                    decimal_type={},
                    datetime_type={},
                )
            )


class TestProductVersionUpdateProductVersion(
    TestPydanticModels.Base[core_api.ProductVersionUpdateProductVersion]
):
    dictionary = dict(
        id="product-version-id-1",
        adjustments_versioning_policy="ADJUSTMENTS_VERSIONING_POLICY_LATEST",
        adjustments_patch_version_id="patch-version-id-1",
    )
    resource = core_api.ProductVersionUpdateProductVersion(
        id="product-version-id-1",
        adjustments_versioning_policy=core_api.AdjustmentsVersioningPolicy.LATEST,
        adjustments_patch_version_id="patch-version-id-1",
    )


class TestProductVersionUpdateProductVersionMinimal(
    TestPydanticModels.Base[core_api.ProductVersionUpdateProductVersion]
):
    dictionary = dict(
        id="product-version-id-1",
        adjustments_versioning_policy=None,
        adjustments_patch_version_id=None,
    )
    resource = core_api.ProductVersionUpdateProductVersion(
        id="product-version-id-1",
    )


class TestProductVersionUpdate(TestPydanticModels.Base[core_api.ProductVersionUpdate]):
    dictionary = dict(
        product_version=dict(
            id="product-version-id-1",
            adjustments_versioning_policy="ADJUSTMENTS_VERSIONING_POLICY_LATEST",
            adjustments_patch_version_id="patch-version-id-1",
        ),
        update_mask=dict(paths=["adjustments_versioning_policy", "adjustments_patch_version_id"]),
    )
    resource = core_api.ProductVersionUpdate(
        product_version=core_api.ProductVersionUpdateProductVersion(
            id="product-version-id-1",
            adjustments_versioning_policy=core_api.AdjustmentsVersioningPolicy.LATEST,
            adjustments_patch_version_id="patch-version-id-1",
        ),
        update_mask=core_api.UpdateMask(
            paths=["adjustments_versioning_policy", "adjustments_patch_version_id"]
        ),
    )


class TestProductVersionUpdateMinimal(TestPydanticModels.Base[core_api.ProductVersionUpdate]):
    dictionary = dict(
        product_version=dict(
            id="product-version-id-1",
            adjustments_versioning_policy=None,
            adjustments_patch_version_id=None,
        ),
        update_mask=dict(paths=["adjustments_versioning_policy"]),
    )
    resource = core_api.ProductVersionUpdate(
        product_version=core_api.ProductVersionUpdateProductVersion(
            id="product-version-id-1",
        ),
        update_mask=core_api.UpdateMask(paths=["adjustments_versioning_policy"]),
    )


class TestBatchUpdateProductVersionsRequestBody(
    TestPydanticModels.Base[core_api.BatchUpdateProductVersionsRequestBody]
):
    dictionary = dict(
        request_id="request-id-123",
        product_version_updates=[
            dict(
                product_version=dict(
                    id="product-version-id-1",
                    adjustments_versioning_policy="ADJUSTMENTS_VERSIONING_POLICY_LATEST",
                    adjustments_patch_version_id=None,
                ),
                update_mask=dict(paths=["adjustments_versioning_policy"]),
            ),
            dict(
                product_version=dict(
                    id="product-version-id-2",
                    adjustments_versioning_policy=None,
                    adjustments_patch_version_id="patch-version-id-2",
                ),
                update_mask=dict(paths=["adjustments_patch_version_id"]),
            ),
        ],
    )
    resource = core_api.BatchUpdateProductVersionsRequestBody(
        request_id="request-id-123",
        product_version_updates=[
            core_api.ProductVersionUpdate(
                product_version=core_api.ProductVersionUpdateProductVersion(
                    id="product-version-id-1",
                    adjustments_versioning_policy=core_api.AdjustmentsVersioningPolicy.LATEST,
                ),
                update_mask=core_api.UpdateMask(paths=["adjustments_versioning_policy"]),
            ),
            core_api.ProductVersionUpdate(
                product_version=core_api.ProductVersionUpdateProductVersion(
                    id="product-version-id-2",
                    adjustments_patch_version_id="patch-version-id-2",
                ),
                update_mask=core_api.UpdateMask(paths=["adjustments_patch_version_id"]),
            ),
        ],
    )


class TestProductVersionUpdateValidation(TestCase):
    def test_validate_raises_if_invalid_update_mask_field(self):
        with self.assertRaises(ValueError) as context:
            core_api.ProductVersionUpdate(
                product_version=core_api.ProductVersionUpdateProductVersion(
                    id="product-version-id-1",
                ),
                update_mask=core_api.UpdateMask(paths=["is_current"]),
            )
            self.assertEqual(
                "Invalid fields in update_mask: is_current."
                "Only the following fields can be updated: "
                "['adjustments_patch_version_id', 'adjustments_versioning_policy']",
                str(context.exception),
            )

    def test_validate_raises_if_multiple_invalid_update_mask_fields(self):
        with self.assertRaises(ValueError) as context:
            core_api.ProductVersionUpdate(
                product_version=core_api.ProductVersionUpdateProductVersion(
                    id="product-version-id-1",
                ),
                update_mask=core_api.UpdateMask(
                    paths=[
                        "is_current",
                        "tags",
                        "code",
                        "adjustments_patch_version_id",
                        "adjustments_versioning_policy",
                    ]
                ),
            )
            self.assertEqual(
                "Invalid fields in update_mask: {'tags', 'code', 'is_current'}."
                "Only the following fields can be updated: "
                "['adjustments_patch_version_id', 'adjustments_versioning_policy']",
                str(context.exception),
            )

    def test_validate_does_not_raise_with_valid_update_mask_fields(self):
        update = core_api.ProductVersionUpdate(
            product_version=core_api.ProductVersionUpdateProductVersion(
                id="product-version-id-1",
            ),
            update_mask=core_api.UpdateMask(
                paths=["adjustments_versioning_policy", "adjustments_patch_version_id"]
            ),
        )
        self.assertEqual(
            update.update_mask.paths,
            ["adjustments_versioning_policy", "adjustments_patch_version_id"],
        )


class TestListProductVersionsRequestBody(
    TestPydanticModels.Base[core_api.ListProductVersionsRequestBody]
):
    dictionary = {
        "product_id": "product1",
        "view": "PRODUCT_VERSION_VIEW_BASIC",
        "page_size": 2,
        "page_token": None,
    }

    resource = core_api.ListProductVersionsRequestBody(
        product_id="product1",
        view=core_api.ProductVersionView.BASIC,
        page_size=2,
        page_token=None,
    )


class TestListProductVersionsResponse(
    TestPydanticModels.Base[core_api.ListProductVersionsResponse]
):
    dictionary = {
        "product_versions": [
            {
                "id": "fixed_term_deposit_v1_0_0",
                "product_id": "fixed_term_deposit",
                "display_name": "Fixed Term Deposit Product v1.0.0",
                "display_version_number": {
                    "major": 1,
                    "minor": 0,
                    "patch": 0,
                    "label": "Release Candidate",
                },
                "description": "A product for a fixed term deposit account.",
                "summary": "High-level summary of the product version.",
                "tags": ["savings", "term_deposit"],
                "core_tags": [
                    "PRODUCT_VERSION_CORE_TAG_FIXED_TERM_DEPOSIT",
                    "PRODUCT_VERSION_CORE_TAG_DEPOSIT",
                ],
                "is_current": True,
                "code": "print('Fixed Term Deposit Contract Code')",
                "params": [
                    {
                        "name": "interest_rate",
                        "display_name": "Annual Interest Rate",
                        "description": "The interest rate applied to the deposit.",
                        "value": "0.035",
                        "default_value": "0.03",
                        "effective_timestamp": "2025-01-01T00:00:00+00:00",
                        "level": "LEVEL_PRODUCT",
                        "update_permission": "UPDATE_PERMISSION_FIXED",
                        "derived": False,
                        "is_optional": False,
                        "denomination": None,
                        "account": None,
                        "date": None,
                        "str": None,
                        "values": None,
                        "number": {
                            "value_type": "NUMBER_FIELD_DISPLAY_STYLE_PERCENTAGE",
                            "min_value": "0.005",
                            "max_value": "0.10",
                            "step": "0.0001",
                        },
                    },
                ],
                "address_details": [
                    {
                        "address_name": "DEFAULT",
                        "description": "The default account address for balances.",
                        "tags": ["account_balances"],
                    }
                ],
                "attributes": [
                    {
                        "name": "customer_segment",
                        "data_type": {
                            "string_type": {},
                            "decimal_type": None,
                            "datetime_type": None,
                        },
                    }
                ],
                "contracts_language_api_version": {"major": 4, "minor": 1, "patch": 0, "label": ""},
                "contract_module_details": {
                    "alias_to_shared_function_details": {
                        "key": {
                            "shared_functions": [
                                {
                                    "name": "share_func_1",
                                    "args": [
                                        {
                                            "name": "name",
                                            "type": "string",
                                        }
                                    ],
                                    "return_type": "string",
                                }
                            ],
                        }
                    }
                },
                "expected_parameters": [
                    {
                        "parameter_id": "INTEREST_RATE",
                        "is_optional": False,
                        "triggers_pre_parameter_change_hook": False,
                        "triggers_post_parameter_change_hook": True,
                    }
                ],
                "high_volume_eligibility": {"ledger": False},
                "notification_types": ["ACCRUE_INTEREST_NOTIFICATION"],
                "parameter_id_by_instance_parameter_name": {
                    "interest_rate": "INTEREST_RATE",
                    "term_length": "TERM_LENGTH",
                },
                "adjustments_versioning_policy": "ADJUSTMENTS_VERSIONING_POLICY_LATEST",
                "adjustments_patch_version_id": "fixed_term_deposit_v0_1_0_patch",
                "supported_denominations": ["GBP", "USD"],
                "tside": "TSIDE_LIABILITY",
                "create_timestamp": "2024-03-20T10:00:00+00:00",
            }
        ],
        "previous_page_token": "prev-token",
        "next_page_token": "next-token",
    }

    resource = core_api.ListProductVersionsResponse(
        product_versions=[
            core_api.ProductVersion(
                id="fixed_term_deposit_v1_0_0",
                product_id="fixed_term_deposit",
                display_name="Fixed Term Deposit Product v1.0.0",
                display_version_number=core_api.SemanticVersion(
                    major=1, minor=0, patch=0, label="Release Candidate"
                ),
                description="A product for a fixed term deposit account.",
                summary="High-level summary of the product version.",
                tags=["savings", "term_deposit"],
                core_tags=[
                    core_api.ProductVersionCoreTag.FIXED_TERM_DEPOSIT,
                    core_api.ProductVersionCoreTag.DEPOSIT,
                ],
                is_current=True,
                code="print('Fixed Term Deposit Contract Code')",
                params=[
                    core_api.ProductVersionParameter(
                        name="interest_rate",
                        display_name="Annual Interest Rate",
                        description="The interest rate applied to the deposit.",
                        value="0.035",
                        default_value="0.03",
                        effective_timestamp=datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC),
                        level=core_api.ProductVersionParameterLevel.PRODUCT,
                        update_permission=core_api.ProductVersionParameterUpdatePermission.FIXED,
                        derived=False,
                        is_optional=False,
                        number=core_api.ParamNumberField(
                            value_type=core_api.NumberValueType.PERCENTAGE,
                            min_value=Decimal("0.005"),
                            max_value=Decimal("0.10"),
                            step=Decimal("0.0001"),
                        ),
                        account=None,
                        values=None,
                        denomination=None,
                        date=None,
                        str_=None,
                    ),
                ],
                address_details=[
                    core_api.ProductVersionAddressDetails(
                        address_name="DEFAULT",
                        description="The default account address for balances.",
                        tags=["account_balances"],
                    )
                ],
                attributes=[
                    core_api.ProductVersionAttribute(
                        name="customer_segment",
                        data_type=core_api.AttributeType(
                            string_type=core_api.AttributeStringType(),
                        ),
                    )
                ],
                contracts_language_api_version=core_api.SemanticVersion(
                    major=4, minor=1, patch=0, label=""
                ),
                contract_module_details=core_api.ContractModuleDetails(
                    alias_to_shared_function_details={
                        "key": core_api.SharedFunctionDetails(
                            shared_functions=[
                                core_api.SharedFunction(
                                    name="share_func_1",
                                    args=[
                                        core_api.SharedFunctionArgs(
                                            name="name",
                                            type="string",
                                        )
                                    ],
                                    return_type="string",
                                ),
                            ]
                        )
                    }
                ),
                expected_parameters=[
                    core_api.ExpectedParameter(
                        parameter_id="INTEREST_RATE",
                        is_optional=False,
                        triggers_pre_parameter_change_hook=False,
                        triggers_post_parameter_change_hook=True,
                    )
                ],
                high_volume_eligibility=core_api.HighVolumeEligibility(ledger=False),
                notification_types=["ACCRUE_INTEREST_NOTIFICATION"],
                parameter_id_by_instance_parameter_name={
                    "interest_rate": "INTEREST_RATE",
                    "term_length": "TERM_LENGTH",
                },
                adjustments_versioning_policy=core_api.AdjustmentsVersioningPolicy.LATEST,
                adjustments_patch_version_id="fixed_term_deposit_v0_1_0_patch",
                supported_denominations=["GBP", "USD"],
                tside=core_api.Tside.LIABILITY,
                create_timestamp=datetime(2024, 3, 20, 10, 0, 0, tzinfo=UTC),
            )
        ],
        previous_page_token="prev-token",
        next_page_token="next-token",
    )


class TestCreateProductVersionRequestProductVersion(
    TestPydanticModels.Base[core_api.CreateProductVersionRequestProductVersion]
):
    dictionary = {
        "product_id": "fixed_term_deposit",
        "display_name": "Fixed Term Deposit Product Draft",
        "description": "A draft version for a fixed term deposit account.",
        "summary": "Initial draft for a new fixed term product.",
        "tags": ["savings", "term_deposit", "draft"],
        "core_tags": ["PRODUCT_VERSION_CORE_TAG_FIXED_TERM_DEPOSIT"],
        "code": "code1",
        "params": [
            {
                "name": "interest_rate",
                "value": "0.5",
            },
        ],
        "high_volume_eligibility": {"ledger": False},
        "supported_denominations": ["GBP", "EUR"],
        "adjustments_versioning_policy": "ADJUSTMENTS_VERSIONING_POLICY_LATEST",
    }

    resource = core_api.CreateProductVersionRequestProductVersion(
        product_id="fixed_term_deposit",
        display_name="Fixed Term Deposit Product Draft",
        description="A draft version for a fixed term deposit account.",
        summary="Initial draft for a new fixed term product.",
        tags=["savings", "term_deposit", "draft"],
        core_tags=[core_api.ProductVersionCoreTag.FIXED_TERM_DEPOSIT],
        code="code1",
        params=[
            core_api.CreateProductVersionParameter(
                name="interest_rate",
                value="0.5",
            ),
        ],
        high_volume_eligibility=core_api.HighVolumeEligibility(ledger=False),
        supported_denominations=["GBP", "EUR"],
        adjustments_versioning_policy=core_api.AdjustmentsVersioningPolicy.LATEST,
    )


class TestCreateProductVersionBodyWithSupportedDenomination(
    TestPydanticModels.Base[core_api.CreateProductVersionRequestBody]
):
    dictionary = {
        "request_id": "request1",
        "product_version": {
            "product_id": "fixed_term_deposit",
            "display_name": "Fixed Term Deposit Product Draft",
            "description": "A draft version for a fixed term deposit account.",
            "summary": "Initial draft for a new fixed term product.",
            "tags": ["savings", "term_deposit", "draft"],
            "core_tags": ["PRODUCT_VERSION_CORE_TAG_FIXED_TERM_DEPOSIT"],
            "code": "code1",
            "params": [
                {
                    "name": "interest_rate",
                    "value": "0.5",
                },
            ],
            "high_volume_eligibility": {"ledger": False},
            "supported_denominations": ["GBP", "EUR"],
            "adjustments_versioning_policy": None,
        },
        "migration_strategy": "PRODUCT_VERSION_MIGRATION_STRATEGY_NEW_PRODUCT",
        "is_internal": True,
    }

    resource = core_api.CreateProductVersionRequestBody(
        request_id="request1",
        product_version=core_api.CreateProductVersionRequestProductVersion(
            product_id="fixed_term_deposit",
            display_name="Fixed Term Deposit Product Draft",
            description="A draft version for a fixed term deposit account.",
            summary="Initial draft for a new fixed term product.",
            tags=["savings", "term_deposit", "draft"],
            core_tags=[core_api.ProductVersionCoreTag.FIXED_TERM_DEPOSIT],
            code="code1",
            params=[
                core_api.CreateProductVersionParameter(
                    name="interest_rate",
                    value="0.5",
                ),
            ],
            high_volume_eligibility=core_api.HighVolumeEligibility(ledger=False),
            supported_denominations=["GBP", "EUR"],
            adjustments_versioning_policy=None,
        ),
        migration_strategy=core_api.ProductVersionMigrationStrategy.NEW_PRODUCT,
        is_internal=True,
    )


class TestCreateProductVersionBodyWithMissingSupportedDenominationsRaises(TestCase):
    def test_raises_value_error_with_non_internal_products(self):
        with self.assertRaises(ValueError):
            core_api.CreateProductVersionRequestBody(
                request_id="request1",
                product_version=core_api.CreateProductVersionRequestProductVersion(
                    product_id="product_1",
                    display_name="display_name",
                    description=None,
                    summary=None,
                    tags=None,
                    core_tags=None,
                    code="code",
                    params=None,
                    high_volume_eligibility=None,
                    supported_denominations=None,
                    adjustments_versioning_policy=None,
                ),
                migration_strategy=core_api.ProductVersionMigrationStrategy.NEW_PRODUCT,
                is_internal=False,
            )


class TestBatchGetProductVersionsRequest(
    TestPydanticModels.Base[core_api.BatchGetProductVersionsRequest]
):
    dictionary = dict(
        ids=["product-version-id-1", "product-version-id-2"],
        view="PRODUCT_VERSION_VIEW_INCLUDE_PARAMETERS",
    )
    resource = core_api.BatchGetProductVersionsRequest(
        ids=["product-version-id-1", "product-version-id-2"],
        view=core_api.ProductVersionView.INCLUDE_PARAMETERS,
    )


class TestBatchGetProductVersionsRequestMinimal(
    TestPydanticModels.Base[core_api.BatchGetProductVersionsRequest]
):
    dictionary = dict(
        ids=["product-version-id-1"],
        view=None,
    )
    resource = core_api.BatchGetProductVersionsRequest(
        ids=["product-version-id-1"],
    )


class TestBatchGetProductVersionsResponse(
    TestPydanticModels.Base[core_api.BatchGetProductVersionsResponse]
):
    dictionary = dict(
        product_versions={
            "product-version-id-1": TestProductVersion.dictionary,
        },
    )
    resource = core_api.BatchGetProductVersionsResponse(
        product_versions={
            "product-version-id-1": TestProductVersion.resource,
        },
    )


class TestUpdateProductVersionParamsRequestBody(
    TestPydanticModels.Base[core_api.UpdateProductVersionParamsRequestBody]
):
    dictionary = {
        "product_version_id": "product-1",
        "request_id": "req-1",
        "items_to_add": [
            {
                "name": "param1",
                "value": "new-value",
                "effective_timestamp": "2020-01-01T00:00:00+00:00",
            },
        ],
        "items_to_remove": [
            {
                "name": "param1",
                "value": None,
                "effective_timestamp": "2020-01-01T00:00:00+00:00",
            },
        ],
    }

    resource = core_api.UpdateProductVersionParamsRequestBody(
        product_version_id="product-1",
        request_id="req-1",
        items_to_add=[
            core_api.UpdateProductVersionParams(
                name="param1",
                value="new-value",
                effective_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
            )
        ],
        items_to_remove=[
            core_api.UpdateProductVersionParams(
                name="param1",
                value=None,
                effective_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
            )
        ],
    )


class TestUpdateProductVersionParamsRequestBodyOnAdd(
    TestPydanticModels.Base[core_api.UpdateProductVersionParamsRequestBody]
):
    dictionary = {
        "product_version_id": "product-1",
        "request_id": "req-1",
        "items_to_add": [
            {
                "name": "param1",
                "value": "new-value",
                "effective_timestamp": "2020-01-01T00:00:00+00:00",
            },
        ],
        "items_to_remove": [],
    }

    resource = core_api.UpdateProductVersionParamsRequestBody(
        product_version_id="product-1",
        request_id="req-1",
        items_to_add=[
            core_api.UpdateProductVersionParams(
                name="param1",
                value="new-value",
                effective_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
            )
        ],
        items_to_remove=[],
    )


class TestUpdateProductVersionParamsRequestBodyOnRemove(
    TestPydanticModels.Base[core_api.UpdateProductVersionParamsRequestBody]
):
    dictionary = {
        "product_version_id": "product-1",
        "request_id": "req-1",
        "items_to_add": [],
        "items_to_remove": [
            {
                "name": "param1",
                "value": None,
                "effective_timestamp": "2020-01-01T00:00:00+00:00",
            },
        ],
    }

    resource = core_api.UpdateProductVersionParamsRequestBody(
        product_version_id="product-1",
        request_id="req-1",
        items_to_add=[],
        items_to_remove=[
            core_api.UpdateProductVersionParams(
                name="param1",
                value=None,
                effective_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
            )
        ],
    )


class TestSemanticVersionString(TestCase):
    def test_semantic_version_string_property(self):
        sem_ver = core_api.SemanticVersion(major=1, minor=2, patch=3, label="-beta1")
        self.assertEqual(sem_ver.version_string, "1.2.3-beta1")


class TestUpdateProductVersionParams(TestPydanticModels.Base[core_api.UpdateProductVersionParams]):
    dictionary = {
        "name": "p1",
        "value": "v1",
        "effective_timestamp": "2020-01-01T00:00:00+00:00",
    }

    resource = core_api.UpdateProductVersionParams(
        name="p1",
        value="v1",
        effective_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
    )


class TestUpdateProductVersionParamsRaises(TestCase):
    def test_items_to_add_with_missing_value_raises(self):
        with self.assertRaises(ValueError):
            core_api.UpdateProductVersionParamsRequestBody.model_validate(
                dict(
                    product_version_id="123",
                    request_id="123",
                    items_to_add=[
                        dict(name="foo", effective_timestamp=datetime(2020, 1, 1, tzinfo=UTC))
                    ],
                )
            )

    def test_items_to_remove_with_value_raises(self):
        with self.assertRaises(ValueError):
            core_api.UpdateProductVersionParamsRequestBody.model_validate(
                dict(
                    product_version_id="123",
                    request_id="123",
                    items_to_remove=[
                        dict(
                            name="foo",
                            value="bar",
                            effective_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
                        )
                    ],
                )
            )


class TestProductVersionParamTimeseriesValue(
    TestPydanticModels.Base[core_api.ProductVersionParamTimeseriesValue]
):
    dictionary = {
        "value": "1",
        "effective_from_timestamp": "2020-01-01T00:00:00+00:00",
    }

    resource = core_api.ProductVersionParamTimeseriesValue(
        value="1",
        effective_from_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
    )


class TestProductVersionParamTimeseries(
    TestPydanticModels.Base[core_api.ProductVersionParamTimeseries]
):
    dictionary = {
        "param_name": "foo",
        "values": [{"value": "1", "effective_from_timestamp": "2020-01-01T00:00:00+00:00"}],
    }

    resource = core_api.ProductVersionParamTimeseries(
        param_name="foo",
        values=[
            core_api.ProductVersionParamTimeseriesValue(
                value="1",
                effective_from_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
            )
        ],
    )


class TestProductVersionParamTimeseriesResponse(
    TestPydanticModels.Base[core_api.ProductVersionParamTimeseriesResponse]
):
    dictionary = {
        "product_version_param_timeseries": [
            {
                "param_name": "foo",
                "values": [{"value": "1", "effective_from_timestamp": "2020-01-01T00:00:00+00:00"}],
            }
        ]
    }

    resource = core_api.ProductVersionParamTimeseriesResponse(
        product_version_param_timeseries=[
            core_api.ProductVersionParamTimeseries(
                param_name="foo",
                values=[
                    core_api.ProductVersionParamTimeseriesValue(
                        value="1",
                        effective_from_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
                    )
                ],
            )
        ]
    )


class TestBalancesV2(TestPydanticModels.Base[core_api.BalanceV2]):
    dictionary = {
        "amount": "1",
        "total_credit": "1",
        "total_debit": "0",
        "account_id": "account_id",
        "account_address": "DEFAULT",
        "asset": "COMMERCIAL_BANK_MONEY",
        "denomination": "XYZ",
        "phase": "POSTING_PHASE_COMMITTED",
        "timestamp": "2020-01-01T00:00:00+00:00",
        "sub_account_id": "sub_account_id",
    }

    resource = core_api.BalanceV2(
        amount=Decimal("1"),
        total_credit=Decimal("1"),
        total_debit=Decimal("0"),
        account_id="account_id",
        account_address="DEFAULT",
        phase=core_api.PostingPhase.COMMITTED,
        asset="COMMERCIAL_BANK_MONEY",
        denomination="XYZ",
        timestamp=datetime(2020, 1, 1, tzinfo=UTC),
        sub_account_id="sub_account_id",
    )


class TestLiveBalancesV2(TestPydanticModels.Base[core_api.LiveBalanceV2]):
    dictionary = {
        "amount": "1",
        "total_credit": "1",
        "total_debit": "0",
        "account_id": "account_id",
        "account_address": "DEFAULT",
        "asset": "COMMERCIAL_BANK_MONEY",
        "denomination": "XYZ",
        "phase": "POSTING_PHASE_COMMITTED",
        "sub_account_id": "sub_account_id",
    }

    resource = core_api.LiveBalanceV2(
        amount=Decimal("1"),
        total_credit=Decimal("1"),
        total_debit=Decimal("0"),
        account_id="account_id",
        account_address="DEFAULT",
        phase=core_api.PostingPhase.COMMITTED,
        asset="COMMERCIAL_BANK_MONEY",
        denomination="XYZ",
        sub_account_id="sub_account_id",
    )


class TestEndBalancesV2(TestPydanticModels.Base[core_api.EndBalanceV2]):
    dictionary = {
        "amount": "1",
        "total_credit": "1",
        "total_debit": "0",
        "account_id": "account_id",
        "account_address": "DEFAULT",
        "asset": "COMMERCIAL_BANK_MONEY",
        "denomination": "XYZ",
        "phase": "POSTING_PHASE_COMMITTED",
        "timestamp": None,
        "sub_account_id": "sub_account_id",
    }

    resource = core_api.EndBalanceV2(
        amount=Decimal("1"),
        total_credit=Decimal("1"),
        total_debit=Decimal("0"),
        account_id="account_id",
        account_address="DEFAULT",
        phase=core_api.PostingPhase.COMMITTED,
        asset="COMMERCIAL_BANK_MONEY",
        denomination="XYZ",
        timestamp=None,
        sub_account_id="sub_account_id",
    )


class TestListAccountAttributeValuesRequest(
    TestPydanticModels.Base[core_api.ListAccountAttributeValuesRequest]
):
    dictionary = {
        "account_ids": ["account_1"],
        "attribute_names": ["attribute_1"],
        "effective_timestamps": ["2025-01-01T00:00:00+00:00"],
        "page_size": 100,
        "page_token": "foo",
    }

    resource = core_api.ListAccountAttributeValuesRequest(
        account_ids=["account_1"],
        attribute_names=["attribute_1"],
        effective_timestamps=[datetime(2025, 1, 1, tzinfo=UTC)],
        page_size=100,
        page_token="foo",
    )


class TestListAccountAttributeValuesResponse(
    TestPydanticModels.Base[core_api.ListAccountAttributeValuesResponse]
):
    dictionary = {
        "account_attribute_values": [
            {
                "account_id": "account_1",
                "attribute_name": "attribute_1",
                "effective_timestamp": "2020-01-01T00:00:00+00:00",
                "value": {
                    "string_value": {"value": "string_value"},
                    "date_time_value": None,
                    "decimal_value": None,
                },
            }
        ],
        "previous_page_token": "foo",
        "next_page_token": "bar",
    }

    resource = core_api.ListAccountAttributeValuesResponse(
        account_attribute_values=[
            core_api.AccountAttributeValue(
                account_id="account_1",
                attribute_name="attribute_1",
                effective_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
                value=core_api.AttributeValue(
                    string_value=core_api.AttributeStringValue(value="string_value")
                ),
            )
        ],
        previous_page_token="foo",
        next_page_token="bar",
    )


class AccountAttributeValue(TestPydanticModels.Base[core_api.AccountAttributeValue]):
    dictionary = {
        "account_id": "account_1",
        "attribute_name": "attribute_1",
        "effective_timestamp": "2020-01-01T00:00:00+00:00",
        "value": {
            "string_value": {"value": "string_value"},
            "date_time_value": None,
            "decimal_value": None,
        },
    }

    resource = core_api.AccountAttributeValue(
        account_id="account_1",
        attribute_name="attribute_1",
        effective_timestamp=datetime(2020, 1, 1, tzinfo=UTC),
        value=core_api.AttributeValue(
            string_value=core_api.AttributeStringValue(value="string_value")
        ),
    )


class AttributeValueStringType(TestPydanticModels.Base[core_api.AttributeValue]):
    dictionary = {
        "string_value": {"value": "string_value"},
        "date_time_value": None,
        "decimal_value": None,
    }

    resource = core_api.AttributeValue(
        string_value=core_api.AttributeStringValue(value="string_value")
    )


class AttributeValueDecimalType(TestPydanticModels.Base[core_api.AttributeValue]):
    dictionary = {
        "decimal_value": {"value": "1.234"},
        "string_value": None,
        "date_time_value": None,
    }

    resource = core_api.AttributeValue(
        decimal_value=core_api.AttributeDecimalValue(value=Decimal("1.234"))
    )


class AttributeValueDatetimeType(TestPydanticModels.Base[core_api.AttributeValue]):
    dictionary = {
        "date_time_value": {"value": "2020-01-01T00:00:00+00:00"},
        "string_value": None,
        "decimal_value": None,
    }

    resource = core_api.AttributeValue(
        date_time_value=core_api.AttributeDateTimeValue(value=datetime(2020, 1, 1, tzinfo=UTC))
    )


class TestAttributeValueOneof(TestCase):
    def test_validate_raises_if_one_of_fails(self):
        with self.assertRaises(OneOfException):
            core_api.AttributeValue.model_validate(
                dict(
                    string_type={},
                    decimal_type={},
                    datetime_type={},
                )
            )


class AttributeStringValue(TestPydanticModels.Base[core_api.AttributeStringValue]):
    dictionary = {"value": "string_value"}

    resource = core_api.AttributeStringValue(value="string_value")


class AttributeDecimalValue(TestPydanticModels.Base[core_api.AttributeDecimalValue]):
    dictionary = {"value": "1.234"}

    resource = core_api.AttributeDecimalValue(value=Decimal("1.234"))


class AttributeDatetimeValue(TestPydanticModels.Base[core_api.AttributeDateTimeValue]):
    dictionary = {"value": "2020-01-01T00:00:00+00:00"}

    resource = core_api.AttributeDateTimeValue(value=datetime(2020, 1, 1, tzinfo=UTC))


class TestGetVaultVersionResponse(TestPydanticModels.Base[core_api.GetVaultVersionResponse]):
    dictionary = {
        "version": {"major": 6, "minor": 3, "patch": 1, "label": "-rc3"},
        "pre_release": "pre_release_tag",
        "build": "build_tag",
        "extensions": [
            "VAULT_CORE_EXTENSION_MULTIPLE_PROCESSING_GROUPS",
            "VAULT_CORE_EXTENSION_HIGH_VOLUME_ACCOUNTS",
            "VAULT_CORE_EXTENSION_ATTRIBUTE_BASED_ACCESS_CONTROL",
            "VAULT_CORE_EXTENSION_SUB_ACCOUNTS",
        ],
    }

    resource = core_api.GetVaultVersionResponse(
        version=core_api.SemanticVersion(major=6, minor=3, patch=1, label="-rc3"),
        pre_release="pre_release_tag",
        build="build_tag",
        extensions=[
            core_api.VaultCoreExtension.MULTIPLE_PROCESSING_GROUPS,
            core_api.VaultCoreExtension.HIGH_VOLUME_ACCOUNTS,
            core_api.VaultCoreExtension.ATTRIBUTE_BASED_ACCESS_CONTROL,
            core_api.VaultCoreExtension.SUB_ACCOUNTS,
        ],
    )


class TestSubAccountRequest(TestPydanticModels.Base[core_api.SubAccount]):
    dictionary = {
        "id": "sub-account-id",
        "type": "sub-account-type",
        "name": "sub-account-name",
        "details": {"sub-account-details": "some-details"},
        "activation_timestamp": "2020-01-06T00:00:00+00:00",
        "create_timestamp": "2020-01-06T00:00:00+00:00",
        "update_timestamp": "2020-01-07T00:00:00+00:00",
        "status": "SUB_ACCOUNT_STATUS_OPEN",
        "account_id": "account-id",
    }

    resource = core_api.SubAccount(
        id="sub-account-id",
        type="sub-account-type",
        name="sub-account-name",
        details={"sub-account-details": "some-details"},
        activation_timestamp=datetime(2020, 1, 6, tzinfo=UTC),
        create_timestamp=datetime(2020, 1, 6, tzinfo=UTC),
        update_timestamp=datetime(2020, 1, 7, tzinfo=UTC),
        status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
        account_id="account-id",
    )


class TestListSubAccountsRequest(TestPydanticModels.Base[core_api.ListSubAccountsRequest]):
    dictionary = {
        "account_id": "account-id",
        "status": "SUB_ACCOUNT_STATUS_OPEN",
        "type": "sub-account-type",
        "page_size": 100,
        "page_token": "some-page-token",
    }

    resource = core_api.ListSubAccountsRequest(
        account_id="account-id",
        status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
        type="sub-account-type",
        page_size=100,
        page_token="some-page-token",
    )


class TestListSubAccountsResponse(TestPydanticModels.Base[core_api.ListSubAccountsResponse]):
    dictionary = {
        "sub_accounts": [
            dict(
                id="sub-account-id",
                type="sub-account-type",
                name="sub-account-name",
                details={"sub-account-details": "some-details"},
                activation_timestamp="2020-01-06T00:00:00+00:00",
                create_timestamp="2020-01-06T00:00:00+00:00",
                update_timestamp="2020-01-07T00:00:00+00:00",
                status="SUB_ACCOUNT_STATUS_OPEN",
                account_id="account-id",
            )
        ],
        "previous_page_token": "prev-page-token",
        "next_page_token": "next-page-token",
    }

    resource = core_api.ListSubAccountsResponse(
        sub_accounts=[
            core_api.SubAccount(
                id="sub-account-id",
                type="sub-account-type",
                name="sub-account-name",
                details={"sub-account-details": "some-details"},
                activation_timestamp=datetime(2020, 1, 6, tzinfo=UTC),
                create_timestamp=datetime(2020, 1, 6, tzinfo=UTC),
                update_timestamp=datetime(2020, 1, 7, tzinfo=UTC),
                status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                account_id="account-id",
            )
        ],
        previous_page_token="prev-page-token",
        next_page_token="next-page-token",
    )


class TestSubAccountCreateSubAccount(TestPydanticModels.Base[core_api.SubAccountCreateSubAccount]):
    dictionary = {
        "id": "sub-account-id",
        "type": "sub-account-type",
        "name": "sub-account-name",
        "details": {"sub-account-details": "some-details"},
        "status": "SUB_ACCOUNT_STATUS_OPEN",
        "account_id": "account-id",
    }

    resource = core_api.SubAccountCreateSubAccount(
        id="sub-account-id",
        type="sub-account-type",
        name="sub-account-name",
        details={"sub-account-details": "some-details"},
        status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
        account_id="account-id",
    )


class TestCreateSubAccountRequest(TestPydanticModels.Base[core_api.CreateSubAccountRequest]):
    dictionary = {
        "request_id": "request-id",
        "sub_account": dict(
            id="sub-account-id",
            type="sub-account-type",
            name="sub-account-name",
            details={"sub-account-details": "some-details"},
            status="SUB_ACCOUNT_STATUS_OPEN",
            account_id="account-id",
        ),
    }

    resource = core_api.CreateSubAccountRequest(
        request_id="request-id",
        sub_account=core_api.SubAccountCreateSubAccount(
            id="sub-account-id",
            type="sub-account-type",
            name="sub-account-name",
            details={"sub-account-details": "some-details"},
            status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
            account_id="account-id",
        ),
    )


class TestSubAccountUpdateSubAccount(TestPydanticModels.Base[core_api.SubAccountUpdateSubAccount]):
    dictionary = {
        "name": "updated-sub-account-name",
        "details": {"sub-account-details": "updated-details"},
        "status": "SUB_ACCOUNT_STATUS_CANCELLED",
    }

    resource = core_api.SubAccountUpdateSubAccount(
        name="updated-sub-account-name",
        details={"sub-account-details": "updated-details"},
        status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_CANCELLED,
    )


class TestUpdateSubAccountRequest(TestPydanticModels.Base[core_api.UpdateSubAccountRequest]):
    dictionary = {
        "sub_account_id": "sub-account-id",
        "request_id": "request-id",
        "sub_account": {
            "name": None,
            "details": None,
            "status": "SUB_ACCOUNT_STATUS_CANCELLED",
        },
        "update_mask": dict(paths=["status"]),
    }

    resource = core_api.UpdateSubAccountRequest(
        sub_account_id="sub-account-id",
        request_id="request-id",
        sub_account=core_api.SubAccountUpdateSubAccount(
            name=None,
            details=None,
            status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_CANCELLED,
        ),
        update_mask=core_api.UpdateMask(paths=["status"]),
    )


class TestUpdateSubAccountRequestValidation(TestCase):
    def test_invalid_update_mask_fields_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            core_api.UpdateSubAccountRequest(
                sub_account_id="sub-account-id",
                request_id="request-id",
                sub_account=core_api.SubAccountUpdateSubAccount(
                    name=None,
                    details=None,
                    status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_CANCELLED,
                ),
                update_mask=core_api.UpdateMask(paths=["details", "unknown_field"]),
            )
        self.assertIn("Invalid fields in update_mask: ['unknown_field']", str(ctx.exception))

    def test_updating_status_with_other_fields_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            core_api.UpdateSubAccountRequest(
                sub_account_id="sub-account-id",
                request_id="request-id",
                sub_account=core_api.SubAccountUpdateSubAccount(
                    name=None,
                    details=None,
                    status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_CANCELLED,
                ),
                update_mask=core_api.UpdateMask(paths=["details", "status"]),
            )
        self.assertIn("Invalid fields in update_mask: ['details']", str(ctx.exception))
        self.assertIn("status must be updated in isolation", str(ctx.exception))


class TestBatchGetSubAccountsRequest(TestPydanticModels.Base[core_api.BatchGetSubAccountsRequest]):
    dictionary = {
        "ids": ["sub-account-id-1", "sub-account-id-2"],
    }

    resource = core_api.BatchGetSubAccountsRequest(
        ids=["sub-account-id-1", "sub-account-id-2"],
    )


class TestBatchGetSubAccountsRequestValidation(TestCase):
    def test_validate_ids_list_with_101_ids_raises_value_error(self):
        ids = [f"id-{i}" for i in range(101)]
        with self.assertRaises(ValueError) as ctx:
            core_api.BatchGetSubAccountsRequest(ids=ids)
        self.assertIn("Invalid number of IDs: 101", str(ctx.exception))
        self.assertIn("Maximum number of allowable IDs: 100", str(ctx.exception))


class TestBatchGetSubAccountsResponse(
    TestPydanticModels.Base[core_api.BatchGetSubAccountsResponse]
):
    dictionary = {
        "sub_accounts": {
            "sub-account-id-1": {
                "id": "sub-account-id-1",
                "type": "sub-account-type",
                "name": "sub-account-name",
                "details": {"sub-account-details": "some-details"},
                "activation_timestamp": "2020-01-06T00:00:00+00:00",
                "create_timestamp": "2020-01-06T00:00:00+00:00",
                "update_timestamp": "2020-01-07T00:00:00+00:00",
                "status": "SUB_ACCOUNT_STATUS_OPEN",
                "account_id": "account-id",
            }
        },
    }

    resource = core_api.BatchGetSubAccountsResponse(
        sub_accounts={
            "sub-account-id-1": core_api.SubAccount(
                id="sub-account-id-1",
                type="sub-account-type",
                name="sub-account-name",
                details={"sub-account-details": "some-details"},
                activation_timestamp=datetime(2020, 1, 6, tzinfo=UTC),
                create_timestamp=datetime(2020, 1, 6, tzinfo=UTC),
                update_timestamp=datetime(2020, 1, 7, tzinfo=UTC),
                status=core_api.SubAccountStatus.SUB_ACCOUNT_STATUS_OPEN,
                account_id="account-id",
            )
        }
    )
