from unittest import TestCase
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from ..types import (
    AccountNotificationDirective,
    ActivationHookResult,
    
    CustomInstruction,
    DeactivationHookResult,
    DEFAULT_ADDRESS,
    DEFAULT_ASSET,
    DerivedParameterHookResult,
    OptionalValue,
    Phase,
    PlanNotificationDirective,
    Posting,
    PostingInstructionsDirective,
    PostingInstructionEnrichment,
    PostingInstructionRejectionReason,
    PostParameterChangeHookResult,
    PreParameterChangeHookResult,
    PostParameterChangeAdjustmentHookResult,
    PostPostingAdjustmentHookResult,
    PostPostingHookResult,
    PrePostingHookResult,
    Rejection,
    RejectionReason,
    ScheduleExpression,
    ScheduledEvent,
    ScheduledEventAdjustmentHookResult,
    ScheduledEventHookResult,
    ScheduleSkip,
    SupervisorActivationHookResult,
    SupervisorConversionHookResult,
    SupervisorPostPostingHookResult,
    SupervisorPrePostingHookResult,
    SupervisorScheduledEventHookResult,
    UnionItemValue,
    UpdateAccountEventTypeDirective,
    UpdatePlanEventTypeDirective,
    ConversionAdjustmentHookResult,
    ConversionHookResult,
    AttributeHookResult,
    
    
)

from ..types import hook_results
from ..types.hook_results import (
    validate_account_directives,
    validate_supervisee_directives,
    
    validate_rejection_exclusivity,
)

from .....utils import symbols
from .....utils.exceptions import (
    StrongTypingError,
    IllegalPython,
    InvalidSmartContractError,
)
from .....utils.feature_flags import (
    is_fflag_enabled,
    skip_if_not_enabled,
    ACCOUNT_ATTRIBUTE_HOOK,
    
    ADJUSTMENTS,
    ENRICH_POSTING_INSTRUCTIONS,
    EXPECTED_PID_REJECTIONS,
    
    HISTORIC_CONTRACT_RESOLUTION,
)
from .....utils.types_utils import (
    ContractsLanguageDunderMixin,
)


class HookResultTestBase(TestCase):
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
    test_account_notification_directives = [
        AccountNotificationDirective(
            notification_type="test_notification_type",
            notification_details={"key1": "value1"},
        )
    ]
    test_posting_instructions_directives = [
        PostingInstructionsDirective(
            client_batch_id="international-payment",
            value_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            posting_instructions=test_posting_instructions,
        )
    ]
    
    test_posting_instructions_directive_with_rejection_reasons = PostingInstructionsDirective(
        client_batch_id="international-payment",
        value_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
        posting_instructions=test_posting_instructions,
        non_blocking_rejection_reasons={
            PostingInstructionRejectionReason.INSUFFICIENT_FUNDS,
            PostingInstructionRejectionReason.ACCOUNT_STATUS_INVALID,
        },
    )
    test_scheduled_events_return_value = {
        "event_1": ScheduledEvent(
            start_datetime=datetime(1970, 1, 1, second=1, tzinfo=ZoneInfo("UTC")),
            end_datetime=datetime(1970, 1, 1, second=2, tzinfo=ZoneInfo("UTC")),
            expression=ScheduleExpression(
                year="2000",
                month="1",
                day="1",
                hour="0",
                minute="0",
                second="0",
            ),
            skip=ScheduleSkip(
                end=datetime(1970, 1, 1, second=3, tzinfo=ZoneInfo("UTC")),
            ),
        ),
        "event_2": ScheduledEvent(
            start_datetime=datetime(1970, 1, 1, second=5, tzinfo=ZoneInfo("UTC")),
            end_datetime=datetime(1970, 1, 1, second=6, tzinfo=ZoneInfo("UTC")),
            expression=ScheduleExpression(
                day_of_week="mon",
            ),
        ),
    }
    test_update_account_event_type_directives = [
        UpdateAccountEventTypeDirective(
            event_type="event_type_1",
            end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
        )
    ]
    test_plan_notification_directives = [
        PlanNotificationDirective(
            notification_type="test_notification_type",
            notification_details={"key1": "value1"},
        )
    ]
    test_update_plan_event_type_directives = [
        UpdatePlanEventTypeDirective(
            event_type="event_type",
            skip=True,
        )
    ]
    test_supervisee_account_notification_directives = {
        test_account_id: [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
    }
    test_supervisee_posting_instructions_directives = {
        test_account_id: test_posting_instructions_directives
    }
    test_supervisee_update_account_event_type_directives = {
        test_account_id: [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
    }
    test_rejection = Rejection(
        message="Cannot open account while account holder has no savings",
        reason_code=RejectionReason.AGAINST_TNC,
    )

    


# Smart Contract Hook Results


class TestAttributeHookResult(HookResultTestBase):
    @skip_if_not_enabled(ACCOUNT_ATTRIBUTE_HOOK)
    def test_attribute_hook_result_with_decimal_value(self):
        attribute_hook_result = AttributeHookResult(attribute_value=Decimal(1000))
        self.assertEqual(attribute_hook_result.attribute_value, Decimal(1000))

    @skip_if_not_enabled(ACCOUNT_ATTRIBUTE_HOOK)
    def test_attribute_hook_result_with_datetime_value(self):
        attribute_hook_result = AttributeHookResult(attribute_value=datetime(2024, 1, 1))
        self.assertEqual(attribute_hook_result.attribute_value, datetime(2024, 1, 1))

    @skip_if_not_enabled(ACCOUNT_ATTRIBUTE_HOOK)
    def test_attribute_hook_result_with_str_value(self):
        attribute_hook_result = AttributeHookResult(attribute_value="and thanks for all the fish")
        self.assertEqual(attribute_hook_result.attribute_value, "and thanks for all the fish")

    @skip_if_not_enabled(ACCOUNT_ATTRIBUTE_HOOK)
    def test_attribute_hook_result_with_none_value(self):
        attribute_hook_result = AttributeHookResult()
        self.assertEqual(attribute_hook_result.attribute_value, None)

    @skip_if_not_enabled(ACCOUNT_ATTRIBUTE_HOOK)
    def test_attribute_hook_result_raises_with_unsupported_value(self):
        with self.assertRaises(StrongTypingError) as ex:
            AttributeHookResult(attribute_value=1)
        self.assertEqual(
            "'attribute_value' expected Union[Decimal, datetime, str] if populated, got '1' of type int",
            str(ex.exception),
        )


class TestActivationHookResult(HookResultTestBase):
    def test_activation_hook_result_without_directives_or_return_values(self):
        activation_hook_result = ActivationHookResult()
        self.assertEqual([], activation_hook_result.account_notification_directives)
        self.assertEqual([], activation_hook_result.posting_instructions_directives)
        self.assertEqual({}, activation_hook_result.scheduled_events_return_value)

    def test_activation_hook_result_with_directives_and_return_values(self):
        account_notification_directives = [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        posting_instructions_directives = self.test_posting_instructions_directives
        activation_hook_result = ActivationHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            scheduled_events_return_value=self.test_scheduled_events_return_value,
        )
        self.assertEqual(
            account_notification_directives,
            activation_hook_result.account_notification_directives,
        )
        self.assertEqual(
            posting_instructions_directives,
            activation_hook_result.posting_instructions_directives,
        )
        self.assertEqual(
            self.test_scheduled_events_return_value,
            activation_hook_result.scheduled_events_return_value,
        )
        self.assertIsNone(activation_hook_result.rejection)

    @patch.object(hook_results, "validate_account_directives")
    def test_activation_hook_result_validates_account_directives(
        self, mock_validate_account_directives: Mock
    ):
        ActivationHookResult(
            account_notification_directives=self.test_account_notification_directives,
            posting_instructions_directives=self.test_posting_instructions_directives,
            scheduled_events_return_value=self.test_scheduled_events_return_value,
        )
        mock_validate_account_directives.assert_called_once_with(
            account_directives=self.test_account_notification_directives,
            posting_directives=self.test_posting_instructions_directives,
        )

    @patch.object(hook_results, "validate_rejection_exclusivity")
    def test_activation_hook_result_validates_rejection_is_not_returned_with_directives_or_return_values(
        self, mock_validate_rejection_exclusivity: Mock
    ):
        ActivationHookResult(
            account_notification_directives=self.test_account_notification_directives,
            posting_instructions_directives=self.test_posting_instructions_directives,
            scheduled_events_return_value=self.test_scheduled_events_return_value,
            rejection=self.test_rejection,
        )
        mock_validate_rejection_exclusivity.assert_called_once_with(
            class_name="ActivationHookResult",
            rejection=self.test_rejection,
            account_notification_directives=self.test_account_notification_directives,
            posting_instructions_directives=self.test_posting_instructions_directives,
            scheduled_events_return_value=self.test_scheduled_events_return_value,
        )

    def test_activation_hook_raises_with_result_invalid_rejection(self):
        with self.assertRaises(StrongTypingError) as ex:
            ActivationHookResult(rejection=27)
        self.assertEqual(
            "'rejection' expected Rejection if populated, got '27' of type int", str(ex.exception)
        )

    def test_activation_hook_result_repr(self):
        account_notification_directives = [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        posting_instructions_directives = self.test_posting_instructions_directives
        activation_hook_result = ActivationHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            scheduled_events_return_value=self.test_scheduled_events_return_value,
        )
        expected = (
            f"ActivationHookResult(account_notification_directives={repr(account_notification_directives)}, "
            f"posting_instructions_directives={repr(posting_instructions_directives)}, "
            f"scheduled_events_return_value={repr(self.test_scheduled_events_return_value)}, "
            f"rejection={repr(activation_hook_result.rejection)})"
        )
        self.assertEqual(expected, repr(activation_hook_result))

    def test_activation_hook_result_equality(self):
        account_notification_directives = [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        posting_instructions_directives = self.test_posting_instructions_directives
        activation_hook_result = ActivationHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            scheduled_events_return_value=self.test_scheduled_events_return_value,
        )
        other_activation_hook_result = ActivationHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            scheduled_events_return_value=self.test_scheduled_events_return_value,
        )

        self.assertEqual(activation_hook_result, other_activation_hook_result)

    def test_activation_hook_result_unequal_scheduled_events_return_value(self):
        account_notification_directives = [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        posting_instructions_directives = self.test_posting_instructions_directives
        other_scheduled_events_return_value = {
            "event_1": ScheduledEvent(
                start_datetime=datetime(1970, 1, 1, second=1, tzinfo=ZoneInfo("UTC")),
                end_datetime=datetime(1970, 1, 1, second=2, tzinfo=ZoneInfo("UTC")),
                expression=ScheduleExpression(
                    year="2000",
                    month="1",
                    day="1",
                    hour="0",
                    minute="0",
                    second="0",
                ),
                skip=ScheduleSkip(
                    end=datetime(1970, 1, 1, second=3, tzinfo=ZoneInfo("UTC")),
                ),
            ),
            "event_2": ScheduledEvent(
                start_datetime=datetime(1970, 1, 1, second=5, tzinfo=ZoneInfo("UTC")),
                end_datetime=datetime(1975, 1, 1, second=6, tzinfo=ZoneInfo("UTC")),
                expression=ScheduleExpression(
                    day_of_week="mon",
                ),
            ),
        }
        activation_hook_result = ActivationHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            scheduled_events_return_value=self.test_scheduled_events_return_value,
        )
        other_activation_hook_result = ActivationHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            scheduled_events_return_value=other_scheduled_events_return_value,
        )

        self.assertNotEqual(activation_hook_result, other_activation_hook_result)


class TestConversionHookResult(HookResultTestBase):
    def test_conversion_hook_result_without_directives_or_return_values(self):
        conversion_hook_result = ConversionHookResult()
        self.assertEqual([], conversion_hook_result.account_notification_directives)
        self.assertEqual([], conversion_hook_result.posting_instructions_directives)
        self.assertEqual({}, conversion_hook_result.scheduled_events_return_value)
        self.assertIsNone(conversion_hook_result.rejection)

    def test_conversion_hook_result_with_directives_and_return_values(self):
        conversion_hook_result = ConversionHookResult(
            account_notification_directives=self.test_account_notification_directives,
            posting_instructions_directives=self.test_posting_instructions_directives,
            scheduled_events_return_value=self.test_scheduled_events_return_value,
        )
        self.assertEqual(
            self.test_account_notification_directives,
            conversion_hook_result.account_notification_directives,
        )
        self.assertEqual(
            self.test_posting_instructions_directives,
            conversion_hook_result.posting_instructions_directives,
        )
        self.assertEqual(
            self.test_scheduled_events_return_value,
            conversion_hook_result.scheduled_events_return_value,
        )
        self.assertIsNone(conversion_hook_result.rejection)

    @patch.object(hook_results, "validate_account_directives")
    def test_conversion_hook_result_validates_account_directives(
        self, mock_validate_account_directives: Mock
    ):
        ConversionHookResult(
            account_notification_directives=self.test_account_notification_directives,
            posting_instructions_directives=self.test_posting_instructions_directives,
            scheduled_events_return_value=self.test_scheduled_events_return_value,
        )
        mock_validate_account_directives.assert_called_once_with(
            account_directives=self.test_account_notification_directives,
            posting_directives=self.test_posting_instructions_directives,
        )

    @patch.object(hook_results, "validate_rejection_exclusivity")
    def test_conversion_hook_result_validates_rejection_is_not_returned_with_directives_or_return_values(
        self, mock_validate_rejection_exclusivity: Mock
    ):
        ConversionHookResult(
            account_notification_directives=self.test_account_notification_directives,
            posting_instructions_directives=self.test_posting_instructions_directives,
            scheduled_events_return_value=self.test_scheduled_events_return_value,
            rejection=self.test_rejection,
        )
        mock_validate_rejection_exclusivity.assert_called_once_with(
            class_name="ConversionHookResult",
            rejection=self.test_rejection,
            account_notification_directives=self.test_account_notification_directives,
            posting_instructions_directives=self.test_posting_instructions_directives,
            scheduled_events_return_value=self.test_scheduled_events_return_value,
        )

    def test_conversion_hook_result_repr(self):
        conversion_hook_result = ConversionHookResult(
            rejection=Rejection(
                message="Cannot convert account while account holder has no savings",
                reason_code=RejectionReason.AGAINST_TNC,
            )
        )
        expected = (
            "ConversionHookResult(account_notification_directives=[], "
            + "posting_instructions_directives=[], scheduled_events_return_value={}, "
            + "rejection=Rejection(message='Cannot convert account while account "
            + "holder has no savings', reason_code=RejectionReason.AGAINST_TNC))"
        )
        self.assertEqual(expected, repr(conversion_hook_result))

    def test_conversion_hook_result_equality(self):
        rejection = Rejection(
            message="Cannot convert account while account holder has no savings",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        conversion_hook_result = ConversionHookResult(rejection=rejection)
        other_rejection = Rejection(
            message="Cannot convert account while account holder has no savings",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        other_conversion_hook_result = ConversionHookResult(rejection=other_rejection)

        self.assertEqual(conversion_hook_result, other_conversion_hook_result)

    def test_conversion_hook_result_unequal_rejection(self):
        rejection = Rejection(
            message="Cannot convert account while account holder has no savings",
            reason_code=RejectionReason.AGAINST_TNC,
        )
        conversion_hook_result = ConversionHookResult(rejection=rejection)
        other_rejection = Rejection(
            message="Cannot convert account while account holder has no savings",
            reason_code=RejectionReason.UNKNOWN_REASON,
        )
        other_conversion_hook_result = ConversionHookResult(rejection=other_rejection)

        self.assertNotEqual(conversion_hook_result, other_conversion_hook_result)

    def test_conversion_hook_result_raises_with_invalid_rejection(self):
        with self.assertRaises(StrongTypingError) as ex:
            ConversionHookResult(rejection=27)
        self.assertEqual(
            "'rejection' expected Rejection if populated, got '27' of type int", str(ex.exception)
        )

    # <NOT RELEASE END>

    def test_conversion_hook_result_raises_with_invalid_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            ConversionHookResult(account_notification_directives=True)
        expected = (
            "Expected list of AccountNotificationDirective objects for 'account_directives', got "
            "'True'"
        )
        self.assertEqual(expected, str(ex.exception))
        with self.assertRaises(StrongTypingError) as ex:
            ConversionHookResult(posting_instructions_directives=True)
        expected = (
            "Expected list of PostingInstructionsDirective objects for 'posting_directives', got "
            "'True'"
        )
        self.assertEqual(expected, str(ex.exception))
        with self.assertRaises(StrongTypingError) as ex:
            ConversionHookResult(scheduled_events_return_value=True)
        expected = "Expected dict, got 'True' of type bool"
        self.assertEqual(expected, str(ex.exception))


class TestDeactivationHookResult(HookResultTestBase):
    def test_deactivation_hook_result_without_directives_and_rejection(self):
        deactivation_hook_result = DeactivationHookResult()
        self.assertEqual([], deactivation_hook_result.account_notification_directives)
        self.assertEqual([], deactivation_hook_result.posting_instructions_directives)
        self.assertIsNone(deactivation_hook_result.rejection)

    def test_deactivation_hook_result_with_directives(self):
        account_notification_directives = [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        posting_instructions_directives = self.test_posting_instructions_directives
        update_account_event_type_directives = [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
        deactivation_hook_result = DeactivationHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=update_account_event_type_directives,
        )
        self.assertEqual(
            account_notification_directives,
            deactivation_hook_result.account_notification_directives,
        )
        self.assertEqual(
            posting_instructions_directives,
            deactivation_hook_result.posting_instructions_directives,
        )
        self.assertEqual(
            update_account_event_type_directives,
            deactivation_hook_result.update_account_event_type_directives,
        )

    @patch.object(hook_results, "validate_rejection_exclusivity")
    def test_deactivation_hook_result_validates_rejection_is_not_returned_with_directives_or_return_values(
        self, mock_validate_rejection_exclusivity: Mock
    ):
        DeactivationHookResult(
            account_notification_directives=self.test_account_notification_directives,
            posting_instructions_directives=self.test_posting_instructions_directives,
            update_account_event_type_directives=self.test_update_account_event_type_directives,
            rejection=self.test_rejection,
        )
        mock_validate_rejection_exclusivity.assert_called_once_with(
            class_name="DeactivationHookResult",
            rejection=self.test_rejection,
            account_notification_directives=self.test_account_notification_directives,
            posting_instructions_directives=self.test_posting_instructions_directives,
            update_account_event_type_directives=self.test_update_account_event_type_directives,
        )

    def test_deactivation_hook_result_repr(self):
        account_notification_directives = [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        posting_instructions_directives = self.test_posting_instructions_directives
        update_account_event_type_directives = [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
        deactivation_hook_result = DeactivationHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=update_account_event_type_directives,
        )
        expected = (
            f"DeactivationHookResult(account_notification_directives={repr(account_notification_directives)}, "
            f"posting_instructions_directives={repr(posting_instructions_directives)}, "
            f"update_account_event_type_directives={repr(update_account_event_type_directives)}, "
            f"rejection={repr(deactivation_hook_result.rejection)})"
        )
        self.assertEqual(expected, repr(deactivation_hook_result))

    def test_deactivation_hook_result_equality(self):
        account_notification_directives = [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        posting_instructions_directives = self.test_posting_instructions_directives
        update_account_event_type_directives = [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
        deactivation_hook_result = DeactivationHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=update_account_event_type_directives,
        )
        other_deactivation_hook_result = DeactivationHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=update_account_event_type_directives,
        )

        self.assertEqual(deactivation_hook_result, other_deactivation_hook_result)

    def test_deactivation_hook_result_unequal_update_account_event_type_directives(self):
        account_notification_directives = [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        posting_instructions_directives = self.test_posting_instructions_directives
        update_account_event_type_directives = [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
        other_update_account_event_type_directives = [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2032, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
        deactivation_hook_result = DeactivationHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=update_account_event_type_directives,
        )
        other_deactivation_hook_result = DeactivationHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=other_update_account_event_type_directives,
        )

        self.assertNotEqual(deactivation_hook_result, other_deactivation_hook_result)

    @patch.object(hook_results, "validate_account_directives")
    def test_deactivation_hook_result_validates_account_directives(
        self, mock_validate_account_directives: Mock
    ):
        DeactivationHookResult(
            account_notification_directives=self.test_account_notification_directives,
            posting_instructions_directives=self.test_posting_instructions_directives,
            update_account_event_type_directives=self.test_update_account_event_type_directives,
        )
        mock_validate_account_directives.assert_called_once_with(
            account_directives=self.test_account_notification_directives,
            posting_directives=self.test_posting_instructions_directives,
            update_events=self.test_update_account_event_type_directives,
        )


class TestDerivedParameterHookResult(HookResultTestBase):
    def test_derived_parameter_result_repr(self):
        result = DerivedParameterHookResult(
            parameters_return_value={
                "interest_account": "1",
                "repayment_date": datetime(2019, 12, 12, 13, 20),
                "denomination": "GBP",
                "monthly_repayment": Decimal("500.00"),
                "customer_name": "Paul",
                "tier": UnionItemValue(key="GOLD"),
                "interest_payment_day": OptionalValue(),
                "overdraft_limit": OptionalValue(Decimal("1000.00")),
                "overdraft_fee": OptionalValue(None),
            }
        )
        expected = (
            "DerivedParameterHookResult(parameters_return_value={'interest_account': '1', "
            + "'repayment_date': datetime.datetime(2019, 12, 12, 13, 20), 'denomination': 'GBP', "
            + "'monthly_repayment': Decimal('500.00'), 'customer_name': 'Paul', 'tier': "
            + "UnionItemValue(key='GOLD'), 'interest_payment_day': OptionalValue(value=None), "
            + "'overdraft_limit': OptionalValue(value=Decimal('1000.00')), "
            + "'overdraft_fee': OptionalValue(value=None)})"
        )
        self.assertEqual(expected, repr(result))

    def test_derived_parameter_result(self):
        derived_parameters_result = DerivedParameterHookResult(
            parameters_return_value={
                "interest_account": "1",
                "repayment_date": datetime(2019, 12, 12, 13, 20),
                "denomination": "GBP",
                "monthly_repayment": Decimal("500.00"),
                "customer_name": "Paul",
                "tier": UnionItemValue(key="GOLD"),
                "interest_payment_day": OptionalValue(),
                "overdraft_limit": OptionalValue(Decimal("1000.00")),
                "overdraft_fee": OptionalValue(None),
            }
        )
        self.assertEqual(9, len(derived_parameters_result.parameters_return_value))

    def test_derived_parameter_result_equality(self):
        derived_parameters_result = DerivedParameterHookResult(
            parameters_return_value={
                "interest_account": "1",
                "repayment_date": datetime(2019, 12, 12, 13, 20),
                "denomination": "GBP",
            }
        )
        other_derived_parameters_result = DerivedParameterHookResult(
            parameters_return_value={
                "interest_account": "1",
                "repayment_date": datetime(2019, 12, 12, 13, 20),
                "denomination": "GBP",
            }
        )
        self.assertEqual(derived_parameters_result, other_derived_parameters_result)

    def test_derived_parameter_result_unequal_parameters_return_value(self):
        derived_parameters_result = DerivedParameterHookResult(
            parameters_return_value={
                "interest_account": "1",
                "repayment_date": datetime(2019, 12, 12, 13, 20),
                "denomination": "GBP",
            }
        )
        other_derived_parameters_result = DerivedParameterHookResult(
            parameters_return_value={
                "interest_account": "1",
                "repayment_date": datetime(2042, 12, 12, 13, 20),
                "denomination": "GBP",
            }
        )
        self.assertNotEqual(derived_parameters_result, other_derived_parameters_result)

    def test_derived_parameter_result_raises_with_invalid_return_value(self):
        with self.assertRaises(StrongTypingError) as ex:
            DerivedParameterHookResult(parameters_return_value=None)
        self.assertEqual(
            "'parameters_return_value' expected dict, got None",
            str(ex.exception),
        )


class TestPreParameterChangeHookResult(HookResultTestBase):
    def test_pre_parameter_change_hook_result(self):
        rejection = Rejection(message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS)
        pre_parameter_change_hook_result = PreParameterChangeHookResult(rejection=rejection)
        self.assertEqual(rejection, pre_parameter_change_hook_result.rejection)

    def test_pre_parameter_change_hook_result_repr(self):
        rejection = Rejection(message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS)
        pre_parameter_change_hook_result = PreParameterChangeHookResult(rejection=rejection)
        expected = (
            "PreParameterChangeHookResult(rejection=Rejection(message='Rejection', "
            + "reason_code=RejectionReason.INSUFFICIENT_FUNDS))"
        )
        self.assertEqual(expected, repr(pre_parameter_change_hook_result))

    def test_pre_parameter_change_hook_result_equality(self):
        rejection = Rejection(message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS)
        pre_parameter_change_hook_result = PreParameterChangeHookResult(rejection=rejection)
        other_rejection = Rejection(
            message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS
        )
        other_pre_parameter_change_hook_result = PreParameterChangeHookResult(
            rejection=other_rejection
        )

        self.assertEqual(pre_parameter_change_hook_result, other_pre_parameter_change_hook_result)

    def test_pre_parameter_change_hook_result_unequal_rejection(self):
        rejection = Rejection(message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS)
        pre_parameter_change_hook_result = PreParameterChangeHookResult(rejection=rejection)
        other_rejection = Rejection(
            message="Rejection", reason_code=RejectionReason.WRONG_DENOMINATION
        )
        other_pre_parameter_change_hook_result = PreParameterChangeHookResult(
            rejection=other_rejection
        )

        self.assertNotEqual(
            pre_parameter_change_hook_result, other_pre_parameter_change_hook_result
        )

    def test_pre_parameter_change_hook_result_with_no_rejection(self):
        pre_parameter_change_hook_result = PreParameterChangeHookResult()
        self.assertEqual(None, pre_parameter_change_hook_result.rejection)

    def test_pre_parameter_change_hook_result_raises_with_invalid_rejection_type(self):
        with self.assertRaises(StrongTypingError) as ex:
            PreParameterChangeHookResult(rejection=True)
        self.assertEqual(
            "'rejection' expected Rejection if populated, got 'True' of type bool",
            str(ex.exception),
        )


class TestPostParameterChangeHookResult(HookResultTestBase):
    def test_post_parameter_change_hook_result_without_directives(self):
        post_parameter_change_hook_result = PostParameterChangeHookResult()
        self.assertEqual([], post_parameter_change_hook_result.account_notification_directives)
        self.assertEqual([], post_parameter_change_hook_result.posting_instructions_directives)
        self.assertEqual([], post_parameter_change_hook_result.update_account_event_type_directives)

    def test_post_parameter_change_hook_result_with_directives(self):
        account_notification_directives = [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        posting_instructions_directives = self.test_posting_instructions_directives
        update_account_event_type_directives = [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
        post_parameter_change_hook_result = PostParameterChangeHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=update_account_event_type_directives,
        )
        self.assertEqual(
            account_notification_directives,
            post_parameter_change_hook_result.account_notification_directives,
        )
        self.assertEqual(
            posting_instructions_directives,
            post_parameter_change_hook_result.posting_instructions_directives,
        )
        self.assertEqual(
            update_account_event_type_directives,
            post_parameter_change_hook_result.update_account_event_type_directives,
        )

    @patch.object(hook_results, "validate_account_directives")
    def test_post_parameter_change_hook_result_validates_account_directives(
        self, mock_validate_account_directives: Mock
    ):
        PostParameterChangeHookResult(
            account_notification_directives=self.test_account_notification_directives,
            posting_instructions_directives=self.test_posting_instructions_directives,
            update_account_event_type_directives=self.test_update_account_event_type_directives,
        )
        mock_validate_account_directives.assert_called_once_with(
            account_directives=self.test_account_notification_directives,
            posting_directives=self.test_posting_instructions_directives,
            update_events=self.test_update_account_event_type_directives,
        )

    def test_post_parameter_change_hook_result_repr(self):
        account_notification_directives = [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        posting_instructions_directives = self.test_posting_instructions_directives
        update_account_event_type_directives = [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
        post_parameter_change_hook_result = PostParameterChangeHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=update_account_event_type_directives,
        )
        expected = (
            f"PostParameterChangeHookResult(account_notification_directives={repr(account_notification_directives)}, "
            f"posting_instructions_directives={repr(posting_instructions_directives)}, "
            f"update_account_event_type_directives={repr(update_account_event_type_directives)})"
        )
        self.assertEqual(expected, repr(post_parameter_change_hook_result))

    def test_post_parameter_change_hook_result_equality(self):
        account_notification_directives = [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        posting_instructions_directives = self.test_posting_instructions_directives
        update_account_event_type_directives = [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
        post_parameter_change_hook_result = PostParameterChangeHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=update_account_event_type_directives,
        )
        other_post_parameter_change_hook_result = PostParameterChangeHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=update_account_event_type_directives,
        )

        self.assertEqual(post_parameter_change_hook_result, other_post_parameter_change_hook_result)

    def test_post_parameter_change_hook_result_unequal_update_account_event_type_directives(self):
        account_notification_directives = [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        posting_instructions_directives = self.test_posting_instructions_directives
        update_account_event_type_directives = [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
        other_update_account_event_type_directives = [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2042, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
        post_parameter_change_hook_result = PostParameterChangeHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=update_account_event_type_directives,
        )
        other_post_parameter_change_hook_result = PostParameterChangeHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=other_update_account_event_type_directives,
        )

        self.assertNotEqual(
            post_parameter_change_hook_result, other_post_parameter_change_hook_result
        )


class TestPrePostingHookResult(HookResultTestBase):
    def test_pre_posting_hook_result(self):
        rejection = Rejection(message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS)
        pre_posting_hook_result = PrePostingHookResult(rejection=rejection)
        self.assertEqual(rejection, pre_posting_hook_result.rejection)

    def test_pre_posting_hook_result_repr(self):
        rejection = Rejection(message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS)
        pre_posting_hook_result = PrePostingHookResult(rejection=rejection)
        expected = (
            "PrePostingHookResult(rejection=Rejection(message='Rejection', "
            + "reason_code=RejectionReason.INSUFFICIENT_FUNDS))"
        )
        if is_fflag_enabled(ENRICH_POSTING_INSTRUCTIONS):
            expected = (
                "PrePostingHookResult(rejection=Rejection(message='Rejection', "
                + "reason_code=RejectionReason.INSUFFICIENT_FUNDS), "
                + "enrichment_details=None)"
            )
        self.assertEqual(expected, repr(pre_posting_hook_result))

    def test_pre_posting_hook_result_equality(self):
        rejection = Rejection(message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS)
        pre_posting_hook_result = PrePostingHookResult(rejection=rejection)
        other_rejection = Rejection(
            message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS
        )
        other_pre_posting_hook_result = PrePostingHookResult(rejection=other_rejection)

        self.assertEqual(pre_posting_hook_result, other_pre_posting_hook_result)

    def test_pre_posting_hook_result_unequal_rejection(self):
        rejection = Rejection(message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS)
        pre_posting_hook_result = PrePostingHookResult(rejection=rejection)
        other_rejection = Rejection(
            message="Rejection", reason_code=RejectionReason.WRONG_DENOMINATION
        )
        other_pre_posting_hook_result = PrePostingHookResult(rejection=other_rejection)

        self.assertNotEqual(pre_posting_hook_result, other_pre_posting_hook_result)

    def test_pre_posting_hook_result_with_no_rejection(self):
        pre_posting_hook_result = PrePostingHookResult()
        self.assertEqual(None, pre_posting_hook_result.rejection)

    def test_pre_posting_hook_skips_validation(self):
        pre_posting_hook_result = PrePostingHookResult(rejection=True, _from_proto=True)
        self.assertEqual(True, pre_posting_hook_result.rejection)

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_pre_posting_hook_result_with_enrichment_details_with_no_rejection(self):
        enrichment_details = {
            "pi_id_1": PostingInstructionEnrichment(details={"1": "a", "2": "b"}),
            "pi_id_2": PostingInstructionEnrichment(details={"3": "c", "4": "d"}),
        }
        pre_posting_hook_result = PrePostingHookResult(enrichment_details=enrichment_details)
        self.assertEqual(None, pre_posting_hook_result.rejection)
        self.assertEqual(enrichment_details, pre_posting_hook_result.enrichment_details)

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_pre_posting_hook_result_with_enrichment_details_with_rejection(self):
        rejection = Rejection(message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS)
        enrichment_details = {
            "pi_id_1": PostingInstructionEnrichment(details={"1": "a", "2": "b"}),
            "pi_id_2": PostingInstructionEnrichment(details={"3": "c", "4": "d"}),
        }
        pre_posting_hook_result = PrePostingHookResult(
            rejection=rejection, enrichment_details=enrichment_details
        )
        self.assertEqual(rejection, pre_posting_hook_result.rejection)
        self.assertEqual(enrichment_details, pre_posting_hook_result.enrichment_details)

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_pre_posting_hook_result_with_enrichment_details_none(self):
        pre_posting_hook_result = PrePostingHookResult(enrichment_details=None)
        self.assertEqual(None, pre_posting_hook_result.enrichment_details)

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_pre_posting_hook_result_with_enrichment_details_equality(self):
        enrichment_details = {
            "pi_id_1": PostingInstructionEnrichment(details={"1": "a", "2": "b"}),
            "pi_id_2": PostingInstructionEnrichment(details={"3": "c", "4": "d"}),
        }
        pre_posting_hook_result = PrePostingHookResult(enrichment_details=enrichment_details)
        other_enrichment_details = {
            "pi_id_1": PostingInstructionEnrichment(details={"1": "a", "2": "b"}),
            "pi_id_2": PostingInstructionEnrichment(details={"3": "c", "4": "d"}),
        }
        other_pre_posting_hook_result = PrePostingHookResult(
            enrichment_details=other_enrichment_details
        )
        self.assertEqual(enrichment_details, other_enrichment_details)
        self.assertEqual(pre_posting_hook_result, other_pre_posting_hook_result)

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_pre_posting_hook_result_with_enrichment_details_unequal(self):
        enrichment_details = {
            "pi_id_1": PostingInstructionEnrichment(details={"1": "a", "2": "b"}),
            "pi_id_2": PostingInstructionEnrichment(details={"3": "c", "4": "d"}),
        }
        pre_posting_hook_result = PrePostingHookResult(enrichment_details=enrichment_details)
        other_enrichment_details = {
            "pi_id_3": PostingInstructionEnrichment(details={"1": "a", "2": "b"}),
            "pi_id_4": PostingInstructionEnrichment(details={"3": "c", "4": "d"}),
        }
        other_pre_posting_hook_result = PrePostingHookResult(
            enrichment_details=other_enrichment_details
        )
        self.assertNotEqual(enrichment_details, other_enrichment_details)
        self.assertNotEqual(pre_posting_hook_result, other_pre_posting_hook_result)

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_pre_posting_hook_result_with_enrichment_details_wrong_type_raises(self):
        enrichment_details = "PostingInstructionEnrichment"
        with self.assertRaises(StrongTypingError) as ex:
            PrePostingHookResult(enrichment_details=enrichment_details)
        self.assertEqual(
            "'enrichment_details' expected dict[str, PostingInstructionEnrichment] if populated, got 'PostingInstructionEnrichment' of type str",
            str(ex.exception),
        )

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_pre_posting_hook_result_with_enrichment_details_wrong_type_key_raises(self):
        enrichment_details = {
            123: PostingInstructionEnrichment(details={"1": "a", "2": "b"}),
        }
        with self.assertRaises(StrongTypingError) as ex:
            PrePostingHookResult(enrichment_details=enrichment_details)
        self.assertEqual(
            "'enrichment_details.key' expected str, got '123' of type int",
            str(ex.exception),
        )

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_pre_posting_hook_result_with_enrichment_details_wrong_type_value_raises(self):
        enrichment_details = {
            "pi_id": 123,
        }
        with self.assertRaises(StrongTypingError) as ex:
            PrePostingHookResult(enrichment_details=enrichment_details)
        self.assertEqual(
            "'enrichment_details.value' expected PostingInstructionEnrichment, got '123' of type int",
            str(ex.exception),
        )


class TestPostPostingHookResult(HookResultTestBase):
    def test_post_posting_hook_result_without_directives(self):
        post_posting_hook_result = PostPostingHookResult()
        self.assertEqual([], post_posting_hook_result.account_notification_directives)
        self.assertEqual([], post_posting_hook_result.posting_instructions_directives)
        self.assertEqual([], post_posting_hook_result.update_account_event_type_directives)

    def test_post_posting_hook_result_with_directives(self):
        account_notification_directives = [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        posting_instructions_directives = self.test_posting_instructions_directives
        update_account_event_type_directives = [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
        post_posting_hook_result = PostPostingHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=update_account_event_type_directives,
        )
        self.assertEqual(
            account_notification_directives,
            post_posting_hook_result.account_notification_directives,
        )
        self.assertEqual(
            posting_instructions_directives,
            post_posting_hook_result.posting_instructions_directives,
        )
        self.assertEqual(
            update_account_event_type_directives,
            post_posting_hook_result.update_account_event_type_directives,
        )

    @patch.object(hook_results, "validate_account_directives")
    def test_post_posting_hook_result_validates_account_directives(
        self, mock_validate_account_directives: Mock
    ):
        PostPostingHookResult(
            account_notification_directives=self.test_account_notification_directives,
            posting_instructions_directives=self.test_posting_instructions_directives,
            update_account_event_type_directives=self.test_update_account_event_type_directives,
        )
        mock_validate_account_directives.assert_called_once_with(
            account_directives=self.test_account_notification_directives,
            posting_directives=self.test_posting_instructions_directives,
            update_events=self.test_update_account_event_type_directives,
        )

    def test_post_posting_hook_result_repr(self):
        account_notification_directives = [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        posting_instructions_directives = self.test_posting_instructions_directives
        update_account_event_type_directives = [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
        post_posting_hook_result = PostPostingHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=update_account_event_type_directives,
        )
        expected = (
            f"PostPostingHookResult(account_notification_directives={repr(account_notification_directives)}, "
            f"posting_instructions_directives={repr(posting_instructions_directives)}, "
            f"update_account_event_type_directives={repr(update_account_event_type_directives)})"
        )
        self.assertEqual(expected, repr(post_posting_hook_result))

    def test_post_posting_hook_result_equality(self):
        account_notification_directives = [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        posting_instructions_directives = self.test_posting_instructions_directives
        update_account_event_type_directives = [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
        post_posting_hook_result = PostPostingHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=update_account_event_type_directives,
        )
        other_post_posting_hook_result = PostPostingHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=update_account_event_type_directives,
        )

        self.assertEqual(
            post_posting_hook_result,
            other_post_posting_hook_result,
        )

    def test_post_posting_hook_result_unequal_update_account_event_type_directives(self):
        account_notification_directives = [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        posting_instructions_directives = self.test_posting_instructions_directives
        update_account_event_type_directives = [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
        other_update_account_event_type_directives = [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2042, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
        post_posting_hook_result = PostPostingHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=update_account_event_type_directives,
        )
        other_post_posting_hook_result = PostPostingHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=other_update_account_event_type_directives,
        )

        self.assertNotEqual(
            post_posting_hook_result,
            other_post_posting_hook_result,
        )

    def test_post_posting_hook_result_from_proto_skips_validation(self):
        post_posting_hook_result = PostPostingHookResult(
            update_account_event_type_directives=True, _from_proto=True
        )
        self.assertEqual(True, post_posting_hook_result.update_account_event_type_directives)


class TestScheduledEventHookResult(HookResultTestBase):
    def test_scheduled_event_hook_result_without_directives(self):
        scheduled_event_hook_result = ScheduledEventHookResult()
        self.assertEqual([], scheduled_event_hook_result.account_notification_directives)
        self.assertEqual([], scheduled_event_hook_result.posting_instructions_directives)
        self.assertEqual([], scheduled_event_hook_result.update_account_event_type_directives)

    def test_scheduled_event_hook_result_with_directives(self):
        account_notification_directives = [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        posting_instructions_directives = self.test_posting_instructions_directives
        update_account_event_type_directives = [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
        scheduled_event_hook_result = ScheduledEventHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=update_account_event_type_directives,
        )
        self.assertEqual(
            account_notification_directives,
            scheduled_event_hook_result.account_notification_directives,
        )
        self.assertEqual(
            posting_instructions_directives,
            scheduled_event_hook_result.posting_instructions_directives,
        )
        self.assertEqual(
            update_account_event_type_directives,
            scheduled_event_hook_result.update_account_event_type_directives,
        )

    @patch.object(hook_results, "validate_account_directives")
    def test_scheduled_event_hook_result_validates_account_directives(
        self, mock_validate_account_directives: Mock
    ):
        ScheduledEventHookResult(
            account_notification_directives=self.test_account_notification_directives,
            posting_instructions_directives=self.test_posting_instructions_directives,
            update_account_event_type_directives=self.test_update_account_event_type_directives,
        )
        mock_validate_account_directives.assert_called_once_with(
            account_directives=self.test_account_notification_directives,
            posting_directives=self.test_posting_instructions_directives,
            update_events=self.test_update_account_event_type_directives,
            is_scheduled_event_hook=True,
        )

    def test_scheduled_event_hook_result_repr(self):
        account_notification_directives = [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        posting_instructions_directives = self.test_posting_instructions_directives
        update_account_event_type_directives = [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
        scheduled_event_hook_result = ScheduledEventHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=update_account_event_type_directives,
        )
        expected = (
            f"ScheduledEventHookResult(account_notification_directives={repr(account_notification_directives)}, "
            f"posting_instructions_directives={repr(posting_instructions_directives)}, "
            f"update_account_event_type_directives={repr(update_account_event_type_directives)})"
        )
        self.assertEqual(expected, repr(scheduled_event_hook_result))

    def test_scheduled_event_hook_result_equality(self):
        account_notification_directives = [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        posting_instructions_directives = self.test_posting_instructions_directives
        update_account_event_type_directives = [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
        scheduled_event_hook_result = ScheduledEventHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=update_account_event_type_directives,
        )
        other_scheduled_event_hook_result = ScheduledEventHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=update_account_event_type_directives,
        )

        self.assertEqual(
            scheduled_event_hook_result,
            other_scheduled_event_hook_result,
        )

    def test_scheduled_event_hook_result_unequal_update_account_event_type_directives(self):
        account_notification_directives = [
            AccountNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        posting_instructions_directives = self.test_posting_instructions_directives
        update_account_event_type_directives = [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
        other_update_account_event_type_directives = [
            UpdateAccountEventTypeDirective(
                event_type="event_type_1",
                end_datetime=datetime(2042, 3, 27, tzinfo=ZoneInfo("UTC")),
            )
        ]
        scheduled_event_hook_result = ScheduledEventHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=update_account_event_type_directives,
        )
        other_scheduled_event_hook_result = ScheduledEventHookResult(
            account_notification_directives=account_notification_directives,
            posting_instructions_directives=posting_instructions_directives,
            update_account_event_type_directives=other_update_account_event_type_directives,
        )

        self.assertNotEqual(
            scheduled_event_hook_result,
            other_scheduled_event_hook_result,
        )

    def test_scheduled_event_hook_result_from_proto_skips_validation(self):
        scheduled_event_hook_result = ScheduledEventHookResult(
            update_account_event_type_directives=True, _from_proto=True
        )
        self.assertEqual(True, scheduled_event_hook_result.update_account_event_type_directives)


# Supervisor Hook Results


class TestSupervisorActivationHookResult(HookResultTestBase):
    def test_supervisor_activation_hook_result(self):
        supervisor_activation_hook_result = SupervisorActivationHookResult(
            scheduled_events_return_value=self.test_scheduled_events_return_value
        )
        self.assertEqual(
            self.test_scheduled_events_return_value,
            supervisor_activation_hook_result.scheduled_events_return_value,
        )
        self.assertIsNone(supervisor_activation_hook_result.rejection)

    def test_supervisor_activation_hook_result_repr(self):
        supervisor_activation_hook_result = SupervisorActivationHookResult(
            scheduled_events_return_value=self.test_scheduled_events_return_value
        )
        expected = (
            "SupervisorActivationHookResult(scheduled_events_return_value={'event_1': "
            + "ScheduledEvent(start_datetime=datetime.datetime(1970, 1, 1, 0, 0, 1, "
            + "tzinfo=zoneinfo.ZoneInfo(key='UTC')), "
            + "end_datetime=datetime.datetime(1970, 1, 1, 0, 0, 2, "
            + "tzinfo=zoneinfo.ZoneInfo(key='UTC')), expression=ScheduleExpression(second='0', "
            + "minute='0', hour='0', day='1', month='1', day_of_week=None, year='2000'), "
            + "schedule_method=None, skip=ScheduleSkip(end=datetime.datetime(1970, 1, 1, 0, 0, 3, "
            + "tzinfo=zoneinfo.ZoneInfo(key='UTC')))), 'event_2': "
            + "ScheduledEvent(start_datetime=datetime.datetime(1970, 1, 1, 0, 0, 5, "
            + "tzinfo=zoneinfo.ZoneInfo(key='UTC')), "
            + "end_datetime=datetime.datetime(1970, 1, 1, 0, 0, 6, "
            + "tzinfo=zoneinfo.ZoneInfo(key='UTC')), expression="
            + "ScheduleExpression(second=None, minute=None, hour=None, day=None, "
            + "month=None, day_of_week='mon', year=None), schedule_method=None, skip=False)}, "
            + "rejection=None)"
        )
        self.assertEqual(expected, repr(supervisor_activation_hook_result))

    def test_supervisor_activation_hook_result_equality(self):
        supervisor_activation_hook_result = SupervisorActivationHookResult(
            scheduled_events_return_value=self.test_scheduled_events_return_value
        )
        other_scheduled_events_return_value = {
            "event_1": ScheduledEvent(
                start_datetime=datetime(1970, 1, 1, second=1, tzinfo=ZoneInfo("UTC")),
                end_datetime=datetime(1970, 1, 1, second=2, tzinfo=ZoneInfo("UTC")),
                expression=ScheduleExpression(
                    year="2000",
                    month="1",
                    day="1",
                    hour="0",
                    minute="0",
                    second="0",
                ),
                skip=ScheduleSkip(
                    end=datetime(1970, 1, 1, second=3, tzinfo=ZoneInfo("UTC")),
                ),
            ),
            "event_2": ScheduledEvent(
                start_datetime=datetime(1970, 1, 1, second=5, tzinfo=ZoneInfo("UTC")),
                end_datetime=datetime(1970, 1, 1, second=6, tzinfo=ZoneInfo("UTC")),
                expression=ScheduleExpression(
                    day_of_week="mon",
                ),
            ),
        }
        other_supervisor_activation_hook_result = SupervisorActivationHookResult(
            scheduled_events_return_value=other_scheduled_events_return_value
        )

        self.assertEqual(
            supervisor_activation_hook_result,
            other_supervisor_activation_hook_result,
        )

    def test_supervisor_activation_hook_result_unequal_scheduled_events_return_value(self):
        supervisor_activation_hook_result = SupervisorActivationHookResult(
            scheduled_events_return_value=self.test_scheduled_events_return_value
        )
        other_scheduled_events_return_value = {
            "event_1": ScheduledEvent(
                start_datetime=datetime(1970, 1, 1, second=1, tzinfo=ZoneInfo("UTC")),
                end_datetime=datetime(1970, 1, 1, second=2, tzinfo=ZoneInfo("UTC")),
                expression=ScheduleExpression(
                    year="2000",
                    month="1",
                    day="1",
                    hour="0",
                    minute="0",
                    second="0",
                ),
                skip=ScheduleSkip(
                    end=datetime(1970, 1, 1, second=5, tzinfo=ZoneInfo("UTC")),
                ),
            ),
            "event_2": ScheduledEvent(
                start_datetime=datetime(1970, 1, 1, second=5, tzinfo=ZoneInfo("UTC")),
                end_datetime=datetime(1970, 1, 1, second=6, tzinfo=ZoneInfo("UTC")),
                expression=ScheduleExpression(
                    day_of_week="mon",
                ),
            ),
        }
        other_supervisor_activation_hook_result = SupervisorActivationHookResult(
            scheduled_events_return_value=other_scheduled_events_return_value
        )

        self.assertNotEqual(
            supervisor_activation_hook_result,
            other_supervisor_activation_hook_result,
        )

    @patch.object(hook_results, "validate_rejection_exclusivity")
    def test_supervisor_activation_hook_result_validates_rejection_is_not_returned_with_directives_or_return_values(
        self, mock_validate_rejection_exclusivity: Mock
    ):
        SupervisorActivationHookResult(
            scheduled_events_return_value=self.test_scheduled_events_return_value,
            rejection=self.test_rejection,
        )
        mock_validate_rejection_exclusivity.assert_called_once_with(
            class_name="SupervisorActivationHookResult",
            rejection=self.test_rejection,
            scheduled_events_return_value=self.test_scheduled_events_return_value,
        )

    def test_supervisor_activation_hook_result_raises_with_invalid_rejection(self):
        with self.assertRaises(StrongTypingError) as ex:
            SupervisorActivationHookResult(rejection=27)
        self.assertEqual(
            "'rejection' expected Rejection if populated, got '27' of type int", str(ex.exception)
        )

    def test_supervisor_activation_hook_result_no_events(self):
        supervisor_activation_hook_result = SupervisorActivationHookResult()
        self.assertEqual({}, supervisor_activation_hook_result.scheduled_events_return_value)
        self.assertIsNone(supervisor_activation_hook_result.rejection)


class TestSupervisorConversionHookResult(HookResultTestBase):
    def test_supervisor_conversion_hook_result(self):
        supervisor_conversion_hook_result = SupervisorConversionHookResult(
            scheduled_events_return_value=self.test_scheduled_events_return_value
        )
        self.assertEqual(
            self.test_scheduled_events_return_value,
            supervisor_conversion_hook_result.scheduled_events_return_value,
        )
        self.assertIsNone(supervisor_conversion_hook_result.rejection)

    def test_supervisor_conversion_hook_result_no_events(self):
        supervisor_conversion_hook_result = SupervisorConversionHookResult()
        self.assertEqual({}, supervisor_conversion_hook_result.scheduled_events_return_value)
        self.assertIsNone(supervisor_conversion_hook_result.rejection)

    def test_supervisor_conversion_hook_result_with_rejection_attribute(self):
        rejection = Rejection(message="Bank of Joel is not open today")
        supervisor_conversion_hook_result = SupervisorConversionHookResult(rejection=rejection)
        self.assertEqual(rejection, supervisor_conversion_hook_result.rejection)
        self.assertEqual({}, supervisor_conversion_hook_result.scheduled_events_return_value)

    def test_supervisor_conversion_hook_result_repr(self):
        rejection = Rejection(message="Nope. You cannot do that!")
        supervisor_conversion_hook_result = SupervisorConversionHookResult(rejection=rejection)
        expected = (
            "SupervisorConversionHookResult(scheduled_events_return_value={}, "
            + "rejection=Rejection(message='Nope. You cannot do that!', reason_code=None))"
        )
        self.assertEqual(expected, repr(supervisor_conversion_hook_result))

    def test_supervisor_conversion_hook_result_equality(self):
        rejection = Rejection(message="Bank of Joel is not open today")
        supervisor_conversion_hook_result = SupervisorConversionHookResult(rejection=rejection)
        other_rejection = Rejection(message="Bank of Joel is not open today")
        other_supervisor_conversion_hook_result = SupervisorConversionHookResult(
            rejection=other_rejection
        )

        self.assertEqual(supervisor_conversion_hook_result, other_supervisor_conversion_hook_result)

    def test_supervisor_conversion_hook_result_unequal_rejection(self):
        rejection = Rejection(message="Bank of Joel is not open today")
        supervisor_conversion_hook_result = SupervisorConversionHookResult(rejection=rejection)
        other_rejection = Rejection(message="Bank of Marianne is not open today")
        other_supervisor_conversion_hook_result = SupervisorConversionHookResult(
            rejection=other_rejection
        )

        self.assertNotEqual(
            supervisor_conversion_hook_result, other_supervisor_conversion_hook_result
        )

    @patch.object(hook_results, "validate_rejection_exclusivity")
    def test_supervisor_conversion_hook_result_validates_rejection_is_not_returned_with_directives_or_return_values(
        self, mock_validate_rejection_exclusivity: Mock
    ):
        SupervisorConversionHookResult(
            scheduled_events_return_value=self.test_scheduled_events_return_value,
            rejection=self.test_rejection,
        )
        mock_validate_rejection_exclusivity.assert_called_once_with(
            class_name="SupervisorConversionHookResult",
            rejection=self.test_rejection,
            scheduled_events_return_value=self.test_scheduled_events_return_value,
        )

    def test_supervisor_conversion_hook_result_raises_with_invalid_rejection_type(self):
        with self.assertRaises(StrongTypingError) as e:
            SupervisorConversionHookResult(rejection=42)
        self.assertEqual(
            "'rejection' expected Rejection if populated, got '42' of type int",
            str(e.exception),
        )


class TestSupervisorPrePostingHookResult(HookResultTestBase):
    def test_supervisor_pre_posting_hook_result(self):
        rejection = Rejection(message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS)
        supervisor_pre_posting_hook_result = SupervisorPrePostingHookResult(rejection=rejection)
        self.assertEqual(rejection, supervisor_pre_posting_hook_result.rejection)

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_supervisor_pre_posting_hook_result_with_enrichment(self):
        enrichment_1 = PostingInstructionEnrichment(details={"a1": "11", "b1": "12"})
        enrichment_2 = PostingInstructionEnrichment(details={"a2": "21", "b2": "22"})
        enrichment_details = {
            "account_id_1": {"instruction_id_1": enrichment_1},
            "account_id_2": {"instruction_id_2": enrichment_2},
        }
        supervisor_pre_posting_hook_result = SupervisorPrePostingHookResult(
            enrichment_details=enrichment_details,
        )
        self.assertEqual(enrichment_details, supervisor_pre_posting_hook_result.enrichment_details)

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_supervisor_pre_posting_hook_result_enrichment_repr(self):
        enrichment_1 = PostingInstructionEnrichment(details={"a": "1"})
        enrichment_2 = PostingInstructionEnrichment(details={"b": "2"})
        enrichment_details = {
            "account_id_1": {"instruction_id_1": enrichment_1},
            "account_id_2": {"instruction_id_2": enrichment_2},
        }
        supervisor_pre_posting_hook_result = SupervisorPrePostingHookResult(
            enrichment_details=enrichment_details,
        )
        expected = (
            "SupervisorPrePostingHookResult(rejection=None, "
            + "enrichment_details={"
            + "'account_id_1': {'instruction_id_1': PostingInstructionEnrichment(details={'a': '1'})}, "
            + "'account_id_2': {'instruction_id_2': PostingInstructionEnrichment(details={'b': '2'})}"
            + "})"
        )
        self.assertEqual(expected, repr(supervisor_pre_posting_hook_result))

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_supervisor_pre_posting_hook_result_equality_enrichment(self):
        enrichment_1 = PostingInstructionEnrichment(details={"a": "1"})
        enrichment_2 = PostingInstructionEnrichment(details={"b": "2"})
        enrichment_details = {
            "account_id_1": {"instruction_id_1": enrichment_1},
            "account_id_2": {"instruction_id_2": enrichment_2},
        }
        supervisor_pre_posting_hook_result = SupervisorPrePostingHookResult(
            enrichment_details=enrichment_details,
        )
        other_enrichment_1 = PostingInstructionEnrichment(details={"a": "1"})
        other_enrichment_2 = PostingInstructionEnrichment(details={"b": "2"})
        other_enrichment_details = {
            "account_id_1": {"instruction_id_1": other_enrichment_1},
            "account_id_2": {"instruction_id_2": other_enrichment_2},
        }
        other_supervisor_pre_posting_hook_result = SupervisorPrePostingHookResult(
            enrichment_details=other_enrichment_details,
        )
        self.assertEqual(
            supervisor_pre_posting_hook_result, other_supervisor_pre_posting_hook_result
        )

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_supervisor_pre_posting_hook_result_unequal_enrichment(self):
        enrichment_1 = PostingInstructionEnrichment(details={"a": "1"})
        enrichment_2 = PostingInstructionEnrichment(details={"b": "2"})
        enrichment_details = {
            "account_id_1": {"instruction_id_1": enrichment_1},
            "account_id_2": {"instruction_id_2": enrichment_2},
        }
        supervisor_pre_posting_hook_result = SupervisorPrePostingHookResult(
            enrichment_details=enrichment_details,
        )
        other_enrichment_1 = PostingInstructionEnrichment(details={"a": "1"})
        other_enrichment_2 = PostingInstructionEnrichment(details={"b": "3"})  # Subtle difference
        other_enrichment_details = {
            "account_id_1": {"instruction_id_1": other_enrichment_1},
            "account_id_2": {"instruction_id_2": other_enrichment_2},
        }
        other_supervisor_pre_posting_hook_result = SupervisorPrePostingHookResult(
            enrichment_details=other_enrichment_details,
        )
        self.assertNotEqual(
            supervisor_pre_posting_hook_result, other_supervisor_pre_posting_hook_result
        )

    @skip_if_not_enabled(ENRICH_POSTING_INSTRUCTIONS)
    def test_supervisor_pre_posting_hook_raises_with_invalid_enrichment_values(self):
        with self.assertRaises(StrongTypingError) as ex:
            SupervisorPrePostingHookResult(enrichment_details=True)
        self.assertEqual(
            "'enrichment_details' expected dict[str, dict[str, PostingInstructionEnrichment]] "
            + "if populated, got 'True' of type bool",
            str(ex.exception),
        )

    def test_supervisor_pre_posting_hook_result_rejection_repr(self):
        rejection = Rejection(message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS)
        supervisor_pre_posting_hook_result = SupervisorPrePostingHookResult(rejection=rejection)
        expected = (
            "SupervisorPrePostingHookResult(rejection=Rejection(message='Rejection', "
            + "reason_code=RejectionReason.INSUFFICIENT_FUNDS), "
            + "enrichment_details=None)"
        )
        self.assertEqual(expected, repr(supervisor_pre_posting_hook_result))

    def test_supervisor_pre_posting_hook_result_equality_rejection(self):
        rejection = Rejection(message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS)
        supervisor_pre_posting_hook_result = SupervisorPrePostingHookResult(rejection=rejection)
        other_rejection = Rejection(
            message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS
        )
        other_supervisor_pre_posting_hook_result = SupervisorPrePostingHookResult(
            rejection=other_rejection
        )

        self.assertEqual(
            supervisor_pre_posting_hook_result, other_supervisor_pre_posting_hook_result
        )

    def test_supervisor_pre_posting_hook_result_unequal_rejection(self):
        rejection = Rejection(message="Rejection", reason_code=RejectionReason.INSUFFICIENT_FUNDS)
        supervisor_pre_posting_hook_result = SupervisorPrePostingHookResult(rejection=rejection)
        other_rejection = Rejection(
            message="Rejection", reason_code=RejectionReason.CLIENT_CUSTOM_REASON
        )
        other_supervisor_pre_posting_hook_result = SupervisorPrePostingHookResult(
            rejection=other_rejection
        )

        self.assertNotEqual(
            supervisor_pre_posting_hook_result, other_supervisor_pre_posting_hook_result
        )

    def test_supervisor_pre_posting_hook_result_with_no_rejection_or_enrichment(self):
        supervisor_pre_posting_hook_result = SupervisorPrePostingHookResult()
        self.assertEqual(None, supervisor_pre_posting_hook_result.rejection)

    def test_supervisor_pre_posting_hook_raises_with_invalid_rejection_values(self):
        with self.assertRaises(StrongTypingError) as ex:
            SupervisorPrePostingHookResult(rejection=True)
        self.assertEqual(
            "'rejection' expected Rejection if populated, got 'True' of type bool",
            str(ex.exception),
        )


class TestSupervisorPostPostingHookResult(HookResultTestBase):
    def test_supervisor_post_posting_hook_result_without_directives(self):
        supervisor_post_posting_hook_result = SupervisorPostPostingHookResult()
        self.assertEqual([], supervisor_post_posting_hook_result.plan_notification_directives)
        self.assertEqual([], supervisor_post_posting_hook_result.update_plan_event_type_directives)

        self.assertEqual(
            {}, supervisor_post_posting_hook_result.supervisee_account_notification_directives
        )
        self.assertEqual(
            {}, supervisor_post_posting_hook_result.supervisee_posting_instructions_directives
        )
        self.assertEqual(
            {}, supervisor_post_posting_hook_result.supervisee_update_account_event_type_directives
        )

    def test_supervisor_post_posting_hook_result_with_directives(self):
        supervisor_post_posting_hook_result = SupervisorPostPostingHookResult(
            plan_notification_directives=self.test_plan_notification_directives,
            update_plan_event_type_directives=self.test_update_plan_event_type_directives,
            supervisee_account_notification_directives=self.test_supervisee_account_notification_directives,
            supervisee_posting_instructions_directives=self.test_supervisee_posting_instructions_directives,
            supervisee_update_account_event_type_directives=self.test_supervisee_update_account_event_type_directives,
        )
        self.assertEqual(
            self.test_plan_notification_directives,
            supervisor_post_posting_hook_result.plan_notification_directives,
        )
        self.assertEqual(
            self.test_update_plan_event_type_directives,
            supervisor_post_posting_hook_result.update_plan_event_type_directives,
        )

        self.assertEqual(
            self.test_supervisee_account_notification_directives,
            supervisor_post_posting_hook_result.supervisee_account_notification_directives,
        )
        self.assertEqual(
            self.test_supervisee_posting_instructions_directives,
            supervisor_post_posting_hook_result.supervisee_posting_instructions_directives,
        )
        self.assertEqual(
            self.test_supervisee_update_account_event_type_directives,
            supervisor_post_posting_hook_result.supervisee_update_account_event_type_directives,
        )

    @patch.object(hook_results, "validate_supervisee_directives")
    def test_supervisor_post_posting_hook_result_validates_account_directives(
        self, mock_validate_supervisee_directives: Mock
    ):
        SupervisorPostPostingHookResult(
            plan_notification_directives=self.test_plan_notification_directives,
            update_plan_event_type_directives=self.test_update_plan_event_type_directives,
            supervisee_account_notification_directives=self.test_supervisee_account_notification_directives,
            supervisee_posting_instructions_directives=self.test_supervisee_posting_instructions_directives,
            supervisee_update_account_event_type_directives=self.test_supervisee_update_account_event_type_directives,
        )
        mock_validate_supervisee_directives.assert_called_once_with(
            self.test_supervisee_account_notification_directives,
            self.test_supervisee_posting_instructions_directives,
            self.test_supervisee_update_account_event_type_directives,
        )

    def test_supervisor_post_posting_hook_result_repr(self):
        plan_notification_directives = [
            PlanNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        update_plan_event_type_directives = [
            UpdatePlanEventTypeDirective(
                event_type="event_type",
                skip=True,
            )
        ]
        supervisee_account_notification_directives = {
            self.test_account_id: [
                AccountNotificationDirective(
                    notification_type="test_notification_type",
                    notification_details={"key1": "value1"},
                )
            ]
        }
        supervisee_posting_instructions_directives = {
            self.test_account_id: self.test_posting_instructions_directives
        }
        supervisee_update_account_event_type_directives = {
            self.test_account_id: [
                UpdateAccountEventTypeDirective(
                    event_type="event_type_1",
                    end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
                )
            ]
        }

        supervisor_post_posting_hook_result = SupervisorPostPostingHookResult(
            plan_notification_directives=plan_notification_directives,
            update_plan_event_type_directives=update_plan_event_type_directives,
            supervisee_account_notification_directives=supervisee_account_notification_directives,
            supervisee_posting_instructions_directives=supervisee_posting_instructions_directives,
            supervisee_update_account_event_type_directives=supervisee_update_account_event_type_directives,
        )
        expected = (
            f"SupervisorPostPostingHookResult(plan_notification_directives={repr(plan_notification_directives)}, "
            f"update_plan_event_type_directives={repr(update_plan_event_type_directives)}, "
            f"supervisee_account_notification_directives={repr(supervisee_account_notification_directives)}, "
            f"supervisee_posting_instructions_directives={repr(supervisee_posting_instructions_directives)}, "
            f"supervisee_update_account_event_type_directives={repr(supervisee_update_account_event_type_directives)})"
        )
        self.assertEqual(expected, repr(supervisor_post_posting_hook_result))

    def test_supervisor_post_posting_hook_result_equality(self):
        plan_notification_directives = [
            PlanNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        update_plan_event_type_directives = [
            UpdatePlanEventTypeDirective(
                event_type="event_type",
                skip=True,
            )
        ]
        supervisee_account_notification_directives = {
            self.test_account_id: [
                AccountNotificationDirective(
                    notification_type="test_notification_type",
                    notification_details={"key1": "value1"},
                )
            ]
        }
        supervisee_posting_instructions_directives = {
            self.test_account_id: self.test_posting_instructions_directives
        }
        supervisee_update_account_event_type_directives = {
            self.test_account_id: [
                UpdateAccountEventTypeDirective(
                    event_type="event_type_1",
                    end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
                )
            ]
        }

        supervisor_post_posting_hook_result = SupervisorPostPostingHookResult(
            plan_notification_directives=plan_notification_directives,
            update_plan_event_type_directives=update_plan_event_type_directives,
            supervisee_account_notification_directives=supervisee_account_notification_directives,
            supervisee_posting_instructions_directives=supervisee_posting_instructions_directives,
            supervisee_update_account_event_type_directives=supervisee_update_account_event_type_directives,
        )
        other_supervisor_post_posting_hook_result = SupervisorPostPostingHookResult(
            plan_notification_directives=plan_notification_directives,
            update_plan_event_type_directives=update_plan_event_type_directives,
            supervisee_account_notification_directives=supervisee_account_notification_directives,
            supervisee_posting_instructions_directives=supervisee_posting_instructions_directives,
            supervisee_update_account_event_type_directives=supervisee_update_account_event_type_directives,
        )

        self.assertEqual(
            supervisor_post_posting_hook_result,
            other_supervisor_post_posting_hook_result,
        )

    def test_supervisor_post_posting_hook_result_unequal_supervisee_update_account_event_type_directives(
        self,
    ):
        plan_notification_directives = [
            PlanNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        update_plan_event_type_directives = [
            UpdatePlanEventTypeDirective(
                event_type="event_type",
                skip=True,
            )
        ]
        supervisee_account_notification_directives = {
            self.test_account_id: [
                AccountNotificationDirective(
                    notification_type="test_notification_type",
                    notification_details={"key1": "value1"},
                )
            ]
        }
        supervisee_posting_instructions_directives = {
            self.test_account_id: self.test_posting_instructions_directives
        }
        supervisee_update_account_event_type_directives = {
            self.test_account_id: [
                UpdateAccountEventTypeDirective(
                    event_type="event_type_1",
                    end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
                )
            ]
        }
        other_supervisee_update_account_event_type_directives = {
            self.test_account_id: [
                UpdateAccountEventTypeDirective(
                    event_type="event_type_42",
                    end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
                )
            ]
        }

        supervisor_post_posting_hook_result = SupervisorPostPostingHookResult(
            plan_notification_directives=plan_notification_directives,
            update_plan_event_type_directives=update_plan_event_type_directives,
            supervisee_account_notification_directives=supervisee_account_notification_directives,
            supervisee_posting_instructions_directives=supervisee_posting_instructions_directives,
            supervisee_update_account_event_type_directives=supervisee_update_account_event_type_directives,
        )
        other_supervisor_post_posting_hook_result = SupervisorPostPostingHookResult(
            plan_notification_directives=plan_notification_directives,
            update_plan_event_type_directives=update_plan_event_type_directives,
            supervisee_account_notification_directives=supervisee_account_notification_directives,
            supervisee_posting_instructions_directives=supervisee_posting_instructions_directives,
            supervisee_update_account_event_type_directives=other_supervisee_update_account_event_type_directives,
        )

        self.assertNotEqual(
            supervisor_post_posting_hook_result,
            other_supervisor_post_posting_hook_result,
        )


class TestSupervisorScheduledEventHookResult(HookResultTestBase):
    def test_supervisor_scheduled_event_hook_result_without_directives(self):
        supervisor_scheduled_event_hook_result = SupervisorScheduledEventHookResult()
        self.assertEqual([], supervisor_scheduled_event_hook_result.plan_notification_directives)
        self.assertEqual(
            [], supervisor_scheduled_event_hook_result.update_plan_event_type_directives
        )

        self.assertEqual(
            {}, supervisor_scheduled_event_hook_result.supervisee_account_notification_directives
        )
        self.assertEqual(
            {}, supervisor_scheduled_event_hook_result.supervisee_posting_instructions_directives
        )
        self.assertEqual(
            {},
            supervisor_scheduled_event_hook_result.supervisee_update_account_event_type_directives,
        )

    def test_supervisor_scheduled_event_hook_result_with_directives(self):
        supervisor_scheduled_event_hook_result = SupervisorScheduledEventHookResult(
            plan_notification_directives=self.test_plan_notification_directives,
            update_plan_event_type_directives=self.test_update_plan_event_type_directives,
            supervisee_account_notification_directives=self.test_supervisee_account_notification_directives,
            supervisee_posting_instructions_directives=self.test_supervisee_posting_instructions_directives,
            supervisee_update_account_event_type_directives=self.test_supervisee_update_account_event_type_directives,
        )
        self.assertEqual(
            self.test_plan_notification_directives,
            supervisor_scheduled_event_hook_result.plan_notification_directives,
        )
        self.assertEqual(
            self.test_update_plan_event_type_directives,
            supervisor_scheduled_event_hook_result.update_plan_event_type_directives,
        )

        self.assertEqual(
            self.test_supervisee_account_notification_directives,
            supervisor_scheduled_event_hook_result.supervisee_account_notification_directives,
        )
        self.assertEqual(
            self.test_supervisee_posting_instructions_directives,
            supervisor_scheduled_event_hook_result.supervisee_posting_instructions_directives,
        )
        self.assertEqual(
            self.test_supervisee_update_account_event_type_directives,
            supervisor_scheduled_event_hook_result.supervisee_update_account_event_type_directives,
        )

    @patch.object(hook_results, "validate_supervisee_directives")
    def test_supervisor_scheduled_event_hook_result_validates_account_directives(
        self, mock_validate_supervisee_directives: Mock
    ):
        SupervisorScheduledEventHookResult(
            plan_notification_directives=self.test_plan_notification_directives,
            update_plan_event_type_directives=self.test_update_plan_event_type_directives,
            supervisee_account_notification_directives=self.test_supervisee_account_notification_directives,
            supervisee_posting_instructions_directives=self.test_supervisee_posting_instructions_directives,
            supervisee_update_account_event_type_directives=self.test_supervisee_update_account_event_type_directives,
        )
        mock_validate_supervisee_directives.assert_called_once_with(
            self.test_supervisee_account_notification_directives,
            self.test_supervisee_posting_instructions_directives,
            self.test_supervisee_update_account_event_type_directives,
            is_scheduled_event_hook=True,
        )

    def test_supervisor_scheduled_event_hook_result_repr(self):
        plan_notification_directives = [
            PlanNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        update_plan_event_type_directives = [
            UpdatePlanEventTypeDirective(
                event_type="event_type",
                skip=True,
            )
        ]
        supervisee_account_notification_directives = {
            self.test_account_id: [
                AccountNotificationDirective(
                    notification_type="test_notification_type",
                    notification_details={"key1": "value1"},
                )
            ]
        }
        supervisee_posting_instructions_directives = {
            self.test_account_id: self.test_posting_instructions_directives
        }
        supervisee_update_account_event_type_directives = {
            self.test_account_id: [
                UpdateAccountEventTypeDirective(
                    event_type="event_type_1",
                    end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
                )
            ]
        }

        supervisor_scheduled_event_hook_result = SupervisorScheduledEventHookResult(
            plan_notification_directives=plan_notification_directives,
            update_plan_event_type_directives=update_plan_event_type_directives,
            supervisee_account_notification_directives=supervisee_account_notification_directives,
            supervisee_posting_instructions_directives=supervisee_posting_instructions_directives,
            supervisee_update_account_event_type_directives=supervisee_update_account_event_type_directives,
        )
        expected = (
            f"SupervisorScheduledEventHookResult(plan_notification_directives={repr(plan_notification_directives)}, "
            f"update_plan_event_type_directives={repr(update_plan_event_type_directives)}, "
            f"supervisee_account_notification_directives={repr(supervisee_account_notification_directives)}, "
            f"supervisee_posting_instructions_directives={repr(supervisee_posting_instructions_directives)}, "
            f"supervisee_update_account_event_type_directives={repr(supervisee_update_account_event_type_directives)})"
        )
        self.assertEqual(expected, repr(supervisor_scheduled_event_hook_result))

    def test_supervisor_scheduled_event_hook_result_equality(self):
        plan_notification_directives = [
            PlanNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        update_plan_event_type_directives = [
            UpdatePlanEventTypeDirective(
                event_type="event_type",
                skip=True,
            )
        ]
        supervisee_account_notification_directives = {
            self.test_account_id: [
                AccountNotificationDirective(
                    notification_type="test_notification_type",
                    notification_details={"key1": "value1"},
                )
            ]
        }
        supervisee_posting_instructions_directives = {
            self.test_account_id: self.test_posting_instructions_directives
        }
        supervisee_update_account_event_type_directives = {
            self.test_account_id: [
                UpdateAccountEventTypeDirective(
                    event_type="event_type_1",
                    end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
                )
            ]
        }

        supervisor_scheduled_event_hook_result = SupervisorScheduledEventHookResult(
            plan_notification_directives=plan_notification_directives,
            update_plan_event_type_directives=update_plan_event_type_directives,
            supervisee_account_notification_directives=supervisee_account_notification_directives,
            supervisee_posting_instructions_directives=supervisee_posting_instructions_directives,
            supervisee_update_account_event_type_directives=supervisee_update_account_event_type_directives,
        )
        other_supervisor_scheduled_event_hook_result = SupervisorScheduledEventHookResult(
            plan_notification_directives=plan_notification_directives,
            update_plan_event_type_directives=update_plan_event_type_directives,
            supervisee_account_notification_directives=supervisee_account_notification_directives,
            supervisee_posting_instructions_directives=supervisee_posting_instructions_directives,
            supervisee_update_account_event_type_directives=supervisee_update_account_event_type_directives,
        )
        self.assertEqual(
            supervisor_scheduled_event_hook_result,
            other_supervisor_scheduled_event_hook_result,
        )

    def test_supervisor_scheduled_event_hook_result_unequal_supervisee_update_account_event_type_directives(
        self,
    ):
        plan_notification_directives = [
            PlanNotificationDirective(
                notification_type="test_notification_type",
                notification_details={"key1": "value1"},
            )
        ]
        update_plan_event_type_directives = [
            UpdatePlanEventTypeDirective(
                event_type="event_type",
                skip=True,
            )
        ]
        supervisee_account_notification_directives = {
            self.test_account_id: [
                AccountNotificationDirective(
                    notification_type="test_notification_type",
                    notification_details={"key1": "value1"},
                )
            ]
        }
        supervisee_posting_instructions_directives = {
            self.test_account_id: self.test_posting_instructions_directives
        }
        supervisee_update_account_event_type_directives = {
            self.test_account_id: [
                UpdateAccountEventTypeDirective(
                    event_type="event_type_1",
                    end_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
                )
            ]
        }
        other_supervisee_update_account_event_type_directives = {
            self.test_account_id: [
                UpdateAccountEventTypeDirective(
                    event_type="event_type_1",
                    end_datetime=datetime(2042, 3, 27, tzinfo=ZoneInfo("UTC")),
                )
            ]
        }

        supervisor_scheduled_event_hook_result = SupervisorScheduledEventHookResult(
            plan_notification_directives=plan_notification_directives,
            update_plan_event_type_directives=update_plan_event_type_directives,
            supervisee_account_notification_directives=supervisee_account_notification_directives,
            supervisee_posting_instructions_directives=supervisee_posting_instructions_directives,
            supervisee_update_account_event_type_directives=supervisee_update_account_event_type_directives,
        )
        other_supervisor_scheduled_event_hook_result = SupervisorScheduledEventHookResult(
            plan_notification_directives=plan_notification_directives,
            update_plan_event_type_directives=update_plan_event_type_directives,
            supervisee_account_notification_directives=supervisee_account_notification_directives,
            supervisee_posting_instructions_directives=supervisee_posting_instructions_directives,
            supervisee_update_account_event_type_directives=other_supervisee_update_account_event_type_directives,
        )
        self.assertNotEqual(
            supervisor_scheduled_event_hook_result,
            other_supervisor_scheduled_event_hook_result,
        )


# Adjustment Hook Results





class TestConversionAdjustmentHookResult(HookResultTestBase):
    @skip_if_not_enabled(HISTORIC_CONTRACT_RESOLUTION)
    def test_conversion_adjustment_hook_result_without_directives(self):
        conversion_hook_result = ConversionAdjustmentHookResult()
        self.assertEqual([], conversion_hook_result.posting_instructions_directives)

    @skip_if_not_enabled(HISTORIC_CONTRACT_RESOLUTION)
    def test_conversion_adjustment_hook_result_with_directives(self):
        conversion_hook_result = ConversionAdjustmentHookResult(
            posting_instructions_directives=self.test_posting_instructions_directives,
        )
        self.assertEqual(
            self.test_posting_instructions_directives,
            conversion_hook_result.posting_instructions_directives,
        )

    

    @skip_if_not_enabled(HISTORIC_CONTRACT_RESOLUTION)
    def test_conversion_adjustment_hook_result_repr(self):
        self.assertTrue(
            issubclass(ConversionAdjustmentHookResult, ContractsLanguageDunderMixin),
        )
        self.assertIn(
            "ConversionAdjustmentHookResult",
            repr(ConversionAdjustmentHookResult),
        )

    @skip_if_not_enabled(HISTORIC_CONTRACT_RESOLUTION)
    def test_conversion_adjustment_hook_result_equality(self):
        posting_instructions_directives = self.test_posting_instructions_directives

        conversion_hook_result = ConversionAdjustmentHookResult(
            posting_instructions_directives=posting_instructions_directives,
        )
        other_conversion_hook_result = ConversionAdjustmentHookResult(
            posting_instructions_directives=posting_instructions_directives,
        )

        self.assertEqual(
            conversion_hook_result,
            other_conversion_hook_result,
        )

    @skip_if_not_enabled(HISTORIC_CONTRACT_RESOLUTION)
    def test_conversion_adjustment_hook_result_unequal_posting_instructions_directives(
        self,
    ):
        posting_instructions_directives = self.test_posting_instructions_directives
        other_posting_instructions_directives = [
            PostingInstructionsDirective(
                client_batch_id="different-client-batch-id",
                value_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
                posting_instructions=self.test_posting_instructions,
            )
        ]
        conversion_hook_result = ConversionAdjustmentHookResult(
            posting_instructions_directives=posting_instructions_directives,
        )
        other_conversion_hook_result = ConversionAdjustmentHookResult(
            posting_instructions_directives=other_posting_instructions_directives,
        )

        self.assertNotEqual(
            conversion_hook_result,
            other_conversion_hook_result,
        )

    @skip_if_not_enabled(HISTORIC_CONTRACT_RESOLUTION)
    def test_conversion_adjustment_hook_result_from_proto_skips_validation(self):
        conversion_hook_result = ConversionAdjustmentHookResult(
            posting_instructions_directives=True,
            _from_proto=True,
        )
        self.assertTrue(conversion_hook_result.posting_instructions_directives)

    @skip_if_not_enabled(HISTORIC_CONTRACT_RESOLUTION)
    def test_conversion_adjustment_hook_result_spec(self):
        spec = ConversionAdjustmentHookResult._spec(  # noqa: SLF001
            language_code=symbols.Languages.ENGLISH
        )
        self.assertEqual(spec.name, "ConversionAdjustmentHookResult")
        self.assertEqual(spec.docstring, "The hook result of the `conversion_adjustment_hook`.")
        self.assertEqual(spec.public_methods, {})


class TestPostParameterChangeAdjustmentHookResult(HookResultTestBase):
    @skip_if_not_enabled(ADJUSTMENTS)
    def test_post_parameter_change_adjustment_hook_result_without_directives(self):
        post_parameter_change_adjustment_hook_result = PostParameterChangeAdjustmentHookResult()
        self.assertEqual(
            [], post_parameter_change_adjustment_hook_result.posting_instructions_directives
        )

    @skip_if_not_enabled(ADJUSTMENTS)
    def test_post_parameter_change_adjustment_hook_result_with_directives(self):
        post_parameter_change_adjustment_hook_result = PostParameterChangeAdjustmentHookResult(
            posting_instructions_directives=self.test_posting_instructions_directives,
        )
        self.assertEqual(
            self.test_posting_instructions_directives,
            post_parameter_change_adjustment_hook_result.posting_instructions_directives,
        )

    

    @skip_if_not_enabled(ADJUSTMENTS)
    def test_post_parameter_change_adjustment_hook_result_repr(self):
        self.assertTrue(
            issubclass(PostParameterChangeAdjustmentHookResult, ContractsLanguageDunderMixin),
        )
        self.assertIn(
            "PostParameterChangeAdjustmentHookResult",
            repr(PostParameterChangeAdjustmentHookResult),
        )

    @skip_if_not_enabled(ADJUSTMENTS)
    def test_post_parameter_change_adjustment_hook_result_equality(self):
        posting_instructions_directives = self.test_posting_instructions_directives
        post_parameter_change_adjustment_hook_result = PostParameterChangeAdjustmentHookResult(
            posting_instructions_directives=posting_instructions_directives,
        )
        other_post_parameter_change_adjustment_hook_result = (
            PostParameterChangeAdjustmentHookResult(
                posting_instructions_directives=deepcopy(posting_instructions_directives),
            )
        )

        self.assertEqual(
            post_parameter_change_adjustment_hook_result,
            other_post_parameter_change_adjustment_hook_result,
        )

    @skip_if_not_enabled(ADJUSTMENTS)
    def test_post_parameter_change_adjustment_hook_result_unequal_posting_instruction_directives(
        self,
    ):
        posting_instructions_directives = self.test_posting_instructions_directives
        other_posting_instructions_directives = [
            PostingInstructionsDirective(
                client_batch_id="different-client-batch-id",
                value_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
                posting_instructions=self.test_posting_instructions,
            )
        ]

        post_parameter_change_adjustment_hook_result = PostParameterChangeAdjustmentHookResult(
            posting_instructions_directives=posting_instructions_directives,
        )
        other_post_parameter_change_adjustment_hook_result = (
            PostParameterChangeAdjustmentHookResult(
                posting_instructions_directives=other_posting_instructions_directives,
            )
        )

        self.assertNotEqual(
            post_parameter_change_adjustment_hook_result,
            other_post_parameter_change_adjustment_hook_result,
        )


class TestPostPostingAdjustmentHookResult(HookResultTestBase):
    @skip_if_not_enabled(ADJUSTMENTS)
    def test_post_posting_adjustment_hook_result_without_directives(self):
        post_posting_adjustment_hook_result = PostPostingAdjustmentHookResult()
        self.assertEqual([], post_posting_adjustment_hook_result.posting_instructions_directives)

    @skip_if_not_enabled(ADJUSTMENTS)
    def test_post_posting_adjustment_hook_result_with_directives(self):
        post_posting_adjustment_hook_result = PostPostingAdjustmentHookResult(
            posting_instructions_directives=self.test_posting_instructions_directives,
        )
        self.assertEqual(
            self.test_posting_instructions_directives,
            post_posting_adjustment_hook_result.posting_instructions_directives,
        )

    

    @skip_if_not_enabled(ADJUSTMENTS)
    def test_post_posting_adjustment_hook_result_repr(self):
        self.assertTrue(
            issubclass(PostPostingAdjustmentHookResult, ContractsLanguageDunderMixin),
        )
        self.assertIn(
            "PostPostingAdjustmentHookResult",
            repr(PostPostingAdjustmentHookResult),
        )

    @skip_if_not_enabled(ADJUSTMENTS)
    def test_post_posting_adjustment_hook_result_equality(self):
        posting_instructions_directives = self.test_posting_instructions_directives
        post_posting_adjustment_hook_result = PostPostingAdjustmentHookResult(
            posting_instructions_directives=posting_instructions_directives,
        )
        other_post_posting_adjustment_hook_result = PostPostingAdjustmentHookResult(
            posting_instructions_directives=deepcopy(posting_instructions_directives),
        )

        self.assertEqual(
            post_posting_adjustment_hook_result,
            other_post_posting_adjustment_hook_result,
        )

    @skip_if_not_enabled(ADJUSTMENTS)
    def test_post_posting_adjustment_hook_result_unequal_posting_instructions_directives(self):
        posting_instructions_directives = self.test_posting_instructions_directives
        other_posting_instructions_directives = [
            PostingInstructionsDirective(
                client_batch_id="different-client-batch-id",
                value_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
                posting_instructions=self.test_posting_instructions,
            )
        ]
        post_posting_adjustment_hook_result = PostPostingAdjustmentHookResult(
            posting_instructions_directives=posting_instructions_directives,
        )
        other_post_posting_adjustment_hook_result = PostPostingAdjustmentHookResult(
            posting_instructions_directives=other_posting_instructions_directives,
        )

        self.assertNotEqual(
            post_posting_adjustment_hook_result,
            other_post_posting_adjustment_hook_result,
        )

    @skip_if_not_enabled(ADJUSTMENTS)
    def test_post_posting_adjustment_hook_result_from_proto_skips_validation(self):
        post_posting_adjustment_hook_result = PostPostingAdjustmentHookResult(
            posting_instructions_directives=True, _from_proto=True
        )
        self.assertEqual(True, post_posting_adjustment_hook_result.posting_instructions_directives)

        post_posting_adjustment_hook_result = PostPostingAdjustmentHookResult(
            posting_instructions_directives=True, _from_proto=True
        )
        self.assertEqual(True, post_posting_adjustment_hook_result.posting_instructions_directives)


class TestScheduledEventAdjustmentHookResult(HookResultTestBase):
    @skip_if_not_enabled(ADJUSTMENTS)
    def test_scheduled_event_adjustment_hook_result_without_directives(self):
        scheduled_event_hook_result = ScheduledEventAdjustmentHookResult()
        self.assertEqual([], scheduled_event_hook_result.posting_instructions_directives)

    @skip_if_not_enabled(ADJUSTMENTS)
    def test_scheduled_event_adjustment_hook_result_with_directives(self):
        scheduled_event_hook_result = ScheduledEventAdjustmentHookResult(
            posting_instructions_directives=self.test_posting_instructions_directives,
        )
        self.assertEqual(
            self.test_posting_instructions_directives,
            scheduled_event_hook_result.posting_instructions_directives,
        )

    

    @skip_if_not_enabled(ADJUSTMENTS)
    def test_scheduled_event_adjustment_hook_result_repr(self):
        self.assertTrue(
            issubclass(ScheduledEventAdjustmentHookResult, ContractsLanguageDunderMixin),
        )
        self.assertIn(
            "ScheduledEventAdjustmentHookResult",
            repr(ScheduledEventAdjustmentHookResult),
        )

    @skip_if_not_enabled(ADJUSTMENTS)
    def test_scheduled_event_adjustment_hook_result_equality(self):
        posting_instructions_directives = self.test_posting_instructions_directives

        scheduled_event_hook_result = ScheduledEventAdjustmentHookResult(
            posting_instructions_directives=posting_instructions_directives,
        )
        other_scheduled_event_hook_result = ScheduledEventAdjustmentHookResult(
            posting_instructions_directives=posting_instructions_directives,
        )

        self.assertEqual(
            scheduled_event_hook_result,
            other_scheduled_event_hook_result,
        )

    @skip_if_not_enabled(ADJUSTMENTS)
    def test_scheduled_event_adjustment_hook_result_unequal_posting_instructions_directives(
        self,
    ):
        posting_instructions_directives = self.test_posting_instructions_directives
        other_posting_instructions_directives = [
            PostingInstructionsDirective(
                client_batch_id="different-client-batch-id",
                value_datetime=datetime(2022, 3, 27, tzinfo=ZoneInfo("UTC")),
                posting_instructions=self.test_posting_instructions,
            )
        ]
        scheduled_event_hook_result = ScheduledEventAdjustmentHookResult(
            posting_instructions_directives=posting_instructions_directives,
        )
        other_scheduled_event_hook_result = ScheduledEventAdjustmentHookResult(
            posting_instructions_directives=other_posting_instructions_directives,
        )

        self.assertNotEqual(
            scheduled_event_hook_result,
            other_scheduled_event_hook_result,
        )

    @skip_if_not_enabled(ADJUSTMENTS)
    def test_scheduled_event_adjustment_hook_result_from_proto_skips_validation(self):
        scheduled_event_hook_result = ScheduledEventAdjustmentHookResult(
            posting_instructions_directives=True,
            _from_proto=True,
        )
        self.assertTrue(scheduled_event_hook_result.posting_instructions_directives)

    @skip_if_not_enabled(ADJUSTMENTS)
    def test_scheduled_event_adjustment_hook_result_spec(self):
        spec = ScheduledEventAdjustmentHookResult._spec(  # noqa: SLF001
            language_code=symbols.Languages.ENGLISH
        )
        self.assertEqual(spec.name, "ScheduledEventAdjustmentHookResult")
        self.assertEqual(
            spec.docstring, "The hook result of the `scheduled_event_adjustment_hook`."
        )
        self.assertEqual(spec.public_methods, {})








class TestValidateDirectivesHelpers(HookResultTestBase):
    # validate_account_directives

    @skip_if_not_enabled(EXPECTED_PID_REJECTIONS)
    def test_validate_account_directives_raises_with_posting_directive_rejection_reasons_for_non_scheduled_hook(
        self,
    ):
        with self.assertRaises(InvalidSmartContractError) as e:
            validate_account_directives(
                account_directives=[],
                posting_directives=[
                    self.test_posting_instructions_directive_with_rejection_reasons
                ],
            )
        self.assertEqual(
            "PostingInstructionsDirective.non_blocking_rejection_reasons can only be "
            "populated in Scheduled Event Hook Results",
            str(e.exception),
        )

    @skip_if_not_enabled(EXPECTED_PID_REJECTIONS)
    def test_validate_account_directives_allows_posting_directive_rejection_reasons_for_scheduled_hook(
        self,
    ):
        # No error raised.
        validate_account_directives(
            account_directives=[],
            posting_directives=[self.test_posting_instructions_directive_with_rejection_reasons],
            is_scheduled_event_hook=True,
        )

    # validate_supervisee_directives

    @skip_if_not_enabled(EXPECTED_PID_REJECTIONS)
    def test_validate_supervisee_directives_raises_with_posting_directive_rejection_reasons_for_non_scheduled_hook(
        self,
    ):
        with self.assertRaises(InvalidSmartContractError) as e:
            validate_supervisee_directives(
                supervisee_account_directives={},
                supervisee_posting_directives={
                    "account_id_1": [
                        self.test_posting_instructions_directive_with_rejection_reasons
                    ]
                },
                supervisee_update_account_directives={},
            )
        self.assertEqual(
            "PostingInstructionsDirective.non_blocking_rejection_reasons can only be "
            "populated in Scheduled Event Hook Results",
            str(e.exception),
        )

    @skip_if_not_enabled(EXPECTED_PID_REJECTIONS)
    def test_validate_supervisee_directives_allows_posting_directive_rejection_reasons_for_scheduled_hook(
        self,
    ):
        # No error raised.
        validate_supervisee_directives(
            supervisee_account_directives={},
            supervisee_posting_directives={
                "account_id_1": [self.test_posting_instructions_directive_with_rejection_reasons]
            },
            supervisee_update_account_directives={},
            is_scheduled_event_hook=True,
        )

    

    # validate_rejection_exclusivity

    def test_validate_rejection_exclusivity_returns_none_when_all_args_none(
        self,
    ):
        # No error raised.
        validate_rejection_exclusivity(
            class_name="TestingClassName",
            rejection=None,
        )

    def test_validate_rejection_exclusivity_returns_none_when_no_rejection(
        self,
    ):
        # No error raised.
        validate_rejection_exclusivity(
            class_name="TestingClassName",
            rejection=None,
            account_notification_directives=self.test_account_notification_directives,
            posting_instructions_directives=self.test_posting_instructions_directives,
            update_account_event_type_directives=self.test_update_account_event_type_directives,
            scheduled_events_return_value=self.test_scheduled_events_return_value,
        )

    def test_validate_rejection_exclusivity_returns_none_when_just_rejection_and_defaults(
        self,
    ):
        # No error raised.
        validate_rejection_exclusivity(
            class_name="TestingClassName",
            rejection=self.test_rejection,
        )

    def test_validate_rejection_exclusivity_returns_none_when_just_rejection_and_empty_args(
        self,
    ):
        # No error raised.
        validate_rejection_exclusivity(
            class_name="TestingClassName",
            rejection=self.test_rejection,
            account_notification_directives=[],
            posting_instructions_directives=[],
            update_account_event_type_directives=[],
            scheduled_events_return_value={},
        )

    def test_validate_rejection_exclusivity_raises_with_rejection_and_account_notification_directives(
        self,
    ):
        with self.assertRaises(InvalidSmartContractError) as e:
            validate_rejection_exclusivity(
                class_name="TestingClassName",
                rejection=self.test_rejection,
                account_notification_directives=self.test_account_notification_directives,
            )
        self.assertEqual(
            "If `rejection` is populated for TestingClassName, no other attributes can be populated.",
            str(e.exception),
        )

    def test_validate_rejection_exclusivity_raises_with_rejection_and_posting_instructions_directives(
        self,
    ):
        with self.assertRaises(InvalidSmartContractError) as e:
            validate_rejection_exclusivity(
                class_name="TestingClassName",
                rejection=self.test_rejection,
                posting_instructions_directives=self.test_posting_instructions_directives,
            )
        self.assertEqual(
            "If `rejection` is populated for TestingClassName, no other attributes can be populated.",
            str(e.exception),
        )

    def test_validate_rejection_exclusivity_raises_with_rejection_and_update_account_event_type_directives(
        self,
    ):
        with self.assertRaises(InvalidSmartContractError) as e:
            validate_rejection_exclusivity(
                class_name="TestingClassName",
                rejection=self.test_rejection,
                update_account_event_type_directives=self.test_update_account_event_type_directives,
            )
        self.assertEqual(
            "If `rejection` is populated for TestingClassName, no other attributes can be populated.",
            str(e.exception),
        )

    def test_validate_rejection_exclusivity_raises_with_rejection_and_scheduled_events_return_value(
        self,
    ):
        with self.assertRaises(InvalidSmartContractError) as e:
            validate_rejection_exclusivity(
                class_name="TestingClassName",
                rejection=self.test_rejection,
                scheduled_events_return_value=self.test_scheduled_events_return_value,
            )
        self.assertEqual(
            "If `rejection` is populated for TestingClassName, no other attributes can be populated.",
            str(e.exception),
        )
