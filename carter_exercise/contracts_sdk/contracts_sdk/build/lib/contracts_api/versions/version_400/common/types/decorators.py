from functools import wraps
from typing import Optional, Union

from ...common.docs import _common_docs_path
from .....utils import types_utils
from .....utils.exceptions import InvalidSmartContractError
from .....utils.feature_flags import (
    ACCOUNT_ATTRIBUTE_HOOK,
    CALENDAR_FETCHERS,
    SCHEDULER_EXECUTION_TIMES,
    is_fflag_enabled,
)




# @requires decorator.
def _requires(
    *,
    attribute_name: Optional[str] = None,
    balances: Optional[str] = None,
    calendar: Optional[list[str]] = None,
    data_scope: Optional[str] = None,
    event_type: Optional[str] = None,
    flags: Optional[bool] = None,
    last_execution_datetime: Optional[list[str]] = None,
    parameters: Optional[bool] = None,
    postings: Optional[bool] = None,
    supervisee_hook_directives: Optional[str] = None,
):
    def wrapper(func):
        @wraps(func)
        def decorator(*args, **kwargs):
            return func(*args, **kwargs)

        return decorator

    return wrapper


requires = types_utils.DecoratorSpec(
    name="requires",
    object=_requires,
)


def populate_requires_decorator_spec():
    """Populates the @requires DecoratorSpec with complete set of fields.

    Returns:
      DecoratorSpec representing the 'requires' decorator.
    """
    requires_docstring = "`@requires(*, "
    if is_fflag_enabled(ACCOUNT_ATTRIBUTE_HOOK):
        requires_docstring += "attribute_name, "
    requires_docstring += (
        "balances, calendar, data_scope, event_type, flags, "
        "last_execution_datetime, parameters, postings, supervisee_hook_directives)`\n\n"
        "See full requirements reference for [Smart Contracts](/reference/contracts/contracts_api_4xx/"
        "smart_contracts_api_reference4xx/hook_requirements) and [Supervisors](/reference/contracts/"
        "contracts_api_4xx/supervisor_contracts_api_reference4xx/hook_requirements).\n\n"
    )
    requires.docstring = requires_docstring
    requires.args = [
        types_utils.ValueSpec(
            name="balances",
            type="str",
            docstring="""
                    A [Range Specifier](/reference/contracts/contracts_api_4xx/concepts/#requirements-range_specifiers)
                    for example "1 day live"
                """,
        ),
        types_utils.ValueSpec(
            name="calendar",
            type="List[str]",
            docstring="A list of Calendar IDs of the required Calendar Events",
        ),
        types_utils.ValueSpec(
            name="data_scope",
            type="str",
            docstring="See [supervisor data scope](../../supervisor_contracts_api_reference4xx/"
            "hook_requirements/#data_scope)<br>  \n(**Supervisor Only**)",
        ),
        types_utils.ValueSpec(
            name="event_type",
            type="str",
            docstring="The defined [metadata event_type](/reference/contracts/contracts_api_4xx/"
            "smart_contracts_api_reference4xx/metadata/#event_types) that the requirements will "
            'fetch, for example: `@requires(event_type="ACCRUE_INTEREST", ...)`\n(only applies '
            "to `scheduled_event_hook`). "
            "The `scheduled_event_hook` can be decorated with multiple `@requires` decorators to "
            "define requirements per event_type.",
        ),
        types_utils.ValueSpec(
            name="flags",
            type="bool",
            docstring="Defaults to False",
        ),
        types_utils.ValueSpec(
            name="last_execution_datetime",
            type="List[str]",
            docstring="A list of [`event_types`](/reference/contracts/contracts_api_4xx/"
            "smart_contracts_api_reference4xx/metadata/#event_types) to retrieve last execution "
            "datetimes for",
        ),
        types_utils.ValueSpec(
            name="parameters",
            type="bool",
            docstring="Defaults to False",
        ),
        types_utils.ValueSpec(
            name="postings",
            type="str",
            docstring="""
                    A [Range Specifier](/reference/contracts/contracts_api_4xx/concepts/#requirements-range_specifiers)
                    for example "1 day live"
                """,
        ),
        types_utils.ValueSpec(
            name="supervisee_hook_directives",
            type="str",
            docstring="""
                    One of `none`, `all` or `invoked` that defaults to `none`
                    <br>  \n(**Supervisor Only**)
                """,
        ),
    ]

    if is_fflag_enabled(ACCOUNT_ATTRIBUTE_HOOK):
        requires.args.insert(
            0,
            types_utils.ValueSpec(
                name="attribute_name",
                type="str",
                docstring="The defined Attribute that the data will be fetched for, for example: "
                '`@requires(attribute_name="current_balance", ...)`\n'
                "(only applies to [attribute_hook](/reference/contracts/contracts_api_4xx/"
                "smart_contracts_api_reference4xx/hooks/#attribute_hook)). "
                "The `attribute_hook` can be decorated with multiple `@requires` decorators "
                "to define requirements per attribute_name.",
            ),
        )

    return requires


# @fetch_account_data decorator.
def _fetch_account_data(
    *,
    attribute_name: Optional[str] = None,
    balances: Optional[Union[list[str], dict[str, list[str]]]] = None,
    event_type: Optional[str] = None,
    parameters: Optional[list[str]] = None,
    postings: Optional[list[str]] = None,
    flags: Optional[list[str]] = None,
    
    calendars: Optional[list[str]] = None,
    last_scheduled_event_datetimes: Optional[list[str]] = None,
):
    def wrapper(func):
        @wraps(func)
        def decorator(*args, **kwargs):
            return func(*args, **kwargs)

        return decorator

    return wrapper


fetch_account_data = types_utils.DecoratorSpec(
    name="fetch_account_data",
    object=_fetch_account_data,
)


def populate_fetch_account_data_decorator_spec():
    """Populates the @fetch_account_data DecoratorSpec with complete set of fields.

    Returns:
      DecoratorSpec representing the 'fetch_account_data' decorator.
    """

    # Dynamically generate the fetch_account_data docstring depending on feature flags defined.
    fetch_account_data_params = "`@fetch_account_data(*, balances, "
    if is_fflag_enabled(ACCOUNT_ATTRIBUTE_HOOK):
        fetch_account_data_params = "`@fetch_account_data(*, attribute_name, balances, "
    if is_fflag_enabled(CALENDAR_FETCHERS):
        fetch_account_data_params += "calendars, "
    fetch_account_data_params += "event_type, flags, "
    if is_fflag_enabled(SCHEDULER_EXECUTION_TIMES):
        fetch_account_data_params += "last_scheduled_event_datetimes, "
    fetch_account_data_params += "parameters, postings)`"

    fetch_account_data_docstring = (
        f"{fetch_account_data_params}"
        "\n\nSee full account fetcher requirements for [Smart Contracts]"
        "(/reference/contracts/contracts_api_4xx/smart_contracts_api_reference4xx/account_fetcher_requirements)"
        " and "
        "[Supervisors](/reference/contracts/contracts_api_4xx/supervisor_contracts_api_reference4xx"
        "/account_fetcher_requirements).\n\n"
    )

    fetch_account_data.docstring = fetch_account_data_docstring
    fetch_account_data.smart_contract_args = [
        types_utils.ValueSpec(
            name="balances",
            type="List[str]",
            docstring="""
                A list of
                [BalancesIntervalFetcher](/reference/contracts/contracts_api_4xx/common_types_4xx/classes#balancesintervalfetcher),
                [BalancesDiscreteIntervalFetcher](/reference/contracts/contracts_api_4xx/common_types_4xx/classes#balancesdiscreteintervalfetcher)
                or
                [BalancesObservationFetcher](/reference/contracts/contracts_api_4xx/common_types_4xx/classes#balancesobservationfetcher)
                Fetcher IDs.
            """,
        ),
        types_utils.ValueSpec(
            name="event_type",
            type="str",
            docstring="The defined [metadata event_type](/reference/contracts/"
            "contracts_api_4xx/smart_contracts_api_reference4xx/metadata/#event_types)  "
            "that the data will be fetched for, for example:  "
            '`@fetch_account_data(event_type="ACCRUE_INTEREST", ...)`\n'
            "(only applies to `scheduled_event_hook`). "
            "The `scheduled_event_hook` can be decorated with multiple `@fetch_account_data` decorators "
            "to define requirements per event_type.",
        ),
        types_utils.ValueSpec(
            name="flags",
            type="List[str]",
            docstring=f"A list of [FlagsIntervalFetcher]({_common_docs_path}classes/#FlagsIntervalFetcher) and "  # noqa: F541
            f"[FlagsObservationFetcher]({_common_docs_path}classes/#FlagsObservationFetcher) Fetcher IDs",
            # noqa: F541
        ),
        types_utils.ValueSpec(
            name="parameters",
            type="List[str]",
            docstring="A list of [ParametersIntervalFetcher](/reference/contracts/"
            "contracts_api_4xx/common_types_4xx/classes/#ParametersIntervalFetcher) or "
            "[ParametersObservationFetcher](/reference/contracts/contracts_api_4xx/"
            "common_types_4xx/classes/#ParametersObservationFetcher) "
            "Fetcher IDs",
        ),
        types_utils.ValueSpec(
            name="postings",
            type="List[str]",
            docstring="A list of [PostingsIntervalFetcher](/reference/contracts/"
            "contracts_api_4xx/common_types_4xx/classes/#PostingsIntervalFetcher) Fetcher IDs",
        ),
    ]
    fetch_account_data.supervisor_args = [
        types_utils.ValueSpec(
            name="balances",
            type="Dict[str, List[str]]",
            docstring="A dictionary where the key is Supervisee [SmartContractDescriptor]"
            f"({_common_docs_path}"
            "classes/#SmartContractDescriptor) alias and value is a list of "
            "[BalancesIntervalFetcher](/reference/contracts/contracts_api_4xx/"
            "common_types_4xx/classes/#BalancesIntervalFetcher) or "
            "[BalancesObservationFetcher](/reference/contracts/contracts_api_4xx/"
            "common_types_4xx/classes/#BalancesObservationFetcher) "
            "Fetcher IDs.<br>  \n*Note: Currently only available in `pre_posting_hook`*",
        ),
    ]
    

    if is_fflag_enabled(CALENDAR_FETCHERS):
        fetch_account_data.smart_contract_args.append(
            types_utils.ValueSpec(
                name="calendars",
                type="List[str]",
                docstring=(
                    "A fetcher for retrieving calendar events over an interval, inclusive of end time."
                    "The `filter` attribute must be populated with a `CalendarsFilter` containing the "
                    "calendar IDs to fetch for. "
                ),
            )
        )
        fetch_account_data.smart_contract_args.sort(key=lambda v: v.name)

    if is_fflag_enabled(SCHEDULER_EXECUTION_TIMES):
        fetch_account_data.smart_contract_args.append(
            types_utils.ValueSpec(
                name="last_scheduled_event_datetimes",
                type="List[str]",
                docstring="A list of [LastScheduledEventDateTimesObservationFetcher](/reference/contracts/"
                "contracts_api_4xx/common_types_4xx/classes/#LastScheduledEventDateTimesObservationFetcher)"
                "Fetcher IDs",
            )
        )
        fetch_account_data.smart_contract_args.sort(key=lambda v: v.name)

    if is_fflag_enabled(ACCOUNT_ATTRIBUTE_HOOK):
        fetch_account_data.smart_contract_args.insert(
            0,
            types_utils.ValueSpec(
                name="attribute_name",
                type="str",
                docstring="The defined Attribute that the data will be fetched for, for example: "
                '`@fetch_account_data(attribute_name="current_balance", ...)`\n'
                "(only applies to [attribute_hook](/reference/contracts/contracts_api_4xx/"
                "smart_contracts_api_reference4xx/hooks/#attribute_hook)). "
                "The `attribute_hook` can be decorated with multiple `@fetch_account_data` decorators "
                "to define requirements per attribute_name.",
            ),
        )

    return fetch_account_data






