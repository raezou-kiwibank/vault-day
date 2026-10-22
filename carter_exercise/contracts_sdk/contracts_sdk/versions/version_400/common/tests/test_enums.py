from unittest import TestCase

from ..types import (
    AdjustmentStrategy,
    DateTimeView,
    DefinedDateTime,
    HookName,
    ScheduleFailover,
    SupervisionExecutionMode,
    ParameterLevel,
    Phase,
    ParameterUpdatePermission,
    PostingInstructionRejectionReason,
    PostingInstructionType,
    RejectionReason,
    Timeline,
    Tside,
    
)


class TestEnums(TestCase):
    def test_adjustment_strategy_enum(self):
        self.assertEqual(AdjustmentStrategy.SCHEDULE_TRIGGERED.value, 1)

    def test_defined_datetime_enum(self):
        self.assertEqual(DefinedDateTime.LIVE.value, -1)
        self.assertEqual(DefinedDateTime.INTERVAL_START.value, 2)
        self.assertEqual(DefinedDateTime.EFFECTIVE_DATETIME.value, 3)
        
        with self.assertRaises(AttributeError):
            DefinedDateTime.EFFECTIVE_TIME

    def test_failover_enum(self):
        self.assertEqual(ScheduleFailover.FIRST_VALID_DAY_BEFORE.value, 1)
        self.assertEqual(ScheduleFailover.FIRST_VALID_DAY_AFTER.value, 2)

    def test_fetcher_datetimeview_enum(self):
        self.assertEqual(DateTimeView.VALUE_DATETIME.value, 2)
        self.assertEqual(DateTimeView.BOOKING_DATETIME.value, 3)

    def test_hook_name_enum(self):
        self.assertEqual(HookName.UNKNOWN_HOOK.value, 0)
        self.assertEqual(HookName.ACTIVATION_HOOK.value, 1)
        self.assertEqual(HookName.SCHEDULED_EVENT_HOOK.value, 2)
        self.assertEqual(HookName.DEACTIVATION_HOOK.value, 3)
        self.assertEqual(HookName.CONVERSION_HOOK.value, 4)
        self.assertEqual(HookName.POST_PARAMETER_CHANGE_HOOK.value, 5)
        self.assertEqual(HookName.PRE_PARAMETER_CHANGE_HOOK.value, 6)
        self.assertEqual(HookName.PRE_POSTING_HOOK.value, 7)
        self.assertEqual(HookName.POST_POSTING_HOOK.value, 8)
        self.assertEqual(HookName.DERIVED_PARAMETERS_HOOK.value, 9)
        self.assertEqual(HookName.ATTRIBUTE_HOOK.value, 10)
        self.assertEqual(HookName.SCHEDULED_EVENT_ADJUSTMENT_HOOK.value, 11)
        self.assertEqual(HookName.POST_POSTING_ADJUSTMENT_HOOK.value, 12)
        self.assertEqual(HookName.POST_PARAMETER_CHANGE_ADJUSTMENT_HOOK.value, 13)
        self.assertEqual(HookName.CONVERSION_ADJUSTMENT_HOOK.value, 14)
        

    def test_level_enum(self):
        self.assertEqual(ParameterLevel.GLOBAL.value, 1)
        self.assertEqual(ParameterLevel.TEMPLATE.value, 2)
        self.assertEqual(ParameterLevel.INSTANCE.value, 3)

    def test_phase_enum(self):
        self.assertEqual(Phase.PENDING_IN.value, "pending_in")
        self.assertEqual(Phase.PENDING_OUT.value, "pending_out")
        self.assertEqual(Phase.COMMITTED.value, "committed")

    def test_posting_instruction_rejection_reason_enum(self):
        self.assertEqual(PostingInstructionRejectionReason.RESTRICTION_PREVENT_DEBITS.value, 1)
        self.assertEqual(PostingInstructionRejectionReason.RESTRICTION_PREVENT_CREDITS.value, 2)
        self.assertEqual(PostingInstructionRejectionReason.RESTRICTION_LIMIT_DEBITS.value, 3)
        self.assertEqual(PostingInstructionRejectionReason.RESTRICTION_LIMIT_CREDITS.value, 4)
        self.assertEqual(PostingInstructionRejectionReason.RESTRICTION_REVIEW_DEBITS.value, 5)
        self.assertEqual(PostingInstructionRejectionReason.RESTRICTION_REVIEW_CREDITS.value, 6)
        self.assertEqual(PostingInstructionRejectionReason.INSUFFICIENT_FUNDS.value, 7)
        self.assertEqual(PostingInstructionRejectionReason.AGAINST_TERMS_AND_CONDITIONS.value, 8)
        self.assertEqual(PostingInstructionRejectionReason.CLIENT_CUSTOM_REASON.value, 9)
        self.assertEqual(PostingInstructionRejectionReason.ACCOUNT_STATUS_INVALID.value, 10)
        self.assertEqual(PostingInstructionRejectionReason.WRONG_DENOMINATION.value, 11)

    def test_posting_instruction_type_enum(self):
        self.assertEqual(PostingInstructionType.AUTHORISATION.value, "Authorisation")
        self.assertEqual(
            PostingInstructionType.AUTHORISATION_ADJUSTMENT.value,
            "AuthorisationAdjustment",
        )
        self.assertEqual(PostingInstructionType.CUSTOM_INSTRUCTION.value, "CustomInstruction")
        self.assertEqual(PostingInstructionType.HARD_SETTLEMENT.value, "HardSettlement")
        self.assertEqual(PostingInstructionType.RELEASE.value, "Release")
        self.assertEqual(PostingInstructionType.SETTLEMENT.value, "Settlement")
        self.assertEqual(PostingInstructionType.TRANSFER.value, "Transfer")

    def test_rejection_reason_enum(self):
        self.assertEqual(RejectionReason.UNKNOWN_REASON.value, 0)
        self.assertEqual(RejectionReason.INSUFFICIENT_FUNDS.value, 1)
        self.assertEqual(RejectionReason.WRONG_DENOMINATION.value, 2)
        self.assertEqual(RejectionReason.AGAINST_TNC.value, 3)
        self.assertEqual(RejectionReason.CLIENT_CUSTOM_REASON.value, 4)

    

    def test_supervision_execution_mode_enum(self):
        self.assertEqual(SupervisionExecutionMode.OVERRIDE.value, 1)
        self.assertEqual(SupervisionExecutionMode.INVOKED.value, 2)

    def test_timeline_enum(self):
        self.assertEqual(Timeline.PRESENT.value, 1)
        self.assertEqual(Timeline.FUTURE.value, 2)

    def test_tside_enum(self):
        self.assertEqual(Tside.ASSET.value, 1)
        self.assertEqual(Tside.LIABILITY.value, 2)

    def test_update_permission_enum(self):
        self.assertEqual(ParameterUpdatePermission.PERMISSION_UNKNOWN.value, 0)
        self.assertEqual(ParameterUpdatePermission.FIXED.value, 1)
        self.assertEqual(ParameterUpdatePermission.OPS_EDITABLE.value, 2)
        self.assertEqual(ParameterUpdatePermission.USER_EDITABLE.value, 3)
        self.assertEqual(ParameterUpdatePermission.USER_EDITABLE_WITH_OPS_PERMISSION.value, 4)
