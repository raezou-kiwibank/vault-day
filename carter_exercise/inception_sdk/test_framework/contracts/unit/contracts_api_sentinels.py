# standard libs
from decimal import Decimal
from unittest.mock import sentinel

# contracts api
from contracts_api import (
    AccountNotificationDirective,
    Balance,
    BalancesObservation,
    CustomInstruction,
    EndOfMonthSchedule,
    Phase,
    Posting,
    PostingInstructionEnrichment,
    PostingInstructionsDirective,
    Rejection,
    ScheduledEvent,
    ScheduleExpression,
    UpdateAccountEventTypeDirective,
    UpdatePlanEventTypeDirective,
)

DEFAULT_POSTINGS = [
    Posting(
        credit=True,
        amount=Decimal("1"),
        denomination=sentinel.denomination,
        account_address=sentinel.account_address,
        account_id=sentinel.account_id,
        asset=sentinel.asset,
        phase=Phase.COMMITTED,
    ),
    Posting(
        credit=False,
        amount=Decimal("1"),
        denomination=sentinel.denomination,
        account_address=sentinel.account_address,
        account_id=sentinel.account_id,
        asset=sentinel.asset,
        phase=Phase.COMMITTED,
    ),
]


class SentinelBase:
    def __eq__(self, other: object) -> bool:
        return isinstance(other, SentinelBase) and self.__dict__ == other.__dict__

    def _validate_attributes(self):
        pass


class SentinelAccountNotificationDirective(SentinelBase, AccountNotificationDirective):
    def __init__(self, instance_id: str):
        attr_dict = {
            attr.name: getattr(sentinel, f"{attr.name}_{instance_id}")
            for attr in self.__class__._public_attributes()
        }
        super().__init__(**attr_dict)


class SentinelBalance(SentinelBase, Balance):
    def __init__(self, instance_id: str):
        attr_dict = {
            attr.name: getattr(sentinel, f"{attr.name}_{instance_id}")
            for attr in self.__class__._public_attributes()
        }
        super().__init__(**attr_dict)


class SentinelBalancesObservation(SentinelBase, BalancesObservation):
    def __init__(self, instance_id: str):
        attr_dict = {
            attr.name: getattr(sentinel, f"{attr.name}_{instance_id}")
            for attr in self.__class__._public_attributes()
        }
        super().__init__(**attr_dict)


class SentinelEndOfMonthSchedule(SentinelBase, EndOfMonthSchedule):
    def __init__(self, instance_id: str):
        attr_dict = {
            attr.name: getattr(sentinel, f"{attr.name}_{instance_id}")
            for attr in self.__class__._public_attributes()
        }
        super().__init__(**attr_dict)


class SentinelPosting(SentinelBase, Posting):
    def __init__(self, instance_id: str):
        attr_dict = {
            attr.name: getattr(sentinel, f"{attr.name}_{instance_id}")
            for attr in self.__class__._public_attributes()
        }
        # Multiple Processing Groups is currently not supported, see IDEA-777
        attr_dict.pop("internal_account_processing_label")
        super().__init__(**attr_dict)


class SentinelCustomInstruction(SentinelBase, CustomInstruction):
    def __init__(self, instance_id: str):
        attr_dict = {
            attr.name: getattr(sentinel, f"{attr.name}_{instance_id}")
            for attr in self.__class__._constructor_args()
        }
        # we need real postings because of validation on amount of postings and net posting sum
        attr_dict["postings"] = DEFAULT_POSTINGS
        super().__init__(**attr_dict)


class SentinelScheduledEvent(SentinelBase, ScheduledEvent):
    def __init__(self, instance_id: str):
        attr_dict = {
            attr.name: getattr(sentinel, f"{attr.name}_{instance_id}")
            for attr in self.__class__._public_attributes()
        }
        super().__init__(**attr_dict)


class SentinelScheduleExpression(SentinelBase, ScheduleExpression):
    def __init__(self, instance_id: str):
        attr_dict = {
            attr.name: getattr(sentinel, f"{attr.name}_{instance_id}")
            for attr in self.__class__._public_attributes()
        }
        super().__init__(**attr_dict)


class SentinelRejection(SentinelBase, Rejection):
    def __init__(self, instance_id: str):
        attr_dict = {
            attr.name: getattr(sentinel, f"{attr.name}_{instance_id}")
            for attr in self.__class__._public_attributes()
        }
        super().__init__(**attr_dict)


class SentinelUpdateAccountEventTypeDirective(SentinelBase, UpdateAccountEventTypeDirective):
    def __init__(self, instance_id: str):
        attr_dict = {
            attr.name: getattr(sentinel, f"{attr.name}_{instance_id}")
            for attr in self.__class__._public_attributes()
        }
        super().__init__(**attr_dict)


class SentinelPostingInstructionsDirective(SentinelBase, PostingInstructionsDirective):
    """
    This sentinel should be used when `non_blocking_rejection_reasons` are not required.
    """

    def __init__(self, instance_id: str):
        attr_dict = {
            attr.name: getattr(sentinel, f"{attr.name}_{instance_id}")
            for attr in self.__class__._public_attributes()
        }
        # set to an empty list as supervisor HookResults call len()
        attr_dict["non_blocking_rejection_reasons"] = []
        super().__init__(**attr_dict)


class SentinelPIDWithNonBlockingRejectionReasons(SentinelBase, PostingInstructionsDirective):
    """
    This sentinel should be used when a sentinel value for `non_blocking_rejection_reasons`
    is required.
    This should not be used outside of constructing a `SupervisorScheduledEventHookResult` since
    this is the only hook which supports `non_blocking_rejection_reasons`.
    """

    def __init__(self, instance_id: str):
        attr_dict = {
            attr.name: getattr(sentinel, f"{attr.name}_{instance_id}")
            for attr in self.__class__._public_attributes()
        }
        # wrap sentinel value in list as supervisor HookResults call len()
        attr_dict["non_blocking_rejection_reasons"] = [attr_dict["non_blocking_rejection_reasons"]]
        super().__init__(**attr_dict)


class SentinelUpdatePlanEventTypeDirective(SentinelBase, UpdatePlanEventTypeDirective):
    def __init__(self, instance_id: str):
        attr_dict = {
            attr.name: getattr(sentinel, f"{attr.name}_{instance_id}")
            for attr in self.__class__._public_attributes()
        }
        super().__init__(**attr_dict)


class SentinelPostingInstructionEnrichment(SentinelBase, PostingInstructionEnrichment):
    def __init__(self, instance_id: str):
        attr_dict = {
            attr.name: getattr(sentinel, f"{attr.name}_{instance_id}")
            for attr in self.__class__._public_attributes()
        }
        super().__init__(**attr_dict)
