from unittest import TestCase

from ..types import (
    fetch_account_data,
    
    requires,
)
from .....utils.exceptions import (
    StrongTypingError,
    InvalidSmartContractError,
)

DECORATOR_ERROR = "decorator should not pass anything to hook"


class TestRequiresDecorator(TestCase):
    def test_requires_decorator(self):
        arguments = ("arg_1", "arg_2")
        keyword_arguments = {"kwarg_1": "kwarg_1_value", "kwarg_2": "kwarg_2_value"}

        @requires(
            balances="latest",
            calendar=["cal_1"],
            data_scope="all",
            event_type="EVENT",
            flags=True,
            last_execution_datetime=["EVENT"],
            parameters=True,
            postings=True,
        )
        def hook(*args, **kwargs):
            self.assertEqual(arguments, args, DECORATOR_ERROR)
            self.assertEqual(keyword_arguments, kwargs, DECORATOR_ERROR)
            return True

        # Assert that the decorator does not change what arguments are propagated to the hook.
        self.assertTrue(hook(*arguments, **keyword_arguments))


class TestFetchAccountDataDecorator(TestCase):
    def test_fetch_account_data_decorator(self):
        arguments = ("arg_1", "arg_2")
        keyword_arguments = {"kwarg_1": "kwarg_1_value", "kwarg_2": "kwarg_2_value"}

        @fetch_account_data(
            balances=["fetcher_1"],
            event_type="EVENT",
            parameters=["fetcher_2"],
            postings=["fetcher_3"],
            flags=["flags_fetcher_1"],
        )
        def hook(*args, **kwargs):
            self.assertEqual(arguments, args, DECORATOR_ERROR)
            self.assertEqual(keyword_arguments, kwargs, DECORATOR_ERROR)
            return True

        # Assert that the decorator does not change what arguments are propagated to the hook.
        self.assertTrue(hook(*arguments, **keyword_arguments))



