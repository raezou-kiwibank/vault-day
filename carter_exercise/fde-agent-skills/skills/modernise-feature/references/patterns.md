# Modern Feature Patterns

This document defines the standardized patterns for modern features in the `feature_library`.

## 0. Feature Metadata

Every feature file MUST start with the following metadata.

```python
__smart_contract_feature__ = True
```

## 1. State Management

Modern features use `SmartContractState` from `feature_library.common.state_utils` to manage immutable state transitions.

### Initialization & Appending

Use `initialise_state` in hooks and a single `_append_to_state` within the feature to consolidate data. This helper MUST ONLY be implemented if the feature defines its own `expected_parameters` or `data_fetchers`. This helper should accept the feature's config object.

```python
def _append_to_state(
    state: state_utils.SmartContractState,
    fetchers_config: SomeFeatureFetchersConfig = DEFAULT_SOME_FEATURE_FETCHERS_CONFIG,
) -> state_utils.SmartContractState:
    """Appends feature-specific parameters and balances to the state.

    Args:
        state: The current state of the smart contract.
        fetchers_config: Configuration for the fetchers.

    Returns:
        The updated state object.
    """
    # 1. Fetch feature-specific parameters
    parameters = get_parameters(state.vault, fetchers_config.param_fetcher_id)

    # 2. Fetch balances if required by config
    balances = (
        state.vault.get_balances_observation(fetcher_id=fetchers_config.balance_fetcher_id).balances
        if fetchers_config.balance_fetcher_id else None
    )

    # 3. Consolidate into state (ONLY feature-specific data)
    state = state_utils.append_to_state(
        state=state,
        parameters=parameters,
        balances=balances,
    )

    return state
```

## 2. Parameter Fetching

Encapsulate parameter fetching in a `get_parameters` helper using a `ParametersObservationFetcher`.

## 3. Structured Entry Points (Entry Points & Hooks)

Features should provide standardized entry points for the hooks and schedules they support.

### Validation (`pre_posting_hook`)

Features that perform transaction validation should provide a `validate` function. Use keyword-only arguments for optional configuration.

```python
def validate(
    *,
    state: state_utils.SmartContractState,
    postings: posting_utils.PostingInstructionListAlias,
    **kwargs,
) -> Rejection | None:
    """Validates proposed postings against feature-specific limits.

    Args:
        state: The current state of the smart contract.
        postings: A list of proposed posting instructions.

    Returns:
        A rejection if validation fails, otherwise None.
    """
    return None
```

### Side-Effect Handling (`post_posting_hook`)

Features that trigger side-effects after a posting (e.g., fee notifications, tracker updates) should return a result **NamedTuple** ONLY if they produce multiple types of side-effects. If only a single type of side-effect is produced (e.g. only a rejection or only custom instructions), it MUST be returned directly.

```python
HandleWithdrawalsResult = NamedTuple(
    "HandleWithdrawalsResult",
    [
        ("custom_instructions", list[CustomInstruction]),
        ("account_notification_directives", list[AccountNotificationDirective]),
        ("rejection", Rejection | None),
    ],
)
```

### Schedule Configuration (`scheduled_event_hook`)

Features that define schedules should provide `get_scheduled_events`, returning a `dict[str, ScheduledEvent]`. It MUST use `assert` statements to ensure all required parameters are available in the `state`.

When setting a `start_datetime` for a schedule, it MUST take into account the account's local timezone (`state.vault.events_timezone`) if effective_datetime is being overwritten.

```python
from zoneinfo import ZoneInfo
# ... other imports
from contracts_api import ScheduledEvent, ScheduleExpression

UTC = ZoneInfo("UTC")

def get_scheduled_events(
    state: state_utils.SmartContractState,
    **kwargs,
) -> dict[str, ScheduledEvent]:
    """Generates scheduled events for the feature.

    Args:
        state: The current state of the smart contract.

    Returns:
        A dictionary of scheduled events.
    """
    # Ensure required parameters exist
    rejection = state_utils.check_parameters_exist(state=state, param_ids={"SOME_PARAM_ID"})
    assert rejection is None, rejection

    # Logic to build ScheduledEvent...
    # Ensure start_datetime is timezone-aware
    start_datetime = state.effective_datetime.astimezone(state.vault.events_timezone).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    scheduled_event = ScheduledEvent(
        start_datetime=start_datetime,
        expression=ScheduleExpression(hour=0, minute=0, second=1),
    )
    return {"SOME_EVENT": scheduled_event}
```

### Schedule Execution (`scheduled_code_hook`)

Features with scheduled logic should provide `schedule_logic`, returning a list of side-effects (e.g., `list[CustomInstruction]`) OR a result **NamedTuple** if multiple types are produced.

```python
# Use a NamedTuple only if multiple attributes are being returned (e.g. CI and Notifications)
def schedule_logic(
    state: state_utils.SmartContractState,
    **kwargs,
) -> common_tuples.ScheduleLogicResult:
    """Executes scheduled logic and returns multiple side-effects.

    Args:
        state: The current state of the smart contract.

    Returns:
        A result object containing instructions and directives.
    """
    # ...
    return common_tuples.ScheduleLogicResult(
        custom_instructions=custom_instructions,
        event_type_directives=[...],
        notification_directives=[...],
    )

# Return the type directly if only one is produced (e.g. just CustomInstructions)
def schedule_logic(
    state: state_utils.SmartContractState,
    **kwargs,
) -> list[CustomInstruction]:
    """Executes scheduled logic and returns custom instructions.

    Args:
        state: The current state of the smart contract.

    Returns:
        A list of custom instructions.
    """
    # ...
    return custom_instructions
```

## 4. Configuration & Results

### Fetcher Filters

The `ParametersFilter` for a feature's `ParametersObservationFetcher` MUST include all parameter IDs in the feature's `expected_parameters` list, including external parameters.

All Observation fetchers (Parameters, Balances, etc.) MUST have their `at` attribute explicitly populated. If not specified in the legacy feature, it MUST default to `DefinedDateTime.EFFECTIVE_DATETIME`.

- **DO**: `parameter_ids=[p.id for p in expected_parameters]` (where `expected_parameters` includes both internal and external parameters).

Example:
```python
SOME_FEATURE_PARAMS_ET_POF = ParametersObservationFetcher(
    fetcher_id=SOME_FEATURE_PARAMS_ET_POF_ID,
    at=DefinedDateTime.EFFECTIVE_DATETIME,
    filter=ParametersFilter(
        parameter_ids=[p.id for p in expected_parameters]
    ),
)
```

### Fetcher/Parameter Configuration

Use a **NamedTuple** (e.g., `SomeFeatureFetchersConfig`) to group related fetcher IDs, parameter IDs, and constants. Entry points should accept this config object (usually with a default) instead of multiple individual ID strings.

Example:
```python
SomeFeatureFetchersConfig = NamedTuple(
    "SomeFeatureFetchersConfig",
    [
        ("balance_fetcher_id", str),
        ("param_fetcher_id", str),
        ("denomination_param_id", str),
        ("precision", int),
    ],
)

DEFAULT_SOME_FEATURE_FETCHERS_CONFIG = SomeFeatureFetchersConfig(
    balance_fetcher_id=fetchers.ALL_BALANCES_ET_BOF_ID,
    param_fetcher_id=SOME_FEATURE_PARAMS_ET_POF_ID,
    denomination_param_id=denomination_module.DENOMINATION_PARAM_ID,
    precision=2,
)

def validate(
    *,
    state: state_utils.SmartContractState,
    postings: posting_utils.PostingInstructionListAlias,
    fetchers_config: SomeFeatureFetchersConfig = DEFAULT_SOME_FEATURE_FETCHERS_CONFIG,
    **kwargs,
) -> Rejection | None:
    # Use config object attributes
    state = _append_to_state(
        state,
        balance_fetcher_id=fetchers_config.balance_fetcher_id,
        param_fetcher_id=fetchers_config.param_fetcher_id
    )
    # ...
```

### Result Standardisation

Always use **NamedTuples** instead of unnamed tuples for complex return values. Prefer shared definitions from `feature_library.common.tuples` when applicable.

### External Parameter Handling

When a feature depends on a parameter from another module (e.g., `denomination`), check for its existence in `state` and **assert** that the resulting rejection is `None`. This ensures that any configuration errors (e.g., a missing parameter in a fetcher) result in a fail-fast assertion rather than silent errors or unexpected behavior.

```python
def schedule_logic(state: SmartContractState, fetchers_config: FetchersConfig):
    state = _append_to_state(state, fetchers_config)

    rejection = state_utils.check_parameters_exist(state, {fetchers_config.denomination_param_id})
    assert rejection is None, rejection

    denomination = state.parameters[fetchers_config.denomination_param_id]
    # ...
```

This pattern applies to all entry points (Validation, Side-Effect Handling, Schedules, etc.). Do NOT return early or return the rejection object; always use an assertion.

## 5. Postings & Custom Instructions

When creating `CustomInstruction` objects, avoid manually instantiating `Posting` objects. Instead, utilize the `create_postings` utility from `feature_library.common.posting_utils`.

### `posting_utils.create_postings`

This helper ensures consistency in how double-entry postings are created, including handling of zero amounts (it returns an empty list).

```python
import feature_library.common.posting_utils as posting_utils
from contracts_api import DEFAULT_ADDRESS

# ... inside a function ...
postings = posting_utils.create_postings(
    amount=principal,
    debit_account=state.vault.account_id,
    credit_account=deposit_account_id,
    denomination=denomination,
    debit_address=principal_address,
    credit_address=DEFAULT_ADDRESS,
)

if postings:
    return [
        CustomInstruction(
            postings=postings,
            override_all_restrictions=True,
            instruction_details={
                "description": f"Principal disbursement of {principal}",
                "event": DISBURSEMENT_EVENT,
            },
        )
    ]
return []
```

## 6. Functional Logic Flattening

When modernising complex logic, prefer a functional approach to reduce nesting and improve readability.

### Guard Clauses & Early Returns

Avoid deeply nested `if` statements by using guard clauses.

```python
# Before
def process(data):
    if data:
        if data.valid:
            # complex logic
            return result
    return None

# After
def process(data):
    if not data or not data.valid:
        return None

    # complex logic (flattened)
    return result
```

### Helper Mapping Functions

Replace complex `if/elif/else` blocks with helper functions or mapping dictionaries when transforming data.

```python
# Before
def get_fee(type):
    if type == "ATM":
        return Decimal("2.00")
    elif type == "WIRE":
        return Decimal("15.00")
    else:
        return Decimal("0.00")

# After
FEE_MAP = {
    "ATM": Decimal("2.00"),
    "WIRE": Decimal("15.00")
}
def get_fee(type):
    return FEE_MAP.get(type, Decimal("0.00"))
```

### List Comprehensions

**Favour the use of list comprehensions** over `for` loops to simplify list construction, especially when filtering or transforming data.

```python
# Before
results = []
for item in items:
    if item.active:
        results.append(process(item))

# After (FAVOURED)
results = [process(item) for item in items if item.active]
```

## 6. Prohibited Methods

Smart Contracts have strict limitations on certain Python built-ins and methods.

- **NamedTuple `_replace`**: Do NOT use `namedtuple._replace()`. It triggers an `IllegalPython: Invalid private member access` error. Instead, instantiate a new object with the desired values.

```python
# Before
# new_config = config._replace(balance_fetcher_id=None)

# After
new_config = SomeConfig(
    balance_fetcher_id=None,
    param_fetcher_id=config.param_fetcher_id,
    # ... include other fields ...
)
```

## 7. Interface Implementation

Secondary features (e.g., specific interest types) should implement a standardized interface defined in `feature_library.deposit.interfaces`.

## 8. Naming conventions

### Parameter constants

- Constants for Parameter IDs should implement the "_PARAM_ID" suffix (e.g. `MAXIMUM_BALANCE_PARAM_ID`).
- Constants for Parameter objects should implement the "_PARAM" suffix (e.g. `MAXIMUM_BALANCE_PARAM`).
- **CRITICAL**: The Parameter object MUST be defined directly under the Parameter ID constant.
- **CRITICAL**: Use all-caps constant naming for both the ID and the Parameter object.
- **CRITICAL**: Do NOT use "PARAM_" as a prefix. Always use the suffix.
- **Hook Triggers**: All `ExpectedParameter` objects MUST include `triggers_pre_parameter_change_hook` and `triggers_post_parameter_change_hook`. These MUST default to `False` unless explicitly required.
- **Constraints**: Do NOT include the `constraint` attribute in `ExpectedParameter` objects.

Example:
```python
MAXIMUM_BALANCE_PARAM_ID = "&{maximum_balance}"
MAXIMUM_BALANCE_PARAM = ExpectedParameter(
    id=MAXIMUM_BALANCE_PARAM_ID,
    optional=True,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)
```

### Attributes

Legacy Derived Parameters should be replaced with `Attribute` objects.

- Constants for Attribute IDs should implement the "_ATTR_ID" suffix (e.g., `TOTAL_INTEREST_ATTR_ID`).
- Constants for Attribute objects should implement the "_ATTRIBUTE" suffix (e.g., `TOTAL_INTEREST_ATTRIBUTE`).
- Use all-caps constant naming for both the ID and the Attribute object.

Example:
```python
TOTAL_INTEREST_ATTR_ID = "total_interest"
TOTAL_INTEREST_ATTRIBUTE = Attribute(
    name=TOTAL_INTEREST_ATTR_ID,
    data_type=AttributeDecimalType(),
)
```

### Time Parameters

When modernising features with separate `hour`, `minute`, and `second` parameters, consolidate them into a single string parameter (formatted as "HH:MM:SS").

- Use the suffix `_TIME_PARAM_ID` and `_TIME_PARAM`.
- The parameter should be a string (no constraint usually, or a custom regex if supported).
- In `get_scheduled_events`, parse the string using `split(':')` to populate `ScheduleExpression`.

Example:
```python
# Before
# hour_param = 0, minute_param = 0, second_param = 1

# After
APPLICATION_TIME_PARAM_ID = "interest_application_time"
APPLICATION_TIME_PARAM = ExpectedParameter(
    id=APPLICATION_TIME_PARAM_ID,
    triggers_pre_parameter_change_hook=False,
    triggers_post_parameter_change_hook=False,
)

# In get_scheduled_events
application_time: str = state.parameters[APPLICATION_TIME_PARAM_ID]
hour, minute, second = map(int, application_time.split(":"))
expression = ScheduleExpression(hour=hour, minute=minute, second=second)
```

### Fetchers

#### Parameter fetchers

- The ID for a `ParametersObservationFetcher` fetching at `EFFECTIVE_DATETIME` should have the suffix "_et_pof"

  - The constant for this ID should have the suffix "_ET_POF_ID"
  - The constant for the object should have the suffix "_ET_POF"

- The ID for a `ParametersObservationFetcher` fetching at `LIVE` should have the suffix "_live_pof"

  - The constant for this ID should have the suffix "_LIVE_POF_ID"
  - The constant for the object should have the suffix "_LIVE_POF"

- The ID for a `ParametersIntervalFetcher` should have the suffix "_pif"

  - The constant for this ID should have the suffix "_PIF_ID"
  - The constant for the object should have the suffix "_PIF"

#### Balances fetchers

- The ID for a `BalancesObservationFetcher` fetching at `EFFECTIVE_DATETIME` should have the suffix "_et_bof"

  - The constant for this ID should have the suffix "_ET_BOF_ID"
  - The constant for the object should have the suffix "_ET_BOF"

- The ID for a `BalancesObservationFetcher` fetching at `LIVE` should have the suffix "_live_bof"

  - The constant for this ID should have the suffix "_LIVE_BOF_ID"
  - The constant for the object should have the suffix "_LIVE_BOF"

- The ID for a `BalancesIntervalFetcher` should have the suffix "_bif"

  - The constant for this ID should have the suffix "_BIF_ID"
  - The constant for the object should have the suffix "_BIF"

- The ID for a `BalancesDiscreteIntervalFetcher` should have the suffix "_bdif"

  - The constant for this ID should have the suffix "_BDIF_ID"
  - The constant for the object should have the suffix "_BDIF"

#### Calendar fetchers

- The ID for a `CalendarsObservationFetcher` fetching at `EFFECTIVE_DATETIME` should have the suffix "_et_cof"

  - The constant for this ID should have the suffix "_ET_COF_ID"
  - The constant for the object should have the suffix "_ET_COF"

- The ID for a `CalendarsObservationFetcher` fetching at `LIVE` should have the suffix "_live_cof"

  - The constant for this ID should have the suffix "_LIVE_COF_ID"
  - The constant for the object should have the suffix "_LIVE_COF"

- The ID for a `CalendarsIntervalFetcher` should have the suffix "_cif"

  - The constant for this ID should have the suffix "_CIF_ID"
  - The constant for the object should have the suffix "_CIF"

#### Flag fetchers

- The ID for a `FlagsObservationFetcher` fetching at `EFFECTIVE_DATETIME` should have the suffix "_et_fof"

  - The constant for this ID should have the suffix "_ET_FOF_ID"
  - The constant for the object should have the suffix "_ET_FOF"

- The ID for a `FlagsObservationFetcher` fetching at `LIVE` should have the suffix "_live_fof"

  - The constant for this ID should have the suffix "_LIVE_FOF_ID"
  - The constant for the object should have the suffix "_LIVE_FOF"

- The ID for a `FlagsIntervalFetcher` should have the suffix "_fif"

  - The constant for this ID should have the suffix "_FIF_ID"
  - The constant for the object should have the suffix "_FIF"

#### Last Scheduled Event DateTimes fetchers

- The ID for a `LastScheduledEventDateTimesObservationFetcher` fetching at `EFFECTIVE_DATETIME` should have the suffix "_et_sof"

  - The constant for this ID should have the suffix "_ET_SOF_ID"
  - The constant for the object should have the suffix "_ET_SOF"

- The ID for a `LastScheduledEventDateTimesObservationFetcher` fetching at `LIVE` should have the suffix "_live_sof"

  - The constant for this ID should have the suffix "_LIVE_SOF_ID"
  - The constant for the object should have the suffix "_LIVE_SOF"

#### Posting fetchers

- The ID for a `PostingsIntervalFetcher` should have the suffix "_postif"

  - The constant for this ID should have the suffix "_POSTIF_ID"
  - The constant for the object should have the suffix "_POSTIF"
