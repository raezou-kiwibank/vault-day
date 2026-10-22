---
name: convert-clv3
description: Convert an existing Thought Machine Vault Smart Contract written using CLv3 (Contracts API 3.x) to CLv4 (Contracts API 4.x), preserving behaviour and migrating its test suite. Use for contract language migrations and upgrades.
compatibility: Requires a Vault client workspace with the feature_library and Inception SDK test framework. Reference documentation bundled for Vault 5.9.
audience: client
---

# Role
You are a conservative Python engineer who follows instructions carefully and makes minimal changes to code in order to achieve the goal of the task.

# Convert CLv3 to CLv4

This skill provides a systematic workflow for refactoring or creating Smart Contracts using the `feature_library` and the `core3` build environment.

## Workflow

### 0. Version Identification
Before starting any work, you MUST ask the user which **Vault version** (e.g., 5.9) they are working with. This information is critical for selecting the correct reference documentation. (The Contracts API versions are fixed for this skill: the source contract is CLv3 and the target is CLv4.)

### 1. Smart Contract Reference Documentation

**STRICT MANDATE**: Always consult the authoritative reference documentation in `../common-references/contracts_api_documentation/vault-<version>/` for the specific Vault version being used (e.g., `vault-5-9/`). You MUST strictly verify methods and parameters of objects (e.g., the `vault` object)—NEVER guess method names, signatures, or parameters.

This folder is organized as follows (using Contracts API 4 as the standard):

- **Contracts API V4** (also known as **CLV4**, short for Contracts Language Version 4): Standard for new contracts.
  - Base Path: `../common-references/contracts_api_documentation/vault-<version>/contracts_api_4xx/`
- **Contracts API V3** (also known as **CLV3**, short for Contracts Language Version 3): For legacy or specific V3 requirements.
  - Base Path: `../common-references/contracts_api_documentation/vault-<version>/contracts_api_3xx/`

### 2. Analyse existing contract and requirements

Analyse and convert the existing smart contract in small batches, for example, by converting the metadata first, then each function in order.  If your conversation context grows long, re-read this skill between batches to keep its rules fresh in your working memory.  Read the Simulation tests and any provided requirements to understand the expected behaviour.

### 3. Create a test plan

Use the create-test-plan skill and a sub agent to come up with a test plan for the new contract

### 4. Create the CLv4 contract
Use the create-smart-contract skill to understand which Python types and keywords can be used and from where they can be imported, and which Python types and keywords are disallowed.
Create the new contract adhering to the behaviours and test plan identified from the old Smart Contract. Do not overwrite the original smart contract resource or its tests, but instead create a new version of required files.  Increment the version number of the new Smart Contract to the next major version.

1. Be conservative during conversion: keep retained function names and variable names the same, and in the same order, in the new contract as in the old.  If you don't know how to convert a piece of code, leave it unchanged and add a comment to say so.  Copy over hook annotations such as `@requires` and `@fetch_account_data` with high fidelity.  Replace the implementation of _get_parameter, if it exists, with this one:
  ```python
  def _get_parameter(
      vault: SmartContractVault,
      name: str,
      at_datetime: datetime | None = None,
      is_json: bool = False,
      is_boolean: bool = False,
      is_union: bool = False,
      is_optional: bool = False,
      default_value: Any | None = None,
  ) -> Any:
      """
      Get the parameter value for a given parameter
      :param vault:
      :param name: name of the parameter to retrieve
      :param at_datetime: datetime, time at which to retrieve the parameter value. If not
      specified the latest value is retrieved
      :param is_json: if true json_loads is called on the retrieved parameter value
      :param is_boolean: boolean parameters are treated as union parameters before calling
      str_to_bool on the retrieved parameter value
      :param is_union: if True parameter will be treated as a UnionItem
      :param is_optional: if true we treat the parameter as optional
      :param default_value: only used in conjunction with the is_optional arg, the value to use if the
      parameter is not set.
      :return: the parameter value, this is type hinted as Any because the parameter could be
      json loaded, therefore it value can be any json serialisable type and we gain little benefit
      from having an extensive Union list
      """
      if at_datetime:
          parameter = vault.get_parameter_timeseries(name=name).at(at_datetime=at_datetime)
      else:
          parameter = vault.get_parameter_timeseries(name=name).latest()

      if is_optional and parameter:
          parameter = parameter.value if parameter.is_set() else default_value

      if is_union and parameter is not None:
          parameter = parameter.key

      if is_boolean and parameter is not None:
          # since boolean parameters are defined by the UnionShape() parameter shape, the key must be
          # accessed
          parameter = str_to_bool(parameter.key)

      if is_json and parameter is not None:
          parameter = loads(parameter)

      return parameter
  ```
  Note that parameter.value only exists if the parameter is an OptionalShape, and parameter.key only exists if the parameter is a UnionShape.

  Metadata global_parameters is a list of strings; there is no special type for global parameters.

#### Note the following critical differences between the style of CLv3 contracts and CLv4 contracts
CLv3 does not have Python imports, but CLv4 strictly imports everything.

- **Types**

  Use type hints liberally, except where the type is obvious.  Include the following type definition aliases for posting instructions and use them:
  ```python
  PostingInstructionTypeAlias = (
      AuthorisationAdjustment
      | CustomInstruction
      | InboundAuthorisation
      | InboundHardSettlement
      | OutboundAuthorisation
      | OutboundHardSettlement
      | Release
      | Settlement
      | Transfer
  )

  # For some reason mypy does not like `list[PostingInstructionTypeAlias]`
  PostingInstructionListAlias = list[
      AuthorisationAdjustment
      | CustomInstruction
      | InboundAuthorisation
      | InboundHardSettlement
      | OutboundAuthorisation
      | OutboundHardSettlement
      | Release
      | Settlement
      | Transfer
  ]
  ```
  Retrieval of `batch_details` has changed.  It is not on the list of posting instructions but on each posting element within that list.

  Retrieval of posting `balances()` has changed.  It is not on the list of posting instructions but on each posting element within that list.

  The following types are importable from `inception_sdk.vault.contracts.extensions.contracts_api_extensions`, but they should not be imported because older versions of the Inception SDK test framework cannot render the contract:
  - `SmartContractVault`
  - `SuperviseeContractVault`
  - `SupervisorContractVault`

  The `NumberKind` type in CLv3 does not exist in CLv4, indeed CLv4 has no equivalent, so `NumberKind` definitions should be omitted from the converted code.

  The `NumberShape` type in CLv4 does not have the attribute `kind`, so any information about the `kind` can be omitted from converted code.

  Use this type equivalence table to assist conversion:

  | Type in CLv3     | Type in CLv4              |
  |------------------|---------------------------|
  | EventType        | SmartContractEventType    |
  | Level            | ParameterLevel            |
  | UpdatePermission | ParameterUpdatePermission |

  The `OptionalShape` type in CLv4 must always receive a keyword argument, `shape` which is an instance of `AccountIdShape`, `DateShape`, `DenominationShape`, `NumberShape`, `StringShape`, `UnionShape`.

  The `OptionalValue` type in CLv4 must always receive a keyword argument, `value` which is an instance of `Decimal`, `str`, `datetime`, `UnionItemValue`, `int`, `None`.

  The `UnionShape` type in CLv4 must always rceive a keyword argument `items` which contains a list of `UnionItem`.

- **Hook Signatures and Arguments**

  All hooks now follow a standard `(vault, hook_arguments)` signature. Instead of varying arguments like `effective_date`, all hook-specific data is accessed via the `hook_arguments` object. For example, `hook_arguments.effective_datetime` is the standard way to access the hook's execution time.

- **Directives as Classes and Result Objects**

  CLv3 "side-effect" calls to `vault` methods must be transformed into CLv4 "returned directives."
  - **Postings**: CLv3 uses methods with side effects like `vault.make_internal_transfer_instructions`, whereas CLv4 manually constructs a list of `CustomInstruction` containing a list of `Posting` objects.
  - CLv3 used `vault.account_creation_datetime` (attribute) or `vault.get_account_creation_date()` (method). In CLv4, this is replaced by the method call `vault.get_account_activation_datetime()`.
  - **Other Actions**: All `vault` methods for instructing actions (e.g., `add_account_note`, `start_workflow`, `amend_schedules`) are replaced by specific Directive classes like `AccountNotificationDirective`, `UpdateAccountEventTypeDirective`, and `PlanNotificationDirective`.
  - **Return Types**: Each CLv4 hook must return a hook-specific `*HookResult` object (e.g., `PostPostingHookResult`) containing the list of directives.

- **Balances fetching**
  The CLv3 `vault` object method `get_balance_timeseries`, with data provided by the `@requires` hook decorator has no direct equivalent in CLv4.  Instead deep analysis is required to determine whether it should be replaced by `get_balances_observation` or `get_balances_timeseries`.  Where the latest or live balances are fetched, eg `vault.get_balance_timeseries().latest()` should be replaced with `vault.get_balances_observation(fetcher_id="some_fetcher").balances`, the `@requires(event_type="some_event", balances="latest")` decorator `balances` attribute should be replaced with a new hook decorator `@fetch_account_data(event_type="some_event", balances=["some_fetcher"])` (the `event_type` argument is mandatory), and a `BalancesObservationFetcher` object should be defined with an id of `"some_fetcher"` and added to the `data_fetchers` contract metadata.  A basic `effective_datetime` balances observation fetcher looks like this:
  ```python
  BalancesObservationFetcher(
      fetcher_id="some_fetcher",
      at=DefinedDateTime.EFFECTIVE_DATETIME
  )
  ```
  and a live balances observation fetcher looks like this:
  ```python
  BalancesObservationFetcher(
      fetcher_id="some_fetcher",
      at=DefinedDateTime.LIVE,
  )
  ```
  A previous day's observation fetcher looks like this:
  ```python
  BalancesObservationFetcher(
      fetcher_id=PREVIOUS_EOD_1_FETCHER_ID,
      at=RelativeDateTime(
          shift=Shift(days=-1),
          origin=DefinedDateTime.EFFECTIVE_DATETIME,
          find=Override(hour=0, minute=0, second=0),
      ),
  )
  ```


- **Rejection Handling**

  In CLv3, business logic often rejected invalid inputs by raising a Python `Exception`. In CLv4, this is strictly handled by returning a `Rejection` object within the appropriate `*HookResult` (e.g., `PrePostingHookResult`). Note that not all hooks support rejections; check the API reference for the specific hook result type. Avoid using `assert` for business logic validation, as it raises an `AssertionError` which the platform may treat as a transient failure rather than a deterministic business rejection.

- **Floating Point Restrictions**

  The use of `float` is strictly forbidden in CLv4 and will raise an exception upon contract upload. All financial and mathematical logic must use `Decimal` or `int`.

- **Date and Time (Timezones)**

  CLv3 datetimes are not zone-aware, but CLv4 datetimes must always be zone-aware.  The built-in constants datetime.min and datetime.max are not zone-aware, so do not use them.  The maximum allowable datetime value in CLv4 is 2099-12-31T23:59:59Z.
  CLv3 uses variables called `effective_date`, but CLv4 by convention renames them as `effective_datetime`.
  CLv3 uses the `timedelta` type as an alias for the `relativedelta` type (from `dateutil.relativedelta`), but CLv4 uses `relativedelta` directly.
  CLv3 localises dates with `vault.localize_datetime` (using `pytz`), but CLv4 uses the standard Python `zoneinfo` library.
  CLv4 adjusts datetimes to different timezones with `ZoneInfo` objects, not `timezone`.  It is illegal in CLv4 to import `timezone` from `datetime`.  Therefore use a constant `UTC = ZoneInfo("UTC")` in place of `timezone.utc`.
  The `vault` object attribute `vault.events_timezone` is now a `ZoneInfo` object.  All datetime calculations should first localise to the local timezone, perform datetime arithmetic, then re-localise to UTC, however schedules declared in `activation_hook` or `conversion_hook` should be localised to `vault.events_timezone`.

- **JSON parsing and serialisation**

  CLv3 uses `json_dumps` as an alias for `json.dumps`, and `json_loads` as an alias for `json.loads`, but CLv4 uses these `json` module functions without aliases.

- **Supervisor Compatibility**

  A CLv4 Supervisor Contract cannot supervise a CLv3 Smart Contract, and vice versa. When upgrading a product ecosystem, the Supervisor and all its supervised Smart Contracts must be converted to CLv4 and upgraded together.

- **CLv3 to CLv4 Hook Equivalence Table for Smart Contracts**

  | CLv3 Hook                    | CLv4 Hook                              | Key Differences & Return Types                                         |
  |------------------------------|----------------------------------------|------------------------------------------------------------------------|
  | execution_schedules()        | activation_hook()                      | v3: Returns list of tuples. v4: Returns ActivationHookResult with      |
  |                              |                                        | ScheduledEvent objects.  'The `start_datetime` of a ScheduledEvent     |
  |                              |                                        | cannot be None, unless it is the ScheduledEvent for an existing        |
  |                              |                                        | schedule returned by `conversion_hook`.                                |
  | scheduled_code()             | scheduled_event_hook()                 | v3: Uses global vault. v4: Returns ScheduledEventHookResult containing |
  |                              |                                        | directives (e.g., PostingInstructionsDirective).                       |
  | pre_posting_code()           | pre_posting_hook()                     | v3: Global postings arg. v4: Returns PrePostingHookResult. Logic is    |
  |                              |                                        | strictly for validation (reject/accept).                               |
  | post_posting_code()          | post_posting_hook()                    | v3: Side-effect based. v4: Returns PostPostingHookResult. Used for     |
  |                              |                                        | reactive logic after a posting is committed.                           |
  | pre_parameter_change_code()  | pre_parameter_change_hook()            | v3: Validates parameter updates. v4: Returns                           |
  |                              |                                        | PreParameterChangeHookResult.                                          |
  | post_parameter_change_code() | post_parameter_change_hook()           | v3: Side-effects after update. v4: Returns                             |
  |                              |                                        | PostParameterChangeHookResult.                                         |
  | derived_parameters()         | derived_parameter_hook()               | v3: Returns a dict. v4: Returns DerivedParameterHookResult.            |
  | close_code()                 | deactivation_hook()                    | v3: Runs on account closure. v4: Returns DeactivationHookResult.       |
  | upgrade_code()               | conversion_hook()                      | v3: Used for migrations. v4: More robust migration of state via        |
  |                              |                                        | ConversionHookResult.                                                  |
  | None                         | attribute_hook()                       | v4: Returns AttributeHookResult. Handles requests for any attribute    |
  |                              |                                        | listed in the attributes metadata.                                     |
  | None                         | conversion_adjustment_hook()           | v4: Returns ConversionAdjustmentHookResult. Handles adjustments        |
  |                              |                                        | during conversion.                                                     |
  | None                         | post_parameter_change_adjustment_hook()| v4: Returns PostParameterChangeAdjustmentHookResult. Handles           |
  |                              |                                        | adjustments after parameter changes.                                   |
  | None                         | post_posting_adjustment_hook()         | v4: Returns PostPostingAdjustmentHookResult. Handles adjustments       |
  |                              |                                        | after postings.                                                        |
  | None                         | scheduled_event_adjustment_hook()      | v4: Returns ScheduledEventAdjustmentHookResult. Handles adjustments    |
  |                              |                                        | for scheduled events.                                                  |
  | pre_boot_code()              | Removed                                | Logic typically migrates to activation_hook or is handled by the       |
  |                              |                                        | platform initialization.                                               |

- **CLv3 to CLv4 Hook Equivalence Table for Supervisors**

  | CLv3 Supervisor Hook  | CLv4 Supervisor Hook     | CLv4 Signature & Key Changes                                                    |
  |-----------------------|--------------------------|---------------------------------------------------------------------------------|
  | execution_schedules() | activation_hook()        | Args: (vault, hook_arguments: SupervisorActivationHookArguments)                |
  |                       |                          | Returns: SupervisorActivationHookResult                                         |
  |                       |                          | Changes: v3 returns a list of tuples;                                           |
  |                       |                          | v4 returns explicit ScheduledEvent and ScheduleExpression objects.              |
  | scheduled_code()      | scheduled_event_hook()   | Args: (vault, hook_arguments: SupervisorScheduledEventHookArguments)            |
  |                       |                          | Returns: Optional[SupervisorScheduledEventHookResult]                           |
  |                       |                          | Changes: Replaces v3 side-effects (e.g. instruct_posting_batch) with returned   |
  |                       |                          | supervisee_posting_instructions_directives.                                     |
  | pre_posting_code()    | pre_posting_hook()       | Args: (vault, hook_arguments: SupervisorPrePostingHookArguments)                |
  |                       |                          | Returns: Optional[SupervisorPrePostingHookResult]                               |
  |                       |                          | Changes: Supervision must be explicitly enabled in SmartContractDescriptor.     |
  |                       |                          | Rejections must be returned as a Rejection object.                              |
  | post_posting_code()   | post_posting_hook()      | Args: (vault, hook_arguments: SupervisorPostPostingHookArguments)               |
  |                       |                          | Returns: Optional[SupervisorPostPostingHookResult]                              |
  |                       |                          | Changes: Purely reactive. Used for cross-account logic (e.g., updating shared   |
  |                       |                          | fee counters) after supervisee transactions commit.                             |
  | upgrade_code()        | conversion_hook()        | Args: (vault, hook_arguments: SupervisorConversionHookArguments)                |
  |                       |                          | Returns: SupervisorConversionHookResult                                         |
  |                       |                          | Changes: v4 adds formal support for re-mapping schedules and plan state during  |
  |                       |                          | a version upgrade.                                                              |


### 5. Verify the new contract
Check which tools are installed and available to use for linting.  Try ruff, black, isort, flake8, or whatever the local repo configures.  Use whatever is available to lint the contract and make sure the code is formatted according to the repo's coding standards.  Iteratively remove unused functions, variables, and imports.  Keep the line length to 100 characters.

### 6. Create the tests for the new contract

Use a sub agent with the create-sc-tests skill to generate the unit tests for the smart contract.

**Note on Unit Testing Strategy:**
CLv4 unit tests require a complete rewrite from CLv3. CLv3 tests often relied on mocking global objects, whereas CLv4 tests must use the `contracts_api` Python package available in the Contracts SDK. This package provides the actual types and structures used in the contract, allowing for more robust and type-safe testing. Ensure that the sub-agent is aware that CLv3 unit tests cannot be directly reused and the test cases must be reconstructed following the CLv4 patterns.  All applicable test cases should be reconstructed, and new tests created for new functions.  Do not convert or write unit tests until the Simulation tests are passing.

**Note on Simulation Testing Strategy:**
CLv4 Simulation tests are essentially the same, so test cases should be as faithful as possible to the original test cases.  Use the Simulation test suite to check the correctness of the converted contract.

**Note on E2E Testing Strategy:**
CLv4 E2E tests are essentially the same, so test cases should be as faithful as possible to the original test cases.
