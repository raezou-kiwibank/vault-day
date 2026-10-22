from collections import defaultdict, namedtuple
from unittest import TestCase
from copy import deepcopy
from datetime import datetime, timezone
from contextlib import redirect_stderr
from decimal import Decimal
from io import StringIO
from zoneinfo import ZoneInfo

from ..types import (
    AccountIdShape,
    CustomInstruction,
    DateShape,
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    DefinedDateTime,
    DenominationShape,
    EndOfMonthSchedule,
    FlagsObservation,
    Logger,
    Next,
    NumberShape,
    OptionalShape,
    OptionalValue,
    Override,
    Parameter,
    ParameterLevel,
    ParametersObservation,
    Phase,
    PlanNotificationDirective,
    Posting,
    PostingInstructionsDirective,
    Previous,
    Rejection,
    RejectionReason,
    RelativeDateTime,
    ScheduleFailover,
    Shift,
    SmartContractDescriptor,
    StringShape,
    SupervisedHooks,
    SupervisionExecutionMode,
    UnionItem,
    UnionItemValue,
    UnionShape,
    ParameterUpdatePermission,
    
)

from .....utils.exceptions import (
    StrongTypingError,
    InvalidSmartContractError,
)
from .....utils.feature_flags import (
    skip_if_not_enabled,
    SERVICING_GROUPS,
    # <NOT RELEASE END>,
)
from .....utils.types_utils import (
    ContractsLanguageDunderMixin,
)


class TestTypes(TestCase):
    test_account_id = "test_test_account_id"
    test_posting_instructions = [
        CustomInstruction(
            postings=[
                Posting(
                    amount=Decimal(1),
                    credit=True,
                    account_id="1",
                    denomination="GBP",
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    phase=Phase.COMMITTED,
                ),
                Posting(
                    amount=Decimal(1),
                    credit=False,
                    account_id="2",
                    denomination="GBP",
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    phase=Phase.COMMITTED,
                ),
            ],
        )
    ]
    test_posting_instructions_directives = [
        PostingInstructionsDirective(
            client_batch_id="international-payment",
            value_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            posting_instructions=test_posting_instructions,
        )
    ]
    

    # Parameters

    def test_parameter(self):
        parameter = Parameter(
            name="day_of_month",
            description="Which day would you like interest to be paid?",
            display_name="Day of month to pay interest",
            level=ParameterLevel.GLOBAL,
            default_value=27,
            derived=False,
            shape=NumberShape(min_value=1, max_value=28, step=1),
        )
        self.assertEqual(parameter.default_value, 27)

    def test_parameter_init_validation(self):
        with self.assertRaises(TypeError) as ex:
            Parameter()
        self.assertEqual(
            str(ex.exception),
            "Parameter.__init__() missing 3 required keyword-only arguments: 'name', 'shape', and "
            "'level'",
        )

        with self.assertRaises(StrongTypingError) as ex:
            Parameter(name=None, shape=None, level=None)
        self.assertEqual(str(ex.exception), "Parameter attribute 'name' expected str, got None")

        with self.assertRaises(InvalidSmartContractError) as ex:
            Parameter(name="", shape=StringShape(), level=1)
        self.assertEqual(str(ex.exception), "Parameter attribute 'name' must be a non-empty string")

        with self.assertRaises(StrongTypingError) as ex:
            Parameter(name="name", shape=None, level=None)
        self.assertEqual(
            str(ex.exception),
            "Parameter attribute 'shape' expected Union[AccountIdShape, DateShape, "
            "DenominationShape, NumberShape, OptionalShape, StringShape, UnionShape],"
            " got None",
        )

        with self.assertRaises(StrongTypingError) as ex:
            Parameter(name="name", shape=Decimal, level=None)
        self.assertEqual(
            str(ex.exception),
            "Parameter attribute 'shape' expected Union[AccountIdShape, DateShape, "
            "DenominationShape, NumberShape, OptionalShape, StringShape, UnionShape], got "
            "'<class 'decimal.Decimal'>'",
        )

        with self.assertRaises(StrongTypingError) as ex:
            Parameter(name="name", shape=StringShape, level=None)
        self.assertEqual(
            str(ex.exception),
            "Parameter init arg 'shape' for parameter 'name' must be an instance of the "
            "StringShape class",
        )

        with self.assertRaises(StrongTypingError) as ex:
            Parameter(name="name", shape=StringShape(), level=None)
        self.assertEqual(
            str(ex.exception),
            "Parameter attribute 'level' expected ParameterLevel, got None",
        )

        with self.assertRaises(StrongTypingError) as ex:
            Parameter(name="name", shape=StringShape(), level=1.0)
        self.assertEqual(
            str(ex.exception),
            "Parameter attribute 'level' expected ParameterLevel, got '1.0' of type float",
        )

        with self.assertRaises(StrongTypingError) as ex:
            Parameter(name="name", shape=StringShape(), level=ParameterLevel.INSTANCE, derived=1)
        self.assertEqual(
            str(ex.exception),
            "Parameter attribute 'derived' expected bool if populated, got '1' of type int",
        )

        with self.assertRaises(StrongTypingError) as ex:
            Parameter(
                name="name",
                shape=StringShape(),
                level=ParameterLevel.INSTANCE,
                derived=True,
                display_name=True,
            )
        self.assertEqual(
            str(ex.exception),
            "Parameter attribute 'display_name' expected str if populated, got 'True' of type bool",
        )

        with self.assertRaises(StrongTypingError) as ex:
            Parameter(
                name="name",
                shape=StringShape(),
                level=ParameterLevel.INSTANCE,
                derived=True,
                display_name="display_name",
                description=StringShape(),
            )
        self.assertEqual(
            str(ex.exception),
            (
                "Parameter attribute 'description' expected str if populated, "
                + "got 'StringShape()' of type StringShape"
            ),
        )

        with self.assertRaises(StrongTypingError) as ex:
            Parameter(
                name="name",
                shape=StringShape(),
                level=ParameterLevel.INSTANCE,
                derived=True,
                display_name="display_name",
                description="description",
                default_value=StringShape(),
            )
        expected = (
            "Parameter attribute 'default_value' expected Union[Decimal, str, "
            + "datetime, OptionalValue, UnionItemValue, int] if populated, "
            + "got 'StringShape()' of type StringShape"
        )
        self.assertEqual(expected, str(ex.exception))

        with self.assertRaises(StrongTypingError) as ex:
            Parameter(
                name="name",
                shape=OptionalShape(shape=StringShape()),
                level=ParameterLevel.INSTANCE,
                derived=False,
                display_name="display_name",
                description="description",
                default_value=OptionalValue(Decimal(1)),
                update_permission=True,
            )
        self.assertEqual(
            str(ex.exception),
            "Parameter attribute 'update_permission' expected ParameterUpdatePermission if "
            "populated, got 'True' of type bool",
        )

    def test_parameter_cannot_use_optional_default_value(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            Parameter(
                name="overdraft_limit",
                level=ParameterLevel.TEMPLATE,
                description="Overdraft limit",
                shape=StringShape(),
                default_value=OptionalValue(1),
            )
        self.assertEqual(
            "Non optional shapes must have a non optional default value: overdraft_limit",
            str(ex.exception),
        )

    def test_parameter_invalid_default_value_raises_error(self):
        with self.assertRaises(StrongTypingError) as ex:
            Parameter(
                name="overdraft_limit",
                level=ParameterLevel.TEMPLATE,
                description="Overdraft limit",
                shape=StringShape(),
                default_value=500,
            )
        self.assertEqual(
            "Expected str, got '500' of type int",
            str(ex.exception),
        )

    def test_parameter_invalid_optional_default_value_raises_error(self):
        with self.assertRaises(StrongTypingError) as ex:
            Parameter(
                name="overdraft_limit",
                level=ParameterLevel.TEMPLATE,
                description="Overdraft limit",
                shape=OptionalShape(shape=StringShape()),
                default_value=500,
            )
        self.assertEqual(
            "Expected OptionalValue, got '500' of type int",
            str(ex.exception),
        )

        with self.assertRaises(StrongTypingError) as ex:
            Parameter(
                name="overdraft_limit",
                level=ParameterLevel.TEMPLATE,
                description="Overdraft limit",
                shape=OptionalShape(shape=StringShape()),
                default_value=OptionalValue(500),
            )
        self.assertEqual(
            "Expected str, got '500' of type int",
            str(ex.exception),
        )

    def test_optional_value_raises_with_invalid_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            OptionalValue(value=True)
        self.assertEqual(
            "'OptionalValue.value' expected Union[Decimal, str, datetime, UnionItemValue, int] "
            + "if populated, got 'True' of type bool",
            str(ex.exception),
        )

    def test_optional_value_raises_with_naive_datetime(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            OptionalValue(datetime(2022, 1, 1))
        self.assertEqual(
            "'value' of OptionalValue is not timezone aware.",
            str(ex.exception),
        )

    def test_optional_value_raises_with_non_utc_timezone(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            OptionalValue(datetime(2022, 1, 1, tzinfo=ZoneInfo("US/Pacific")))
        self.assertEqual(
            "'value' of OptionalValue must have timezone UTC, currently US/Pacific.",
            str(ex.exception),
        )

    def test_optional_value_raises_with_non_zoneinfo_timezone(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            OptionalValue(datetime.fromtimestamp(1, timezone.utc))
        self.assertEqual(
            "'value' of OptionalValue must have timezone of type ZoneInfo, currently <class 'datetime.timezone'>.",
            str(ex.exception),
        )

    def test_parameter_global_level(self):
        parameter = Parameter(
            name="day_of_month",
            description="Which day would you like interest to be paid?",
            display_name="Day of month to pay interest",
            level=ParameterLevel.GLOBAL,
            default_value=27,
            shape=NumberShape(min_value=1, max_value=28, step=1),
        )
        self.assertEqual(parameter.default_value, 27)

    def test_parameter_default_value_raises_with_naive_datetime(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            Parameter(
                name="day_of_month",
                description="Which day would you like interest to be paid?",
                display_name="Day of month to pay interest",
                level=ParameterLevel.GLOBAL,
                default_value=datetime(2022, 1, 1),
                shape=DateShape(
                    min_date=datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC")),
                    max_date=datetime(2020, 3, 31, tzinfo=ZoneInfo("UTC")),
                ),
            )
        self.assertEqual(
            "'default_value' of Parameter is not timezone aware.",
            str(ex.exception),
        )

    def test_parameter_default_value_raises_with_non_utc_timezone(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            Parameter(
                name="day_of_month",
                description="Which day would you like interest to be paid?",
                display_name="Day of month to pay interest",
                level=ParameterLevel.GLOBAL,
                default_value=datetime(2022, 1, 1, tzinfo=ZoneInfo("US/Pacific")),
                shape=DateShape(
                    min_date=datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC")),
                    max_date=datetime(2020, 3, 31, tzinfo=ZoneInfo("UTC")),
                ),
            )
        self.assertEqual(
            "'default_value' of Parameter must have timezone UTC, currently US/Pacific.",
            str(ex.exception),
        )

    def test_parameter_default_value_raises_with_non_zoneinfo_timezone(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            Parameter(
                name="day_of_month",
                description="Which day would you like interest to be paid?",
                display_name="Day of month to pay interest",
                level=ParameterLevel.GLOBAL,
                default_value=datetime.fromtimestamp(1, timezone.utc),
                shape=DateShape(
                    min_date=datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC")),
                    max_date=datetime(2020, 3, 31, tzinfo=ZoneInfo("UTC")),
                ),
            )
        self.assertEqual(
            "'default_value' of Parameter must have timezone of type ZoneInfo, currently <class 'datetime.timezone'>.",
            str(ex.exception),
        )

    def test_parameter_template_level(self):
        parameter = Parameter(
            name="overdraft_fee",
            description="Overdraft fee",
            display_name="Fee charged for balances over the overdraft limit",
            level=ParameterLevel.TEMPLATE,
            default_value=Decimal(15),
            shape=NumberShape(min_value=0, max_value=100, step=Decimal("0.01")),
        )
        self.assertEqual(parameter.default_value, Decimal(15))

    def test_parameter_instance_level(self):
        parameter = Parameter(
            name="minimum_interest_rate",
            description="Minimum interest rate",
            display_name="Minimum interest rate paid on positive balances",
            level=ParameterLevel.INSTANCE,
            update_permission=ParameterUpdatePermission.FIXED,
            derived=False,
            default_value=Decimal(1.0),
            shape=NumberShape(min_value=0, max_value=100, step=Decimal("0.01")),
        )
        self.assertEqual(parameter.default_value, Decimal(1.0))

    def test_parameter_string_shape(self):
        parameter = Parameter(
            name="string_parameter",
            description="template level string parameter",
            display_name="Test Parameter",
            level=ParameterLevel.TEMPLATE,
            shape=StringShape(),
        )
        self.assertTrue(isinstance(parameter.shape, StringShape))

    def test_parameter_account_id_shape(self):
        parameter = Parameter(
            name="account_id",
            description="template level account id parameter",
            display_name="Test Parameter",
            level=ParameterLevel.TEMPLATE,
            shape=AccountIdShape(),
        )
        self.assertTrue(isinstance(parameter.shape, AccountIdShape))

    def test_parameter_denomination_shape(self):
        parameter = Parameter(
            name="denomination",
            description="template level denomination parameter",
            display_name="Test Parameter",
            level=ParameterLevel.TEMPLATE,
            shape=DenominationShape(),
        )
        self.assertTrue(isinstance(parameter.shape, DenominationShape))

    def test_parameter_date_shape(self):
        date_shape = DateShape(
            min_date=datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC")),
            max_date=datetime(2020, 3, 31, tzinfo=ZoneInfo("UTC")),
        )
        parameter = Parameter(
            name="bonus_date",
            description="Date account bonus will be paid",
            display_name="Bonus date",
            level=ParameterLevel.TEMPLATE,
            shape=date_shape,
        )
        self.assertEqual(parameter.shape, date_shape)

    def test_parameter_date_shape_min_date_raise_with_naive_datetime(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            DateShape(
                min_date=datetime(2020, 1, 1),
                max_date=datetime(2020, 3, 31, tzinfo=ZoneInfo("UTC")),
            )
        self.assertEqual(
            "'min_date' of DateShape is not timezone aware.",
            str(ex.exception),
        )

    def test_parameter_date_shape_min_date_raise_with_non_utc_timezone(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            DateShape(
                min_date=datetime(2020, 1, 1, tzinfo=ZoneInfo("US/Pacific")),
                max_date=datetime(2020, 3, 31, tzinfo=ZoneInfo("UTC")),
            )
        self.assertEqual(
            "'min_date' of DateShape must have timezone UTC, currently US/Pacific.",
            str(ex.exception),
        )

    def test_parameter_date_shape_min_date_raise_with_non_zoneinfo_timezone(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            DateShape(
                min_date=datetime.fromtimestamp(1, timezone.utc),
                max_date=datetime(2020, 3, 31, tzinfo=ZoneInfo("UTC")),
            )
        self.assertEqual(
            "'min_date' of DateShape must have timezone of type ZoneInfo, currently <class 'datetime.timezone'>.",
            str(ex.exception),
        )

    def test_parameter_date_shape_max_date_raise_with_naive_datetime(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            DateShape(
                min_date=datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC")),
                max_date=datetime(2020, 3, 31),
            )
        self.assertEqual(
            "'max_date' of DateShape is not timezone aware.",
            str(ex.exception),
        )

    def test_parameter_date_shape_max_date_raise_with_non_utc_timezone(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            DateShape(
                min_date=datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC")),
                max_date=datetime(2020, 3, 31, tzinfo=ZoneInfo("US/Pacific")),
            )
        self.assertEqual(
            "'max_date' of DateShape must have timezone UTC, currently US/Pacific.",
            str(ex.exception),
        )

    def test_parameter_date_shape_max_date_raise_with_non_zoneinfo_timezone(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            DateShape(
                min_date=datetime(2020, 1, 1, tzinfo=ZoneInfo("UTC")),
                max_date=datetime.fromtimestamp(1, timezone.utc),
            )
        self.assertEqual(
            "'max_date' of DateShape must have timezone of type ZoneInfo, currently <class 'datetime.timezone'>.",
            str(ex.exception),
        )

    def test_parameter_not_using_shape_instance(self):
        with self.assertRaises(StrongTypingError) as ex:
            Parameter(
                name="day_of_month",
                description="Which day would you like interest to be paid?",
                display_name="Day of month to pay interest",
                level=ParameterLevel.GLOBAL,
                default_value=27,
                derived=False,
                shape=NumberShape,
            )
        self.assertEqual(
            str(ex.exception),
            "Parameter init arg 'shape' for parameter 'day_of_month' must be an instance of the "
            "NumberShape class",
        )

    def test_parameter_invalid_shape(self):
        with self.assertRaises(StrongTypingError) as ex:
            Parameter(
                name="day_of_month",
                description="Which day would you like interest to be paid?",
                display_name="Day of month to pay interest",
                level=ParameterLevel.GLOBAL,
                default_value=27,
                derived=False,
                shape=Decimal,
            )
        self.assertEqual(
            str(ex.exception),
            "Parameter attribute 'shape' expected Union[AccountIdShape, DateShape, "
            "DenominationShape, NumberShape, OptionalShape, StringShape, UnionShape], got "
            "'<class 'decimal.Decimal'>'",
        )

    def test_derived_parameters_cannot_have_default_values(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            Parameter(
                name="overdraft_limit",
                level=ParameterLevel.INSTANCE,
                description="Overdraft limit",
                shape=StringShape(),
                default_value="1",
                derived=True,
            )
        self.assertEqual(
            "Derived Parameters cannot have a default value or update permissions: "
            "overdraft_limit",
            str(ex.exception),
        )

    def test_parameter_default_value_multiple_optional_value(self):
        with self.assertRaises(StrongTypingError) as ex:
            Parameter(
                name="day_of_month",
                description="Which day would you like interest to be paid?",
                display_name="Day of month to pay interest",
                level=ParameterLevel.GLOBAL,
                derived=False,
                shape=OptionalShape(shape=NumberShape()),
                default_value=OptionalValue(OptionalValue(1)),
            )
        expected = (
            "'OptionalValue.value' expected Union[Decimal, str, datetime, UnionItemValue, int] "
            + "if populated, got 'OptionalValue(value=1)' of type OptionalValue"
        )
        self.assertEqual(expected, str(ex.exception))

    # Shapes

    # NumberShape

    def test_number_shape_init(self):
        with self.assertRaises(StrongTypingError) as ex:
            NumberShape(min_value="")
        self.assertEqual(
            str(ex.exception),
            "'min_value' expected Union[Decimal, int] if populated, got '' " "of type str",
        )

        with self.assertRaises(StrongTypingError) as ex:
            NumberShape(min_value=1, max_value="")
        self.assertEqual(
            str(ex.exception),
            "'max_value' expected Union[Decimal, int] if populated, got '' of type str",
        )

        with self.assertRaises(StrongTypingError) as ex:
            NumberShape(min_value=1, max_value=2, step="")
        self.assertEqual(
            str(ex.exception),
            "'step' expected Union[Decimal, int] if populated, got '' of type str",
        )

        with self.assertRaises(InvalidSmartContractError) as ex:
            NumberShape(min_value=2, max_value=1)
        self.assertEqual(str(ex.exception), "NumberShape min_value must be less than max_value")

        valid_number_shape = NumberShape(min_value=1, max_value=2, step=Decimal(0.01))
        self.assertEqual(valid_number_shape.min_value, 1)
        self.assertEqual(valid_number_shape.max_value, 2)
        self.assertEqual(valid_number_shape.step, Decimal(0.01))

    def test_number_shape_repr(self):
        shape = NumberShape(min_value=1, max_value=5, step=1)
        expected = "NumberShape(min_value=1, max_value=5, step=1)"
        self.assertEqual(expected, repr(shape))

    def test_number_shape_equality(self):
        shape = NumberShape(min_value=1, max_value=2)
        other_shape = NumberShape(min_value=1, max_value=2)

        self.assertEqual(shape, other_shape)

    def test_number_shape_unequal_max_value(self):
        shape = NumberShape(min_value=1, max_value=2)
        other_shape = NumberShape(min_value=1, max_value=42)

        self.assertNotEqual(shape, other_shape)

    # StringShape

    def test_string_shape_repr(self):
        shape = StringShape()
        expected = "StringShape()"
        self.assertEqual(expected, repr(shape))

    def test_string_shape_equality(self):
        shape = StringShape()
        other_shape = StringShape()

        self.assertEqual(shape, other_shape)

    # DateShape

    def test_date_shape_init(self):
        with self.assertRaises(StrongTypingError) as ex:
            DateShape(min_date="")
        self.assertEqual(
            str(ex.exception), "'min_date' expected datetime if populated, got '' of type str"
        )

        with self.assertRaises(StrongTypingError) as ex:
            DateShape(min_date=datetime(1999, 1, 1, tzinfo=ZoneInfo("UTC")), max_date="")
        self.assertEqual(
            str(ex.exception), "'max_date' expected datetime if populated, got '' of type str"
        )

        with self.assertRaises(InvalidSmartContractError) as ex:
            DateShape(
                min_date=datetime(2000, 1, 1, tzinfo=ZoneInfo("UTC")),
                max_date=datetime(1999, 1, 1, tzinfo=ZoneInfo("UTC")),
            )
        self.assertEqual(str(ex.exception), "DateShape min_date must be less than max_date")

        valid_date_shape_1 = DateShape()
        valid_date_shape_2 = DateShape(min_date=datetime(1999, 1, 1, tzinfo=ZoneInfo("UTC")))
        valid_date_shape_3 = DateShape(max_date=datetime(2000, 1, 1, tzinfo=ZoneInfo("UTC")))

        self.assertEqual(valid_date_shape_1.min_date, None)
        self.assertEqual(valid_date_shape_1.max_date, None)
        self.assertEqual(valid_date_shape_2.min_date, datetime(1999, 1, 1, tzinfo=ZoneInfo("UTC")))
        self.assertEqual(valid_date_shape_2.max_date, None)
        self.assertEqual(valid_date_shape_3.min_date, None)
        self.assertEqual(valid_date_shape_3.max_date, datetime(2000, 1, 1, tzinfo=ZoneInfo("UTC")))

    def test_date_shape_repr(self):
        shape = DateShape(min_date=datetime(1999, 1, 1, tzinfo=ZoneInfo("UTC")))
        expected = (
            "DateShape(min_date=datetime.datetime(1999, 1, 1, 0, 0, "
            + "tzinfo=zoneinfo.ZoneInfo(key='UTC')), max_date=None)"
        )
        self.assertEqual(expected, repr(shape))

    def test_date_shape_equality(self):
        shape = DateShape(min_date=datetime(1999, 1, 1, tzinfo=ZoneInfo("UTC")))
        other_shape = DateShape(min_date=datetime(1999, 1, 1, tzinfo=ZoneInfo("UTC")))

        self.assertEqual(shape, other_shape)

    def test_date_shape_unequal_min_date(self):
        shape = DateShape(min_date=datetime(1999, 1, 1, tzinfo=ZoneInfo("UTC")))
        other_shape = DateShape(min_date=datetime(2000, 1, 1, tzinfo=ZoneInfo("UTC")))

        self.assertNotEqual(shape, other_shape)

    # AccountIdShape

    def test_account_id_shape_repr(self):
        shape = AccountIdShape()
        expected = "AccountIdShape()"
        self.assertEqual(expected, repr(shape))

    def test_account_id_shape_equality(self):
        shape = AccountIdShape()
        other_shape = AccountIdShape()

        self.assertEqual(shape, other_shape)

    # DenominationShape

    def test_denomination_shape_repr(self):
        shape = DenominationShape(permitted_denominations=["GBP"])
        expected = "DenominationShape(permitted_denominations=['GBP'])"
        self.assertEqual(expected, repr(shape))

    def test_denomination_shape_equality(self):
        shape = DenominationShape(permitted_denominations=["GBP"])
        other_shape = DenominationShape(permitted_denominations=["GBP"])

        self.assertEqual(shape, other_shape)

    def test_denomination_shape_unequal_max_value(self):
        shape = DenominationShape(permitted_denominations=["GBP"])
        other_shape = DenominationShape(permitted_denominations=["USD"])

        self.assertNotEqual(shape, other_shape)

    # UnionShape

    def test_union_shape_init(self):
        with self.assertRaises(TypeError) as ex:
            UnionShape()
        self.assertEqual(
            str(ex.exception),
            "UnionShape.__init__() missing 1 required keyword-only argument: 'items'",
        )

        with self.assertRaises(StrongTypingError) as ex:
            UnionShape(items=1)
        self.assertEqual(
            str(ex.exception),
            "UnionShape __init__ Expected list of UnionItem objects for " "'items', got '1'",
        )

        with self.assertRaises(InvalidSmartContractError) as ex:
            UnionShape(items=[])
        self.assertEqual(str(ex.exception), "'items' must be a non empty list, got []")

        with self.assertRaises(StrongTypingError) as ex:
            UnionShape(items=[1, 2, 3])
        self.assertEqual(
            str(ex.exception), "UnionShape __init__ Expected UnionItem, got '1' of type int"
        )

        with self.assertRaises(InvalidSmartContractError) as ex:
            UnionShape(
                items=[
                    UnionItem(key="key_1", display_name="display_name_1"),
                    UnionItem(key="key_1", display_name="display_name_2"),
                ]
            )
        self.assertEqual(str(ex.exception), "Parameter contains duplicate UnionItem key_1")

        union_item = UnionItem(key="key", display_name="display_name")
        valid_union_shape = UnionShape(items=[union_item])
        self.assertEqual(valid_union_shape.items[0], union_item)

    def test_union_shape_repr(self):
        union_item = UnionItem(key="key", display_name="display_name")
        shape = UnionShape(items=[union_item])
        expected = "UnionShape(items=[UnionItem(key='key', display_name='display_name')])"
        self.assertEqual(expected, repr(shape))

    def test_union_shape_equality(self):
        union_item = UnionItem(key="key", display_name="display_name")
        shape = UnionShape(items=[union_item])

        other_union_item = UnionItem(key="key", display_name="display_name")
        other_shape = UnionShape(items=[other_union_item])

        self.assertEqual(shape, other_shape)

    def test_union_shape_unequal_items(self):
        union_item = UnionItem(key="key", display_name="display_name")
        shape = UnionShape(items=[union_item])

        other_union_item = UnionItem(key="key", display_name="display_eman")
        other_shape = UnionShape(items=[other_union_item])

        self.assertNotEqual(shape, other_shape)

    # UnionItem

    def test_union_item_init(self):
        with self.assertRaises(StrongTypingError) as ex:
            UnionItem(key=None, display_name=None)
        self.assertEqual(str(ex.exception), "UnionItem init arg 'key' must be populated")

        with self.assertRaises(StrongTypingError) as ex:
            UnionItem(key="", display_name=None)
        self.assertEqual(str(ex.exception), "UnionItem init arg 'key' must be populated")

        with self.assertRaises(StrongTypingError) as ex:
            UnionItem(key="KEY", display_name=None)
        self.assertEqual(str(ex.exception), "UnionItem init arg 'display_name' must be populated")

        with self.assertRaises(StrongTypingError) as ex:
            UnionItem(key="KEY", display_name="")
        self.assertEqual(str(ex.exception), "UnionItem init arg 'display_name' must be populated")

        valid_union_item = UnionItem(key="KEY", display_name="display_name")
        self.assertEqual(valid_union_item.key, "KEY")
        self.assertEqual(valid_union_item.display_name, "display_name")

    def test_union_item_repr(self):
        item = UnionItem(key="KEY", display_name="display_name")
        expected = "UnionItem(key='KEY', display_name='display_name')"
        self.assertEqual(expected, repr(item))

    def test_union_item_equality(self):
        item = UnionItem(key="bob", display_name="ken")
        other_item = UnionItem(key="bob", display_name="ken")
        self.assertEqual(item, other_item)

    def test_union_item_unequal_key(self):
        item = UnionItem(key="bob", display_name="ken")
        other_item = UnionItem(key="alice", display_name="ken")
        self.assertNotEqual(item, other_item)

    # UnionItemValue

    def test_union_item_value_repr(self):
        value = UnionItemValue(key="KEY")
        expected = "UnionItemValue(key='KEY')"
        self.assertEqual(expected, repr(value))

    def test_union_item_value_equality(self):
        value = UnionItemValue(key="bob")
        other_value = UnionItemValue(key="bob")
        self.assertEqual(value, other_value)

    def test_union_item_value_unequal_key(self):
        value = UnionItemValue(key="bob")
        other_value = UnionItemValue(key="alice")
        self.assertNotEqual(value, other_value)

    # OptionalShape

    def test_optional_shape_init(self):
        with self.assertRaises(TypeError) as ex:
            OptionalShape()
        self.assertEqual(
            str(ex.exception),
            "OptionalShape.__init__() missing 1 required keyword-only argument: 'shape'",
        )

        with self.assertRaises(TypeError) as ex:
            OptionalShape(1)
        self.assertEqual(
            str(ex.exception),
            "OptionalShape.__init__() takes 1 positional argument but 2 were given",
        )

        with self.assertRaises(StrongTypingError) as ex:
            OptionalShape(shape=1)
        self.assertEqual(
            str(ex.exception),
            "'shape' expected Union[AccountIdShape, DateShape, DenominationShape, NumberShape, "
            "StringShape, UnionShape], got '1' of type int",
        )

        with self.assertRaises(StrongTypingError) as ex:
            OptionalShape(shape=StringShape)
        self.assertEqual(
            str(ex.exception),
            "OptionalShape init arg 'shape' must be an instance of StringShape class",
        )

        shape = StringShape()
        valid_optional_shape = OptionalShape(shape=shape)
        self.assertEqual(valid_optional_shape.shape, shape)

    def test_optional_shape_repr(self):
        optional_value = OptionalShape(
            shape=NumberShape(min_value=1, max_value=2, step=Decimal("0.01"))
        )
        expected = (
            "OptionalShape(shape=NumberShape(min_value=1, max_value=2, step=Decimal('0.01')))"
        )
        self.assertEqual(expected, repr(optional_value))

    def test_optional_shape_equality(self):
        optional_value = OptionalShape(
            shape=NumberShape(min_value=1, max_value=2, step=Decimal(0.01))
        )
        other_optional_value = OptionalShape(
            shape=NumberShape(min_value=1, max_value=2, step=Decimal(0.01))
        )

        self.assertEqual(optional_value, other_optional_value)

    def test_optional_shape_unequal_shape(self):
        optional_value = OptionalShape(
            shape=NumberShape(min_value=1, max_value=2, step=Decimal(0.01))
        )
        other_optional_value = OptionalShape(
            shape=NumberShape(min_value=1, max_value=42, step=Decimal(0.01))
        )

        self.assertNotEqual(optional_value, other_optional_value)

    # OptionalValue

    def test_optional_value_init(self):
        with self.assertRaises(StrongTypingError) as ex:
            OptionalValue(AccountIdShape())
        expected = (
            "'OptionalValue.value' expected Union[Decimal, str, datetime, UnionItemValue, int] "
            + "if populated, got 'AccountIdShape()' of type AccountIdShape"
        )
        self.assertEqual(str(ex.exception), expected)

        with self.assertRaises(StrongTypingError) as ex:
            OptionalValue([])
        self.assertEqual(
            str(ex.exception),
            "'OptionalValue.value' expected Union[Decimal, str, datetime, UnionItemValue, int] "
            + "if populated, got '[]' of type list",
        )

        self.assertEqual(OptionalValue("").value, "")

        valid_optional_value = OptionalValue(1)
        self.assertEqual(valid_optional_value.value, 1)
        self.assertEqual(valid_optional_value.is_set(), True)
        valid_optional_value.value = None
        self.assertEqual(valid_optional_value.is_set(), False)

    def test_optional_value_repr(self):
        value = OptionalValue(45)
        expected = "OptionalValue(value=45)"
        self.assertEqual(expected, repr(value))

    def test_optional_value_equality(self):
        optional_value = OptionalValue(1)
        other_optional_value = OptionalValue(1)
        self.assertEqual(optional_value, other_optional_value)

    def test_optional_value_unequal_value(self):
        optional_value = OptionalValue(1)
        other_optional_value = OptionalValue(42)
        self.assertNotEqual(optional_value, other_optional_value)

    # FlagsObservation

    def test_flags_observation(self):
        value_datetime = datetime(year=2020, month=2, day=20, tzinfo=ZoneInfo("UTC"))
        flags = {"flag_def_1": True, "flag_def_2": False}
        flags_observation = FlagsObservation(
            flags=deepcopy(flags), value_datetime=deepcopy(value_datetime)
        )
        self.assertEqual(value_datetime, flags_observation.value_datetime)
        self.assertEqual(flags, flags_observation.flags)

    def test_flags_observation_no_value_datetime(self):
        flags = {"flag_def_1": True, "flag_def_2": False}
        flags_observation = FlagsObservation(flags=deepcopy(flags))
        self.assertIsNone(flags_observation.value_datetime)
        self.assertEqual(flags, flags_observation.flags)

    def test_flags_observation_equality(self):
        value_datetime = datetime(year=2020, month=2, day=20, tzinfo=ZoneInfo("UTC"))
        flags = {"flag_def_1": True, "flag_def_2": False}
        flags_observation_1 = FlagsObservation(flags=flags, value_datetime=value_datetime)
        flags_observation_2 = FlagsObservation(
            flags=deepcopy(flags), value_datetime=deepcopy(value_datetime)
        )
        self.assertEqual(flags_observation_1, flags_observation_2)

    def test_flags_observation_equality_different_from_proto(self):
        """Should be equal if all public attributes are equal by value."""
        value_datetime = datetime(year=2020, month=2, day=20, tzinfo=ZoneInfo("UTC"))
        flags = {"flag_def_1": True, "flag_def_2": False}
        flags_observation_1 = FlagsObservation(flags=flags, value_datetime=value_datetime)
        flags_observation_2 = FlagsObservation(
            flags=deepcopy(flags), value_datetime=deepcopy(value_datetime), _from_proto=True
        )
        self.assertEqual(flags_observation_1, flags_observation_2)

    def test_flags_observation_unequal_flags(self):
        value_datetime = datetime(year=2020, month=2, day=20, tzinfo=ZoneInfo("UTC"))
        flags_1 = {"flag_def_1": True, "flag_def_2": False}
        flags_2 = {"flag_def_1": False, "flag_def_2": False}
        flags_observation_1 = FlagsObservation(flags=flags_1, value_datetime=value_datetime)
        flags_observation_2 = FlagsObservation(flags=flags_2, value_datetime=value_datetime)
        self.assertNotEqual(flags_observation_1, flags_observation_2)

    def test_flags_observation_unequal_datetime(self):
        value_datetime = datetime(year=2020, month=2, day=20, tzinfo=ZoneInfo("UTC"))
        christmas_day = datetime(year=2022, month=12, day=25, tzinfo=ZoneInfo("UTC"))
        flags = {"flag_def_1": True, "flag_def_2": False}
        flags_observation_1 = FlagsObservation(flags=flags, value_datetime=value_datetime)
        flags_observation_2 = FlagsObservation(flags=flags, value_datetime=christmas_day)
        self.assertNotEqual(flags_observation_1, flags_observation_2)

    def test_flags_observation_repr(self):
        christmas_day = datetime(year=2022, month=12, day=25, tzinfo=ZoneInfo("UTC"))
        flags = {"flag_def_1": True, "flag_def_2": False}
        flags_observation = FlagsObservation(flags=flags, value_datetime=christmas_day)
        expected_repr = (
            "FlagsObservation(flags={'flag_def_1': True, 'flag_def_2': False}, "
            "value_datetime=datetime.datetime(2022, 12, 25, 0, 0, "
            "tzinfo=zoneinfo.ZoneInfo(key='UTC')))"
        )
        self.assertEqual(expected_repr, repr(flags_observation))

    def test_flags_observation_repr_empty_flags(self):
        flags_observation = FlagsObservation(flags=defaultdict(lambda: False), value_datetime=None)
        expected_repr = "FlagsObservation(flags={}, value_datetime=None)"
        self.assertEqual(expected_repr, repr(flags_observation))

    def test_flags_observation_raises_error_with_wrong_flags_type(self):
        with self.assertRaises(StrongTypingError) as e:
            christmas_day = datetime(year=2022, month=12, day=25, tzinfo=ZoneInfo("UTC"))
            FlagsObservation(flags=1, value_datetime=christmas_day)
        self.assertEqual(
            "'FlagsObservation.flags' expected dict[str, bool], got '1' of type int",
            str(e.exception),
        )

    def test_flags_observation_raises_error_with_wrong_value_datetime_type(self):
        with self.assertRaises(StrongTypingError) as e:
            flags = {"flag_def_1": True, "flag_def_2": False}
            FlagsObservation(flags=flags, value_datetime=1)
        self.assertEqual(
            "'FlagsObservation.value_datetime' expected datetime if populated, got '1' of type int",
            str(e.exception),
        )

    def test_flags_observation_raises_error_with_value_datetime_not_timezone_aware(self):
        with self.assertRaises(InvalidSmartContractError) as e:
            naive_datetime = datetime(year=2020, month=2, day=20)
            flags = {"flag_def_1": True, "flag_def_2": False}
            FlagsObservation(flags=flags, value_datetime=naive_datetime)
        self.assertEqual(
            "'value_datetime' of FlagsObservation is not timezone aware.", str(e.exception)
        )

    def test_flags_observation_raises_with_non_utc_timezone(self):
        value_datetime = datetime(year=2020, month=2, day=20, tzinfo=ZoneInfo("US/Pacific"))
        flags = {"flag_def_1": True, "flag_def_2": False}
        with self.assertRaises(InvalidSmartContractError) as e:
            FlagsObservation(flags=flags, value_datetime=value_datetime)
        self.assertEqual(
            str(e.exception),
            "'value_datetime' of FlagsObservation must have timezone UTC, currently " "US/Pacific.",
        )

    def test_flags_observation_raises_with_non_zoneinfo_timezone(self):
        value_datetime = datetime.fromtimestamp(1, timezone.utc)
        flags = {"flag_def_1": True, "flag_def_2": False}
        with self.assertRaises(InvalidSmartContractError) as e:
            FlagsObservation(flags=flags, value_datetime=value_datetime)
        self.assertEqual(
            "'value_datetime' of FlagsObservation must have timezone of type ZoneInfo, currently <class 'datetime.timezone'>.",
            str(e.exception),
        )

    def test_flags_observation_no_value_datetime_and_empty_balances(self):
        flags = {}
        flags_observation = FlagsObservation(flags=flags)
        self.assertIsNone(flags_observation.value_datetime)
        self.assertEqual({}, flags_observation.flags)

    # Shift, Override, Next, Previous

    def test_time_operations_equality(self):
        shift = Shift(years=3, months=1, days=12, hours=4, minutes=5, seconds=6)
        override = Override(year=2000, month=1, day=12)
        next = Next(month=1, day=12, hour=4, minute=5, second=6)
        previous = Previous(month=1, day=12, hour=6, minute=7, second=25)
        relative_date_time = RelativeDateTime(
            origin=DefinedDateTime.EFFECTIVE_DATETIME,
            shift=Shift(years=4, months=1, days=2, hours=-10, minutes=25, seconds=-45),
            find=Next(month=1, day=12, hour=4, minute=5, second=6),
        )

        other_shift = Shift(years=3, months=1, days=12, hours=4, minutes=5, seconds=6)
        other_override = Override(year=2000, month=1, day=12)
        other_next = Next(month=1, day=12, hour=4, minute=5, second=6)
        other_previous = Previous(month=1, day=12, hour=6, minute=7, second=25)
        other_relative_date_time = RelativeDateTime(
            origin=DefinedDateTime.EFFECTIVE_DATETIME,
            shift=Shift(years=4, months=1, days=2, hours=-10, minutes=25, seconds=-45),
            find=Next(month=1, day=12, hour=4, minute=5, second=6),
        )

        self.assertEqual(shift, other_shift)
        self.assertEqual(override, other_override)
        self.assertEqual(next, other_next)
        self.assertEqual(previous, other_previous)
        self.assertEqual(relative_date_time, other_relative_date_time)

    def test_time_operations_unequal_month(self):
        shift = Shift(years=3, months=1, days=12, hours=4, minutes=5, seconds=6)
        override = Override(year=2000, month=1, day=12)
        next = Next(month=1, day=12, hour=4, minute=5, second=6)
        previous = Previous(month=1, day=12, hour=6, minute=7, second=25)
        relative_date_time = RelativeDateTime(
            origin=DefinedDateTime.EFFECTIVE_DATETIME,
            shift=Shift(years=4, months=1, days=2, hours=-10, minutes=25, seconds=-45),
            find=Next(month=1, day=12, hour=4, minute=5, second=6),
        )

        other_shift = Shift(years=3, months=2, days=12, hours=4, minutes=5, seconds=6)
        other_override = Override(year=2000, month=2, day=12)
        other_next = Next(month=2, day=12, hour=4, minute=5, second=6)
        other_previous = Previous(month=2, day=12, hour=6, minute=7, second=25)
        other_relative_date_time = RelativeDateTime(
            origin=DefinedDateTime.EFFECTIVE_DATETIME,
            shift=Shift(years=4, months=1, days=2, hours=-10, minutes=25, seconds=-45),
            find=Next(month=2, day=12, hour=4, minute=5, second=6),
        )

        self.assertNotEqual(shift, other_shift)
        self.assertNotEqual(override, other_override)
        self.assertNotEqual(next, other_next)
        self.assertNotEqual(previous, other_previous)
        self.assertNotEqual(relative_date_time, other_relative_date_time)

    def test_shift_with_positive_values(self):
        shift = Shift(years=3, months=1, days=12, hours=4, minutes=5, seconds=6)
        self.assertEqual(3, shift.years)
        self.assertEqual(1, shift.months)
        self.assertEqual(12, shift.days)
        self.assertEqual(4, shift.hours)
        self.assertEqual(5, shift.minutes)
        self.assertEqual(6, shift.seconds)

    def test_shift_with_negative_values(self):
        shift = Shift(years=-4, months=-3, days=-2, hours=-10, minutes=-25, seconds=-45)
        self.assertEqual(-4, shift.years)
        self.assertEqual(-3, shift.months)
        self.assertEqual(-2, shift.days)
        self.assertEqual(-10, shift.hours)
        self.assertEqual(-25, shift.minutes)
        self.assertEqual(-45, shift.seconds)

    def test_shift_with_only_time_attribute_values(self):
        shift = Shift(hours=7, minutes=8, seconds=25)
        self.assertEqual(7, shift.hours)
        self.assertEqual(8, shift.minutes)
        self.assertEqual(25, shift.seconds)

    def test_shift_with_optional_values_not_provided(self):
        shift_missing_months = Shift(years=4, days=2, hours=-10, minutes=-25, seconds=-45)
        shift_missing_days = Shift(years=4, months=3, hours=-10, minutes=-25, seconds=-45)
        shift_missing_years = Shift(months=3, days=2, hours=-10, minutes=-25, seconds=-45)
        shift_missing_hours = Shift(years=4, months=3, days=2, minutes=25, seconds=45)
        shift_missing_minutes = Shift(years=2, days=2, months=3, hours=10, seconds=45)
        shift_missing_seconds = Shift(years=2, days=2, months=3, hours=10, minutes=25)

        # Confirm that values are populated with zero if left empty.
        self.assertEqual(None, shift_missing_years.years)
        self.assertEqual(None, shift_missing_months.months)
        self.assertEqual(None, shift_missing_days.days)
        self.assertEqual(None, shift_missing_hours.hours)
        self.assertEqual(None, shift_missing_minutes.minutes)
        self.assertEqual(None, shift_missing_seconds.seconds)

    def test_shift_repr(self):
        shift = Shift(years=2, months=3, days=-2, hours=-10, minutes=25, seconds=-45)
        expected = "Shift(years=2, months=3, days=-2, hours=-10, minutes=25, seconds=-45)"
        self.assertEqual(expected, repr(shift))

    def test_shift_raises_if_no_values_provided(self):
        with self.assertRaises(InvalidSmartContractError) as e:
            Shift()

        self.assertEqual(
            str(e.exception), "Shift object needs to be populated with at least one attribute."
        )

    def test_shift_raises_if_invalid_year_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Shift(years="1")
        self.assertEqual(
            str(e.exception), "'Shift.years' expected int if populated, got '1' of type str"
        )

    def test_shift_raises_if_invalid_month_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Shift(months="1")
        self.assertEqual(
            str(e.exception), "'Shift.months' expected int if populated, got '1' of type str"
        )

    def test_shift_raises_if_invalid_day_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Shift(days="1")
        self.assertEqual(
            str(e.exception), "'Shift.days' expected int if populated, got '1' of type str"
        )

    def test_shift_raises_if_invalid_hour_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Shift(hours="1")
        self.assertEqual(
            str(e.exception), "'Shift.hours' expected int if populated, got '1' of type str"
        )

    def test_shift_raises_if_invalid_minute_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Shift(minutes="1")
        self.assertEqual(
            str(e.exception), "'Shift.minutes' expected int if populated, got '1' of type str"
        )

    def test_shift_raises_if_invalid_second_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Shift(seconds="1")
        self.assertEqual(
            str(e.exception), "'Shift.seconds' expected int if populated, got '1' of type str"
        )

    def test_override_repr(self):
        override = Override(year=2000, month=1, day=12, hour=4, minute=5, second=6)
        expected = "Override(year=2000, month=1, day=12, hour=4, minute=5, second=6)"
        self.assertEqual(expected, repr(override))

    def test_override_with_valid_values(self):
        override = Override(year=2000, month=1, day=12, hour=4, minute=5, second=6)
        self.assertEqual(2000, override.year)
        self.assertEqual(1, override.month)
        self.assertEqual(12, override.day)
        self.assertEqual(4, override.hour)
        self.assertEqual(5, override.minute)
        self.assertEqual(6, override.second)

    def test_override_with_time_attributes_not_populated(self):
        override = Override(year=2000, month=1, day=12)
        self.assertEqual(2000, override.year)
        self.assertEqual(1, override.month)
        self.assertEqual(12, override.day)
        self.assertEqual(None, override.hour)
        self.assertEqual(None, override.minute)
        self.assertEqual(None, override.second)

    def test_override_with_optional_date_attribute_not_populated(self):
        override = Override(year=2000, day=12)
        self.assertEqual(2000, override.year)
        self.assertEqual(None, override.month)
        self.assertEqual(12, override.day)
        self.assertEqual(None, override.hour)
        self.assertEqual(None, override.minute)
        self.assertEqual(None, override.second)

    def test_override_raises_if_no_values_provided(self):
        with self.assertRaises(InvalidSmartContractError) as e:
            Override()

        self.assertEqual(
            str(e.exception), "Override object needs to be populated with at least one attribute."
        )

    def test_override_raises_if_invalid_year_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Override(year="1")
        self.assertEqual(
            str(e.exception),
            "'Override.year' expected int if populated, got '1' of type str",
        )

    def test_override_raises_if_invalid_month_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Override(month="1")
        self.assertEqual(
            str(e.exception),
            "'Override.month' expected int if populated, got '1' of type str",
        )

    def test_override_raises_if_invalid_day_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Override(day="1")
        self.assertEqual(
            str(e.exception),
            "'Override.day' expected int if populated, got '1' of type str",
        )

    def test_override_raises_if_invalid_hour_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Override(hour="1")
        self.assertEqual(
            str(e.exception),
            "'Override.hour' expected int if populated, got '1' of type str",
        )

    def test_override_raises_if_invalid_minute_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Override(minute="1")
        self.assertEqual(
            str(e.exception),
            "'Override.minute' expected int if populated, got '1' of type str",
        )

    def test_override_raises_if_invalid_second_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Override(second="1")
        self.assertEqual(
            str(e.exception),
            "'Override.second' expected int if populated, got '1' of type str",
        )

    def test_override_raises_if_invalid_year_types_provided_bool(self):
        with self.assertRaises(StrongTypingError) as e:
            Override(year=True)
        self.assertEqual(
            str(e.exception),
            "'Override.year' expected int if populated, got 'True' of type bool",
        )

    def test_override_raises_if_invalid_month_types_provided_bool(self):
        with self.assertRaises(StrongTypingError) as e:
            Override(month=True)
        self.assertEqual(
            str(e.exception),
            "'Override.month' expected int if populated, got 'True' of type bool",
        )

    def test_override_raises_if_invalid_day_types_provided_bool(self):
        with self.assertRaises(StrongTypingError) as e:
            Override(day=True)
        self.assertEqual(
            str(e.exception),
            "'Override.day' expected int if populated, got 'True' of type bool",
        )

    def test_override_raises_if_invalid_hour_types_provided_bool(self):
        with self.assertRaises(StrongTypingError) as e:
            Override(hour=True)
        self.assertEqual(
            str(e.exception),
            "'Override.hour' expected int if populated, got 'True' of type bool",
        )

    def test_override_raises_if_invalid_minute_types_provided_bool(self):
        with self.assertRaises(StrongTypingError) as e:
            Override(minute=True)
        self.assertEqual(
            str(e.exception),
            "'Override.minute' expected int if populated, got 'True' of type bool",
        )

    def test_override_raises_if_invalid_second_types_provided_bool(self):
        with self.assertRaises(StrongTypingError) as e:
            Override(second=True)
        self.assertEqual(
            str(e.exception),
            "'Override.second' expected int if populated, got 'True' of type bool",
        )

    def test_override_raises_if_values_out_of_range(self):
        with self.assertRaises(InvalidSmartContractError) as ex1:
            Override(month=13)
        with self.assertRaises(InvalidSmartContractError) as ex2:
            Override(day=32)
        with self.assertRaises(InvalidSmartContractError) as ex3:
            Override(hour=24)
        with self.assertRaises(InvalidSmartContractError) as ex4:
            Override(minute=60)
        with self.assertRaises(InvalidSmartContractError) as ex5:
            Override(second=60)
        with self.assertRaises(InvalidSmartContractError) as ex6:
            Override(year=-1)
        with self.assertRaises(InvalidSmartContractError) as ex7:
            Override(month=0)
        with self.assertRaises(InvalidSmartContractError) as ex8:
            Override(day=0)
        with self.assertRaises(InvalidSmartContractError) as ex9:
            Override(hour=-1)
        with self.assertRaises(InvalidSmartContractError) as ex10:
            Override(minute=-1)
        with self.assertRaises(InvalidSmartContractError) as ex11:
            Override(second=-1)

        for ex in [ex1, ex2, ex3, ex4, ex5, ex6, ex7, ex8, ex9, ex10, ex11]:
            self.assertEqual(str(ex.exception), "Values of Override object are out of range.")

    def test_next_with_all_values_not_provided(self):
        with self.assertRaises(TypeError) as e:
            Next()
        self.assertEqual(
            str(e.exception),
            "Next.__init__() missing 1 required keyword-only argument: 'day'",
        )

    def test_next_raises_if_invalid_month_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Next(month="1", day=1)
        self.assertEqual(
            str(e.exception), "'Next.month' expected int if populated, got '1' of type str"
        )

    def test_next_raises_if_invalid_day_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Next(day="1")
        self.assertEqual(str(e.exception), "'Next.day' expected int, got '1' of type str")

    def test_next_raises_if_invalid_hour_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Next(hour="1", day=1)
        self.assertEqual(
            str(e.exception), "'Next.hour' expected int if populated, got '1' of type str"
        )

    def test_next_raises_if_invalid_minute_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Next(minute="1", day=1)
        self.assertEqual(
            str(e.exception), "'Next.minute' expected int if populated, got '1' of type str"
        )

    def test_next_raises_if_invalid_second_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Next(second="1", day=1)
        self.assertEqual(
            str(e.exception), "'Next.second' expected int if populated, got '1' of type str"
        )

    def test_next_raises_if_invalid_month_types_provided_bool(self):
        with self.assertRaises(StrongTypingError) as e:
            Next(month=True, day=1)
        self.assertEqual(
            str(e.exception), "'Next.month' expected int if populated, got 'True' of type bool"
        )

    def test_next_raises_if_invalid_day_types_provided_bool(self):
        with self.assertRaises(StrongTypingError) as e:
            Next(day=True)
        self.assertEqual(str(e.exception), "'Next.day' expected int, got 'True' of type bool")

    def test_next_raises_if_invalid_hour_types_provided_bool(self):
        with self.assertRaises(StrongTypingError) as e:
            Next(hour=True, day=1)
        self.assertEqual(
            str(e.exception), "'Next.hour' expected int if populated, got 'True' of type bool"
        )

    def test_next_raises_if_invalid_minute_types_provided_bool(self):
        with self.assertRaises(StrongTypingError) as e:
            Next(minute=True, day=1)
        self.assertEqual(
            str(e.exception), "'Next.minute' expected int if populated, got 'True' of type bool"
        )

    def test_next_raises_if_invalid_second_types_provided_bool(self):
        with self.assertRaises(StrongTypingError) as e:
            Next(second=True, day=1)
        self.assertEqual(
            str(e.exception), "'Next.second' expected int if populated, got 'True' of type bool"
        )

    def test_previous_with_all_values_not_provided(self):
        with self.assertRaises(TypeError) as e:
            Previous()
        self.assertEqual(
            str(e.exception),
            "Previous.__init__() missing 1 required keyword-only argument: 'day'",
        )

    def test_previous_raises_if_invalid_month_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Previous(month="1", day=1)
        self.assertEqual(
            str(e.exception), "'Previous.month' expected int if populated, got '1' of type str"
        )

    def test_previous_raises_if_invalid_day_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Previous(day="1")
        self.assertEqual(str(e.exception), "'Previous.day' expected int, got '1' of type str")

    def test_previous_raises_if_invalid_hour_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Previous(hour="1", day=1)
        self.assertEqual(
            str(e.exception), "'Previous.hour' expected int if populated, got '1' of type str"
        )

    def test_previous_raises_if_invalid_minute_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Previous(minute="1", day=1)
        self.assertEqual(
            str(e.exception), "'Previous.minute' expected int if populated, got '1' of type str"
        )

    def test_previous_raises_if_invalid_second_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            Previous(second="1", day=1)
        self.assertEqual(
            str(e.exception), "'Previous.second' expected int if populated, got '1' of type str"
        )

    def test_previous_raises_if_invalid_month_types_provided_bool(self):
        with self.assertRaises(StrongTypingError) as e:
            Previous(month=True, day=1)
        self.assertEqual(
            str(e.exception), "'Previous.month' expected int if populated, got 'True' of type bool"
        )

    def test_previous_raises_if_invalid_day_types_provided_bool(self):
        with self.assertRaises(StrongTypingError) as e:
            Previous(day=True)
        self.assertEqual(str(e.exception), "'Previous.day' expected int, got 'True' of type bool")

    def test_previous_raises_if_invalid_hour_types_provided_bool(self):
        with self.assertRaises(StrongTypingError) as e:
            Previous(hour=True, day=1)
        self.assertEqual(
            str(e.exception), "'Previous.hour' expected int if populated, got 'True' of type bool"
        )

    def test_previous_raises_if_invalid_minute_types_provided_bool(self):
        with self.assertRaises(StrongTypingError) as e:
            Previous(minute=True, day=1)
        self.assertEqual(
            str(e.exception),
            "'Previous.minute' expected int if populated, got 'True' of type " "bool",
        )

    def test_previous_raises_if_invalid_second_types_provided_bool(self):
        with self.assertRaises(StrongTypingError) as e:
            Previous(second=True, day=1)
        self.assertEqual(
            str(e.exception),
            "'Previous.second' expected int if populated, got 'True' of type " "bool",
        )

    def test_next_repr(self):
        next_native_type = Next(month=1, day=12, hour=4, minute=5, second=6)
        expected = "Next(month=1, day=12, hour=4, minute=5, second=6)"
        self.assertEqual(expected, repr(next_native_type))

    def test_next_with_all_values_populated(self):
        next_native_type = Next(month=1, day=12, hour=4, minute=5, second=6)
        self.assertEqual(1, next_native_type.month)
        self.assertEqual(12, next_native_type.day)
        self.assertEqual(4, next_native_type.hour)
        self.assertEqual(5, next_native_type.minute)
        self.assertEqual(6, next_native_type.second)

    def test_previous_repr(self):
        previous = Previous(month=5, day=17, hour=3, minute=45, second=12)
        expected = "Previous(month=5, day=17, hour=3, minute=45, second=12)"
        self.assertEqual(expected, repr(previous))

    def test_previous_with_all_values_populated(self):
        previous_native_type = Previous(month=5, day=17, hour=3, minute=45, second=12)
        self.assertEqual(5, previous_native_type.month)
        self.assertEqual(17, previous_native_type.day)
        self.assertEqual(3, previous_native_type.hour)
        self.assertEqual(45, previous_native_type.minute)
        self.assertEqual(12, previous_native_type.second)

    def test_next_raises_if_values_out_of_range(self):
        with self.assertRaises(InvalidSmartContractError) as ex1:
            Next(month=13, day=2)
        with self.assertRaises(InvalidSmartContractError) as ex2:
            Next(day=32)
        with self.assertRaises(InvalidSmartContractError) as ex3:
            Next(hour=24, day=2)
        with self.assertRaises(InvalidSmartContractError) as ex4:
            Next(minute=60, day=2)
        with self.assertRaises(InvalidSmartContractError) as ex5:
            Next(second=60, day=2)
        with self.assertRaises(InvalidSmartContractError) as ex6:
            Next(month=0, day=2)
        with self.assertRaises(InvalidSmartContractError) as ex7:
            Next(day=0)

        for ex in [ex1, ex2, ex3, ex4, ex5, ex6, ex7]:
            self.assertEqual(str(ex.exception), "Values of Next object are out of range.")

    def test_previous_raises_if_values_out_of_range(self):
        with self.assertRaises(InvalidSmartContractError) as ex1:
            Previous(month=13, day=2)
        with self.assertRaises(InvalidSmartContractError) as ex2:
            Previous(day=32)
        with self.assertRaises(InvalidSmartContractError) as ex3:
            Previous(hour=24, day=2)
        with self.assertRaises(InvalidSmartContractError) as ex4:
            Previous(minute=60, day=2)
        with self.assertRaises(InvalidSmartContractError) as ex5:
            Previous(second=60, day=2)
        with self.assertRaises(InvalidSmartContractError) as ex6:
            Previous(month=0, day=2)
        with self.assertRaises(InvalidSmartContractError) as ex7:
            Previous(day=0)

        for ex in [ex1, ex2, ex3, ex4, ex5, ex6, ex7]:
            self.assertEqual(str(ex.exception), "Values of Previous object are out of range.")

    def test_relative_date_time_with_next(self):
        relative_date_time_native_object = RelativeDateTime(
            origin=DefinedDateTime.EFFECTIVE_DATETIME,
            shift=Shift(years=4, months=1, days=2, hours=-10, minutes=25, seconds=-45),
            find=Next(month=1, day=12, hour=4, minute=5, second=6),
        )

        self.assertEqual(4, relative_date_time_native_object.shift.years)
        self.assertEqual(1, relative_date_time_native_object.shift.months)
        self.assertEqual(2, relative_date_time_native_object.shift.days)
        self.assertEqual(-10, relative_date_time_native_object.shift.hours)
        self.assertEqual(25, relative_date_time_native_object.shift.minutes)
        self.assertEqual(-45, relative_date_time_native_object.shift.seconds)

        self.assertEqual(1, relative_date_time_native_object.find.month)
        self.assertEqual(12, relative_date_time_native_object.find.day)
        self.assertEqual(4, relative_date_time_native_object.find.hour)
        self.assertEqual(5, relative_date_time_native_object.find.minute)
        self.assertEqual(6, relative_date_time_native_object.find.second)

        self.assertEqual(
            DefinedDateTime.EFFECTIVE_DATETIME, relative_date_time_native_object.origin
        )

    def test_relative_date_time_with_previous(self):
        relative_date_time_native_object = RelativeDateTime(
            origin=DefinedDateTime.EFFECTIVE_DATETIME,
            shift=Shift(years=4, months=1, days=2, hours=-10, minutes=25, seconds=-45),
            find=Previous(month=1, day=12, hour=6, minute=7, second=25),
        )

        self.assertEqual(4, relative_date_time_native_object.shift.years)
        self.assertEqual(1, relative_date_time_native_object.shift.months)
        self.assertEqual(2, relative_date_time_native_object.shift.days)
        self.assertEqual(-10, relative_date_time_native_object.shift.hours)
        self.assertEqual(25, relative_date_time_native_object.shift.minutes)
        self.assertEqual(-45, relative_date_time_native_object.shift.seconds)

        self.assertEqual(1, relative_date_time_native_object.find.month)
        self.assertEqual(12, relative_date_time_native_object.find.day)
        self.assertEqual(6, relative_date_time_native_object.find.hour)
        self.assertEqual(7, relative_date_time_native_object.find.minute)
        self.assertEqual(25, relative_date_time_native_object.find.second)

        self.assertEqual(
            DefinedDateTime.EFFECTIVE_DATETIME, relative_date_time_native_object.origin
        )

    def test_relative_date_time_raises_if_invalid_shift_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            RelativeDateTime(shift="1", origin=DefinedDateTime.EFFECTIVE_DATETIME)
        self.assertEqual(
            str(e.exception),
            "'RelativeDateTime.shift' expected Shift if populated, got '1' of type str",
        )

    def test_relative_date_time_raises_if_invalid_find_types_provided(self):
        with self.assertRaises(StrongTypingError) as e:
            RelativeDateTime(find="1", origin=DefinedDateTime.EFFECTIVE_DATETIME)
        self.assertEqual(
            str(e.exception),
            "'RelativeDateTime.find' expected Union[Next, Previous, Override] if populated, got "
            "'1' of type str",
        )

    def test_relative_date_time_with_shift_and_find_not_populated(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            RelativeDateTime(origin=DefinedDateTime.EFFECTIVE_DATETIME)

        self.assertEqual(
            str(ex.exception),
            "RelativeDateTime Object requires either shift or find attributes to be populated",
        )

    def test_relative_date_time_repr(self):
        relative_date_time_native_object = RelativeDateTime(
            origin=DefinedDateTime.EFFECTIVE_DATETIME,
            shift=Shift(years=4, months=1, days=2, hours=-10, minutes=25, seconds=-45),
            find=Override(year=2, month=1, day=12, hour=2, minute=9, second=53),
        )
        expected = (
            "RelativeDateTime(origin=DefinedDateTime.EFFECTIVE_DATETIME, "
            + "shift=Shift(years=4, months=1, days=2, hours=-10, minutes=25, seconds=-45), "
            + "find=Override(year=2, month=1, day=12, hour=2, minute=9, second=53))"
        )
        self.assertEqual(expected, repr(relative_date_time_native_object))

    def test_relative_date_time_with_override(self):
        relative_date_time_native_object = RelativeDateTime(
            origin=DefinedDateTime.EFFECTIVE_DATETIME,
            shift=Shift(years=4, months=1, days=2, hours=-10, minutes=25, seconds=-45),
            find=Override(year=2, month=1, day=12, hour=2, minute=9, second=53),
        )

        self.assertEqual(4, relative_date_time_native_object.shift.years)
        self.assertEqual(1, relative_date_time_native_object.shift.months)
        self.assertEqual(2, relative_date_time_native_object.shift.days)
        self.assertEqual(-10, relative_date_time_native_object.shift.hours)
        self.assertEqual(25, relative_date_time_native_object.shift.minutes)
        self.assertEqual(-45, relative_date_time_native_object.shift.seconds)

        self.assertEqual(2, relative_date_time_native_object.find.year)
        self.assertEqual(1, relative_date_time_native_object.find.month)
        self.assertEqual(12, relative_date_time_native_object.find.day)
        self.assertEqual(2, relative_date_time_native_object.find.hour)
        self.assertEqual(9, relative_date_time_native_object.find.minute)
        self.assertEqual(53, relative_date_time_native_object.find.second)

        self.assertEqual(
            DefinedDateTime.EFFECTIVE_DATETIME, relative_date_time_native_object.origin
        )

    def test_relative_date_time_with_origin_interval_start(self):
        relative_date_time_native_object = RelativeDateTime(
            shift=Shift(years=4, months=1, days=2, hours=-10, minutes=25, seconds=-45),
            find=Override(year=2, month=1, day=12, hour=2, minute=9, second=53),
            origin=DefinedDateTime.INTERVAL_START,
        )

        self.assertEqual(4, relative_date_time_native_object.shift.years)
        self.assertEqual(1, relative_date_time_native_object.shift.months)
        self.assertEqual(2, relative_date_time_native_object.shift.days)
        self.assertEqual(-10, relative_date_time_native_object.shift.hours)
        self.assertEqual(25, relative_date_time_native_object.shift.minutes)
        self.assertEqual(-45, relative_date_time_native_object.shift.seconds)

        self.assertEqual(2, relative_date_time_native_object.find.year)
        self.assertEqual(1, relative_date_time_native_object.find.month)
        self.assertEqual(12, relative_date_time_native_object.find.day)
        self.assertEqual(2, relative_date_time_native_object.find.hour)
        self.assertEqual(9, relative_date_time_native_object.find.minute)
        self.assertEqual(53, relative_date_time_native_object.find.second)

        self.assertEqual(DefinedDateTime.INTERVAL_START, relative_date_time_native_object.origin)

    def test_relative_date_time_with_origin_using_illegal_live_value(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            RelativeDateTime(
                shift=Shift(years=4, months=1, days=2, hours=-10, minutes=25, seconds=-45),
                find=Override(year=2, month=1, day=12, hour=2, minute=9, second=53),
                origin=DefinedDateTime.LIVE,
            )
        self.assertEqual(
            str(ex.exception),
            "RelativeDateTime origin attribute does not support 'DefinedDateTime.LIVE'",
        )

    # ParametersObservation

    def test_parameters_observation(self):
        value_datetime = datetime(year=2020, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        parameters = {
            "parameter_1": "string_value",
            "parameter_2": Decimal("3.14159"),
        }
        parameters_observation = ParametersObservation(
            parameters=parameters,
            value_datetime=value_datetime,
        )
        self.assertEqual(parameters, parameters_observation.parameters)
        self.assertEqual(value_datetime, parameters_observation.value_datetime)

    def test_parameters_observation_repr(self):
        value_datetime = datetime(year=2020, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        parameters = {
            "parameter_1": "string_value",
            "parameter_2": Decimal("3.14159"),
        }
        parameters_observation = ParametersObservation(
            parameters=parameters,
            value_datetime=value_datetime,
        )
        expected = (
            "ParametersObservation(parameters={'parameter_1': 'string_value', "
            + "'parameter_2': Decimal('3.14159')}, value_datetime="
            + "datetime.datetime(2020, 1, 1, 0, 0, tzinfo=zoneinfo.ZoneInfo(key='UTC')))"
        )
        self.assertEqual(expected, repr(parameters_observation))

    def test_parameters_observation_equality(self):
        value_datetime = datetime(year=2020, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        parameters = {
            "parameter_1": "string_value",
            "parameter_2": Decimal("3.14159"),
        }
        parameters_observation = ParametersObservation(
            parameters=parameters,
            value_datetime=value_datetime,
        )
        other_parameters_observation = ParametersObservation(
            parameters=parameters,
            value_datetime=value_datetime,
        )
        self.assertEqual(parameters_observation, other_parameters_observation)

    def test_parameters_observation_unequal_parameters(self):
        value_datetime = datetime(year=2020, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        parameters = {
            "parameter_1": "string_value",
            "parameter_2": Decimal("3.14159"),
        }
        parameters_observation = ParametersObservation(
            parameters=parameters,
            value_datetime=value_datetime,
        )
        other_parameters = {
            "parameter_1": "string_value",
            "parameter_2": Decimal("3.1"),
        }
        other_parameters_observation = ParametersObservation(
            parameters=other_parameters,
            value_datetime=value_datetime,
        )
        self.assertNotEqual(parameters_observation, other_parameters_observation)

    def test_parameters_observation_empty_parameters(self):
        value_datetime = datetime(year=2020, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        parameters = {}
        parameters_observation = ParametersObservation(
            parameters=parameters,
            value_datetime=value_datetime,
        )
        self.assertEqual(parameters, parameters_observation.parameters)
        self.assertEqual(value_datetime, parameters_observation.value_datetime)

    def test_parameters_observation_raises_with_naive_value_datetime(self):
        value_datetime = datetime(year=2020, month=1, day=1)
        parameters = {
            "parameter_1": "string_value",
            "parameter_2": Decimal("3.14159"),
        }
        with self.assertRaises(InvalidSmartContractError) as e:
            ParametersObservation(
                parameters=parameters,
                value_datetime=value_datetime,
            )
        self.assertEqual(
            str(e.exception),
            "'value_datetime' of ParametersObservation is not timezone aware.",
        )

    def test_parameters_observation_raises_with_non_utc_timezone(self):
        value_datetime = datetime(year=2020, month=1, day=1, tzinfo=ZoneInfo("US/Pacific"))
        parameters = {
            "parameter_1": "string_value",
            "parameter_2": Decimal("3.14159"),
        }
        with self.assertRaises(InvalidSmartContractError) as e:
            ParametersObservation(
                parameters=parameters,
                value_datetime=value_datetime,
            )
        self.assertEqual(
            str(e.exception),
            "'value_datetime' of ParametersObservation must have timezone UTC, currently US/Pacific.",
        )

    def test_parameters_observation_raises_with_non_zoneinfo_timezone(self):
        value_datetime = datetime.fromtimestamp(1, timezone.utc)
        parameters = {
            "parameter_1": "string_value",
            "parameter_2": Decimal("3.14159"),
        }
        with self.assertRaises(InvalidSmartContractError) as e:
            ParametersObservation(
                parameters=parameters,
                value_datetime=value_datetime,
            )
        self.assertEqual(
            "'value_datetime' of ParametersObservation must have timezone of type ZoneInfo, currently <class 'datetime.timezone'>.",
            str(e.exception),
        )

    def test_parameters_observation_raises_with_naive_datetime_parameters(self):
        value_datetime = datetime(year=2020, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        parameters = {
            "parameter_1": "string_value",
            "parameter_2": datetime(2022, 1, 1),
        }
        with self.assertRaises(InvalidSmartContractError) as e:
            ParametersObservation(
                parameters=parameters,
                value_datetime=value_datetime,
            )
        self.assertEqual(
            str(e.exception),
            "'parameters[\"parameter_2\"]' of ParametersObservation is not timezone aware.",
        )

    def test_parameters_observation_raises_with_non_utc_timezone_datetime_parameters(self):
        value_datetime = datetime(year=2020, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        parameters = {
            "parameter_1": "string_value",
            "parameter_2": datetime(2022, 1, 1, tzinfo=ZoneInfo("US/Pacific")),
        }
        with self.assertRaises(InvalidSmartContractError) as e:
            ParametersObservation(
                parameters=parameters,
                value_datetime=value_datetime,
            )
        self.assertEqual(
            str(e.exception),
            "'parameters[\"parameter_2\"]' of ParametersObservation must have timezone UTC, currently US/Pacific.",
        )

    def test_parameters_observation_raises_with_non_zoneinfo_timezone_datetime_parameters(self):
        value_datetime = datetime(year=2020, month=1, day=1, tzinfo=ZoneInfo("UTC"))
        parameters = {
            "parameter_1": "string_value",
            "parameter_2": datetime.fromtimestamp(1, timezone.utc),
        }
        with self.assertRaises(InvalidSmartContractError) as e:
            ParametersObservation(
                parameters=parameters,
                value_datetime=value_datetime,
            )
        self.assertEqual(
            "'parameters[\"parameter_2\"]' of ParametersObservation must have timezone of type ZoneInfo, currently <class 'datetime.timezone'>.",
            str(e.exception),
        )

    # EndOfMonthSchedule

    def test_end_of_month_schedule_type_default_values(self):
        end_of_month_schedule = EndOfMonthSchedule(day=1)
        self.assertEqual(0, end_of_month_schedule.hour)
        self.assertEqual(0, end_of_month_schedule.minute)
        self.assertEqual(0, end_of_month_schedule.second)
        self.assertEqual(ScheduleFailover.FIRST_VALID_DAY_BEFORE, end_of_month_schedule.failover)

    def test_end_of_month_schedule_repr(self):
        end_of_month_schedule = EndOfMonthSchedule(day=1)
        expected = (
            "EndOfMonthSchedule(day=1, hour=0, minute=0, second=0, "
            + "failover=ScheduleFailover.FIRST_VALID_DAY_BEFORE)"
        )
        self.assertEqual(expected, repr(end_of_month_schedule))

    def test_end_of_month_schedule_equality(self):
        end_of_month_schedule = EndOfMonthSchedule(day=1)
        other_end_of_month_schedule = EndOfMonthSchedule(day=1)
        self.assertEqual(end_of_month_schedule, other_end_of_month_schedule)

    def test_end_of_month_schedule_unequal_day(self):
        end_of_month_schedule = EndOfMonthSchedule(day=1)
        other_end_of_month_schedule = EndOfMonthSchedule(day=24)
        self.assertNotEqual(end_of_month_schedule, other_end_of_month_schedule)

    def test_end_of_month_schedule_type_can_set_values(self):
        end_of_month_schedule = EndOfMonthSchedule(
            day=15, hour=10, minute=20, second=5, failover=ScheduleFailover.FIRST_VALID_DAY_BEFORE
        )
        self.assertEqual(15, end_of_month_schedule.day)
        self.assertEqual(10, end_of_month_schedule.hour)
        self.assertEqual(20, end_of_month_schedule.minute)
        self.assertEqual(5, end_of_month_schedule.second)
        self.assertEqual(ScheduleFailover.FIRST_VALID_DAY_BEFORE, end_of_month_schedule.failover)

    def test_end_of_month_schedule_type_can_set_decimal_values(self):
        end_of_month_schedule = EndOfMonthSchedule(
            day=Decimal(15),
            hour=Decimal(10),
            minute=Decimal(20),
            second=Decimal(5),
            failover=ScheduleFailover.FIRST_VALID_DAY_BEFORE,
        )
        self.assertEqual(15, end_of_month_schedule.day)
        self.assertEqual(10, end_of_month_schedule.hour)
        self.assertEqual(20, end_of_month_schedule.minute)
        self.assertEqual(5, end_of_month_schedule.second)
        self.assertEqual(ScheduleFailover.FIRST_VALID_DAY_BEFORE, end_of_month_schedule.failover)

    def test_end_of_month_schedule_raise_if_values_out_of_range(self):
        values = [
            {"day": 0},
            {"day": 32},
            {"day": 1, "hour": -1},
            {"day": 1, "hour": 25},
            {"day": 1, "minute": -1},
            {"day": 1, "minute": 61},
            {"day": 1, "second": -1},
            {"day": 1, "second": 61},
        ]

        error_parts = [
            ("day", 1, 31),
            ("day", 1, 31),
            ("hour", 0, 23),
            ("hour", 0, 23),
            ("minute", 0, 59),
            ("minute", 0, 59),
            ("second", 0, 59),
            ("second", 0, 59),
        ]

        for i, value in enumerate(values):
            time_component, low, high = error_parts[i]
            with self.assertRaises(InvalidSmartContractError) as e:
                EndOfMonthSchedule(**value)
            self.assertEqual(
                str(e.exception),
                f"Argument {time_component} of EndOfMonthSchedule"
                f" object is out of range({low}-{high}).",
            )

    def test_end_of_month_schedule_raises_if_decimal_values_out_of_range(self):
        values = [
            {"day": Decimal(0)},
            {"day": Decimal(32)},
            {"day": Decimal(1), "hour": Decimal(-1)},
            {"day": Decimal(1), "hour": Decimal(25)},
            {"day": Decimal(1), "minute": Decimal(-1)},
            {"day": Decimal(1), "minute": Decimal(61)},
            {"day": Decimal(1), "second": Decimal(-1)},
            {"day": Decimal(1), "second": Decimal(61)},
        ]

        error_parts = [
            ("day", 1, 31),
            ("day", 1, 31),
            ("hour", 0, 23),
            ("hour", 0, 23),
            ("minute", 0, 59),
            ("minute", 0, 59),
            ("second", 0, 59),
            ("second", 0, 59),
        ]

        for i, value in enumerate(values):
            time_component, low, high = error_parts[i]
            with self.assertRaises(InvalidSmartContractError) as e:
                EndOfMonthSchedule(**value)
            self.assertEqual(
                str(e.exception),
                f"Argument {time_component} of EndOfMonthSchedule"
                f" object is out of range({low}-{high}).",
            )

    def test_end_of_month_schedule_raises_if_decimal_values_not_integer(self):
        values = [
            {"day": Decimal(0.1)},
            {"day": Decimal(1.5)},
            {"day": Decimal(-1.5)},
            {"day": Decimal(1), "hour": Decimal(1.5)},
            {"day": Decimal(1), "minute": Decimal(1.5)},
            {"day": Decimal(1), "second": Decimal(1.5)},
        ]

        error_parts = [
            ("day", 1, 31),
            ("day", 1, 31),
            ("day", 1, 31),
            ("hour", 0, 23),
            ("minute", 0, 59),
            ("second", 0, 59),
        ]

        for i, value in enumerate(values):
            time_component, low, high = error_parts[i]
            with self.assertRaises(InvalidSmartContractError) as e:
                EndOfMonthSchedule(**value)
            self.assertEqual(
                str(e.exception),
                f"Argument {time_component} of EndOfMonthSchedule"
                f" object is not an integer value in range({low}-{high}).",
            )

    def test_end_of_month_schedule_invalid_argument_raises(self):
        Test = namedtuple(
            "Test",
            ["method_kwargs", "invalid_field_name", "expected_type", "got_value", "got_type"],
        )

        test_cases = [
            Test(
                method_kwargs={"day": "1"},
                invalid_field_name="day",
                expected_type="int",
                got_value="1",
                got_type="str",
            ),
            Test(
                method_kwargs={"day": 1, "hour": "1"},
                invalid_field_name="hour",
                expected_type="int",
                got_value="1",
                got_type="str",
            ),
            Test(
                method_kwargs={"day": "1", "hour": 1},
                invalid_field_name="day",
                expected_type="int",
                got_value="1",
                got_type="str",
            ),
            Test(
                method_kwargs={"day": 1, "minute": (1,)},
                invalid_field_name="minute",
                expected_type="int",
                got_value="(1,)",
                got_type="tuple",
            ),
            Test(
                method_kwargs={"day": [1], "minute": 1},
                invalid_field_name="day",
                expected_type="int",
                got_value="[1]",
                got_type="list",
            ),
            Test(
                method_kwargs={"day": {1: 1}, "second": 1},
                invalid_field_name="day",
                expected_type="int",
                got_value="{1: 1}",
                got_type="dict",
            ),
            Test(
                method_kwargs={"day": 1.0, "second": 1.0},
                invalid_field_name="day",
                expected_type="int",
                got_value="1.0",
                got_type="float",
            ),
            Test(
                method_kwargs={"day": 1, "failover": 2},
                invalid_field_name="failover",
                expected_type="ScheduleFailover",
                got_value="2",
                got_type="int",
            ),
        ]

        for test_case in test_cases:
            with self.assertRaises(StrongTypingError) as e:
                EndOfMonthSchedule(**test_case.method_kwargs)
            self.assertEqual(
                str(e.exception),
                f"'EndOfMonthSchedule.{test_case.invalid_field_name}' expected {test_case.expected_type}, "
                f"got '{test_case.got_value}' of type {test_case.got_type}",
            )

    # SupervisedHooks

    def test_supervised_hooks(self):
        supervised_hooks = SupervisedHooks(pre_posting_hook=SupervisionExecutionMode.OVERRIDE)
        self.assertEqual(supervised_hooks.pre_posting_hook, SupervisionExecutionMode.OVERRIDE)

    def test_supervised_hooks_argument_required(self):
        with self.assertRaises(InvalidSmartContractError) as e:
            SupervisedHooks()

        self.assertEqual(
            str(e.exception),
            "At least one hook supervision must be specified.",
        )

    def test_supervised_hooks_repr(self):
        supervised_hooks = SupervisedHooks(pre_posting_hook=SupervisionExecutionMode.OVERRIDE)
        expected = "SupervisedHooks(pre_posting_hook=SupervisionExecutionMode.OVERRIDE)"
        self.assertEqual(expected, repr(supervised_hooks))

    def test_supervised_hooks_equality(self):
        supervised_hooks = SupervisedHooks(pre_posting_hook=SupervisionExecutionMode.OVERRIDE)
        other_supervised_hooks = SupervisedHooks(pre_posting_hook=SupervisionExecutionMode.OVERRIDE)
        self.assertEqual(supervised_hooks, other_supervised_hooks)

    def test_supervised_hooks_unequal_pre_posting_hook(self):
        supervised_hooks = SupervisedHooks(pre_posting_hook=SupervisionExecutionMode.OVERRIDE)
        other_supervised_hooks = SupervisedHooks(pre_posting_hook=SupervisionExecutionMode.INVOKED)
        self.assertNotEqual(supervised_hooks, other_supervised_hooks)

    # Rejection

    def test_rejection(self):
        rejection = Rejection(message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS)
        self.assertEqual("Rejection", rejection.message)
        self.assertEqual(RejectionReason.INSUFFICIENT_FUNDS, rejection.reason_code)

    def test_rejection_repr(self):
        rejection = Rejection(message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS)
        expected = "Rejection(message='Rejection', reason_code=RejectionReason.INSUFFICIENT_FUNDS)"
        self.assertEqual(expected, repr(rejection))

    def test_rejection_equality(self):
        rejection = Rejection(message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS)
        other_rejection = Rejection(
            message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS
        )
        self.assertEqual(rejection, other_rejection)

    def test_rejection_unequal_reason_code(self):
        rejection = Rejection(message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS)
        other_rejection = Rejection(
            message="Rejection", reason_code=RejectionReason.WRONG_DENOMINATION
        )
        self.assertNotEqual(rejection, other_rejection)

    def test_rejection_with_no_reason_code(self):
        rejection = Rejection(message="Rejection")
        self.assertEqual("Rejection", rejection.message)
        self.assertEqual(None, rejection.reason_code)

    def test_rejection_raises_with_no_message(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            Rejection(message="", reason_code=RejectionReason.INSUFFICIENT_FUNDS)
        self.assertEqual("Rejection 'message' must be populated", str(ex.exception))

    def test_rejection_from_proto_skips_validation(self):
        rejection = Rejection(message=True, _from_proto=True)
        self.assertEqual(True, rejection.message)
        self.assertEqual(None, rejection.reason_code)

    # ServicingInterface

    @skip_if_not_enabled(SERVICING_GROUPS)
    def test_servicing_interface(self):
        servicing_interface = ServicingInterface(
            name="test1",
            attributes=self.test_attributes,
        )
        self.assertEqual("test1", servicing_interface.name)
        self.assertEqual(self.test_attributes, servicing_interface.attributes)

    @skip_if_not_enabled(SERVICING_GROUPS)
    def test_servicing_interface_no_attributes(self):
        servicing_interface = ServicingInterface(
            name="test1",
        )
        self.assertEqual("test1", servicing_interface.name)
        self.assertEqual(None, servicing_interface.attributes)

    @skip_if_not_enabled(SERVICING_GROUPS)
    def test_servicing_interface_repr(self):
        servicing_interface = ServicingInterface(
            name="test1",
            attributes=self.test_attributes,
        )
        self.assertTrue(issubclass(ServicingInterface, ContractsLanguageDunderMixin))
        self.assertIn("ServicingInterface", repr(servicing_interface))

    @skip_if_not_enabled(SERVICING_GROUPS)
    def test_servicing_interface_equality(self):
        servicing_interface = ServicingInterface(
            name="test1",
            attributes=self.test_attributes,
        )
        other_servicing_interface = ServicingInterface(
            name="test1",
            attributes=deepcopy(self.test_attributes),
        )
        self.assertEqual(servicing_interface, other_servicing_interface)

    @skip_if_not_enabled(SERVICING_GROUPS)
    def test_servicing_interface_unequal_name(self):
        servicing_interface = ServicingInterface(
            name="test1",
            attributes=self.test_attributes,
        )
        other_servicing_interface = ServicingInterface(
            name="test2",
            attributes=self.test_attributes,
        )
        self.assertNotEqual(servicing_interface, other_servicing_interface)

    @skip_if_not_enabled(SERVICING_GROUPS)
    def test_servicing_interface_raises_with_name_wrong_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            ServicingInterface(name=42)
        self.assertEqual(
            "'ServicingInterface.name' expected str, got '42' of type int", str(ex.exception)
        )

    @skip_if_not_enabled(SERVICING_GROUPS)
    def test_servicing_interface_raises_with_name_not_populated(self):
        with self.assertRaises(StrongTypingError) as ex:
            ServicingInterface(name=None)
        self.assertEqual("'ServicingInterface.name' expected str, got None", str(ex.exception))

    @skip_if_not_enabled(SERVICING_GROUPS)
    def test_servicing_interface_raises_with_name_empty(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            ServicingInterface(name="")
        self.assertEqual("'ServicingInterface.name' must be a non-empty string", str(ex.exception))

    @skip_if_not_enabled(SERVICING_GROUPS)
    def test_servicing_interface_raises_with_attributes_wrong_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            ServicingInterface(name="test1", attributes=42)
        self.assertEqual(
            "Expected list of Attribute objects for 'ServicingInterface.attributes', got '42'",
            str(ex.exception),
        )

    @skip_if_not_enabled(SERVICING_GROUPS)
    def test_servicing_interface_raises_with_attributes_wrong_item_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            ServicingInterface(name="test1", attributes=[42])
        self.assertEqual(
            "'ServicingInterface.attributes[0]' expected Attribute, got '42' of type int",
            str(ex.exception),
        )

    @skip_if_not_enabled(SERVICING_GROUPS)
    def test_servicing_interface_raises_with_attributes_same_name(self):
        with self.assertRaises(InvalidSmartContractError) as ex:
            ServicingInterface(
                name="test1",
                attributes=[
                    Attribute(name="same", data_type=AttributeDecimalType()),
                    Attribute(name="same", data_type=AttributeStringType()),
                ],
            )
        self.assertEqual(
            "ServicingInterface contains Attributes with duplicate names, duplicates: ['same']",
            str(ex.exception),
        )

    # <NOT RELEASE END>

    # SmartContractDescriptor

    def test_smart_contract_descriptor(self):
        supervised_smart_contract = SmartContractDescriptor(
            alias="test1",
            smart_contract_version_id="test_smart_contract_version_id",
            supervise_post_posting_hook=True,
        )
        self.assertEqual("test1", supervised_smart_contract.alias)

    def test_smart_contract_descriptor_repr(self):
        supervised_smart_contract = SmartContractDescriptor(
            alias="test1",
            smart_contract_version_id="test_smart_contract_version_id",
            supervise_post_posting_hook=True,
        )
        expected = (
            "SmartContractDescriptor(alias='test1', "
            + "smart_contract_version_id='test_smart_contract_version_id', "
            + "supervise_post_posting_hook=True, supervised_hooks=None)"
        )
        self.maxDiff = None
        self.assertEqual(expected, repr(supervised_smart_contract))

    def test_smart_contract_descriptor_equality(self):
        supervised_smart_contract = SmartContractDescriptor(
            alias="test1",
            smart_contract_version_id="test_smart_contract_version_id",
            supervise_post_posting_hook=True,
        )
        other_supervised_smart_contract = SmartContractDescriptor(
            alias="test1",
            smart_contract_version_id="test_smart_contract_version_id",
            supervise_post_posting_hook=True,
        )
        self.assertEqual(supervised_smart_contract, other_supervised_smart_contract)

    def test_smart_contract_descriptor_unequal_alias(self):
        supervised_smart_contract = SmartContractDescriptor(
            alias="test1",
            smart_contract_version_id="test_smart_contract_version_id",
            supervise_post_posting_hook=True,
        )
        other_supervised_smart_contract = SmartContractDescriptor(
            alias="test2",
            smart_contract_version_id="test_smart_contract_version_id",
            supervise_post_posting_hook=True,
        )
        self.assertNotEqual(supervised_smart_contract, other_supervised_smart_contract)

    def test_smart_contract_descriptor_raises_if_alias_not_populated(self):
        with self.assertRaises(StrongTypingError) as ex:
            SmartContractDescriptor(
                alias=None, smart_contract_version_id="test_smart_contract_version_id"
            )
        self.assertEqual("SmartContractDescriptor 'alias' must be populated", str(ex.exception))

    def test_smart_contract_descriptor_raises_if_smart_contract_version_id_not_populated(self):
        with self.assertRaises(StrongTypingError) as ex:
            SmartContractDescriptor(alias="alias", smart_contract_version_id=None)
        self.assertEqual(
            "SmartContractDescriptor 'smart_contract_version_id' must be populated",
            str(ex.exception),
        )

    def test_smart_contract_descriptor_no_supervised_hooks(self):
        supervised_smart_contract = SmartContractDescriptor(
            alias="test1", smart_contract_version_id="test_smart_contract_version_id"
        )
        self.assertEqual("test1", supervised_smart_contract.alias)
        self.assertIsNone(supervised_smart_contract.supervised_hooks)

    def test_smart_contract_descriptor_raises_with_invalid_supervised_hooks_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            SmartContractDescriptor(
                alias="test1",
                smart_contract_version_id="test_smart_contract_version_id",
                supervised_hooks="foo",
            )
        self.assertEqual(
            "'SmartContractDescriptor.supervised_hooks' expected SupervisedHooks if populated, got "
            "'foo' of type str",
            str(ex.exception),
        )

    # Parameter

    def test_can_construct_parameter(self):
        shape = NumberShape()
        parameter = Parameter(
            name="name",
            description="description",
            display_name="display_name",
            level=ParameterLevel.INSTANCE,
            default_value=42,
            shape=shape,
        )

        self.assertEqual("name", parameter.name)
        self.assertEqual("description", parameter.description)
        self.assertEqual("display_name", parameter.display_name)
        self.assertEqual(ParameterLevel.INSTANCE, parameter.level)
        self.assertEqual(42, parameter.default_value)
        self.assertEqual(shape, parameter.shape)

    def test_parameter_repr(self):
        parameter = Parameter(
            name="name",
            description="description",
            display_name="display_name",
            level=ParameterLevel.INSTANCE,
            default_value=42,
            shape=NumberShape(),
        )
        expected = (
            "Parameter(name='name', shape=NumberShape(min_value=None, max_value=None, step=None), "
            + "level=ParameterLevel.INSTANCE, derived=False, display_name='display_name', "
            + "description='description', default_value=42, update_permission=None)"
        )
        self.assertEqual(expected, repr(parameter))

    def test_parameter_equality(self):
        shape = NumberShape()
        parameter = Parameter(
            name="name",
            description="description",
            display_name="display_name",
            level=ParameterLevel.INSTANCE,
            default_value=42,
            shape=shape,
        )
        other_shape = NumberShape()
        other_parameter = Parameter(
            name="name",
            description="description",
            display_name="display_name",
            level=ParameterLevel.INSTANCE,
            default_value=42,
            shape=other_shape,
        )

        self.assertEqual(parameter, other_parameter)

    def test_parameter_unequal_shape(self):
        shape = NumberShape()
        parameter = Parameter(
            name="name",
            description="description",
            display_name="display_name",
            level=ParameterLevel.INSTANCE,
            default_value=42,
            shape=shape,
        )
        other_shape = NumberShape(min_value=42)
        other_parameter = Parameter(
            name="name",
            description="description",
            display_name="display_name",
            level=ParameterLevel.INSTANCE,
            default_value=42,
            shape=other_shape,
        )

        self.assertNotEqual(parameter, other_parameter)

    # PlanNotificationDirective

    def test_plan_notification_directive_equality(self):
        plan_notification_directive = PlanNotificationDirective(
            notification_type="test_notification_type",
            notification_details={"key1": "value1"},
        )
        other_plan_notification_directive = PlanNotificationDirective(
            notification_type="test_notification_type",
            notification_details={"key1": "value1"},
        )
        self.assertEqual(plan_notification_directive, other_plan_notification_directive)

    def test_plan_notification_directive_unequal_notification_details(self):
        plan_notification_directive = PlanNotificationDirective(
            notification_type="test_notification_type",
            notification_details={"key1": "value1"},
        )
        other_plan_notification_directive = PlanNotificationDirective(
            notification_type="test_notification_type",
            notification_details={"key1": "value42"},
        )
        self.assertNotEqual(plan_notification_directive, other_plan_notification_directive)

    # PostingInstructionsDirective

    def test_posting_instructions_directive_repr_inherited_from_mixin(self):
        directive = self.test_posting_instructions_directives[0]
        self.assertTrue(issubclass(PostingInstructionsDirective, ContractsLanguageDunderMixin))
        self.assertIn("PostingInstructionsDirective", repr(directive))

    def test_posting_instructions_directive_equality(self):
        posting_instructions_directive = self.test_posting_instructions_directives[0]
        other_custom_instructions = CustomInstruction(
            postings=[
                Posting(
                    amount=Decimal(1),
                    credit=True,
                    account_id="1",
                    denomination="GBP",
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    phase=Phase.COMMITTED,
                ),
                Posting(
                    amount=Decimal(1),
                    credit=False,
                    account_id="2",
                    denomination="GBP",
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    phase=Phase.COMMITTED,
                ),
            ]
        )
        other_posting_instructions_directive = PostingInstructionsDirective(
            client_batch_id="international-payment",
            value_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            posting_instructions=[other_custom_instructions],
        )
        self.assertEqual(posting_instructions_directive, other_posting_instructions_directive)

    def test_posting_instructions_directive_unequal_posting_instructions(self):
        posting_instructions_directive = self.test_posting_instructions_directives[0]
        other_custom_instructions = CustomInstruction(
            postings=[
                Posting(
                    amount=Decimal(1),
                    credit=True,
                    account_id="1",
                    denomination="GBP",
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    phase=Phase.COMMITTED,
                ),
                Posting(
                    amount=Decimal(1),
                    credit=False,
                    account_id="42",
                    denomination="GBP",
                    account_address=DEFAULT_ADDRESS,
                    asset=DEFAULT_ASSET,
                    phase=Phase.COMMITTED,
                ),
            ]
        )
        other_posting_instructions_directive = PostingInstructionsDirective(
            client_batch_id="international-payment",
            value_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            posting_instructions=[other_custom_instructions],
        )
        self.assertNotEqual(posting_instructions_directive, other_posting_instructions_directive)

    # Logger

    def test_logger_debug_to_stderr(self):
        logger = Logger.instance()

        with StringIO() as buf:
            with redirect_stderr(buf):
                logger.debug("hello from the tside")

            self.assertEqual("hello from the tside", buf.getvalue().strip())

    def test_logger_debug_raises_with_invalid_type(self):
        logger = Logger.instance()

        with self.assertRaises(StrongTypingError) as ex:
            logger.debug({"hello": "from", "the": "tside"})

        self.assertEqual(
            "'message' expected str, got '{'hello': 'from', 'the': 'tside'}' of type dict",
            str(ex.exception),
        )

        with self.assertRaises(StrongTypingError) as ex:
            logger.debug(["hello", "from", "the", "tside"])

        self.assertEqual(
            "'message' expected str, got '['hello', 'from', 'the', 'tside']' of type list",
            str(ex.exception),
        )

    def test_logger_raises_on_init(self):
        with self.assertRaises(Exception) as ex:
            Logger()
        self.assertEqual("Logger is a singleton. Use instance() instead.", str(ex.exception))
