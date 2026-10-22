_© Thought Machine Group Limited 2022_

_All Rights Reserved. Confidential - Limited Distribution to Authorized Persons Only, Pursuant to the Terms of the Agreement between You and Thought Machine Group Limited granting you a licence for the software to which this documentation relates. This software is protected as an unpublished work and constitutes a trade secret of Thought Machine Group Limited, 5 New Street Square, London EC4A 3TW._

# Unit Tests

Unless specified otherwise `PostingInstruction` is interchangeable with `Union[AuthorisationAdjustment, CustomInstruction, InboundAuthorisation, InboundHardSettlement, OutboundAuthorisation, OutboundHardSettlement, Release, Settlement, Transfer]` for fetched / hook argument data, or `CustomInstruction` for contract-generated data. `PostingInstructionBatch` is interchangeable with `list[Union[AuthorisationAdjustment, CustomInstruction, InboundAuthorisation, InboundHardSettlement, OutboundAuthorisation, OutboundHardSettlement, Release, Settlement, Transfer]]` for fetched / hook argument data, which won't have equivalents for class methods or attributes.

## Use of TestCase

We encourage the use of separate `TestCase` classes (or extensions thereof, such as `ContractTest`) to group a specific feature's unit tests.

### Why

This helps improve legibility, traceability of tests and features, and can promote reuse of code by highlighting opportunities for shared `setUp` or `setUpClass` functions. As these tests are run using `unittest` by default, there are no direct performance improvements. This is not a priority for unit tests, as they are inherently lightweight and quick to run and do not need better performance. However, the separate classes makes it easier to subsequently split the tests into separate files, which would easily enable more parallelism with `plz`, our build system of choice.

### How

For example, if a product named `CurrentAccount` has a `MinimumBalance` feature and an `InterestAccrual` feature, we can structure our unit test file like:

- `CurrentAccountTest(ContractTest)` - this is optional, but can be useful to share product-specific test utilities across the various features
- `MinimumBalanceTest(CurrentAccountTest)` - groups specific tests for the `MinimumBalance` feature
- `InterestAccrualTest(CurrentAccountTest)` - groups specific tests for the `InterestAccrual` feature

## Subtests

We do not use pseudo sub-tests (i.e. looping through a dictionary of test cases) in our unit test classes.

### Why

The pseudo sub-tests are an undesirable compromise that favours the initial test writer without considering impact to others:

1. They're difficult to maintain as you lose IDE refactor assistance (e.g. the dictionary keys won't be updated by an automated rename)
2. They make it hard to tell where coverage is coming from
3. They have worse visibility, as when one sub test fails it risks prevents some or all the others
4. The test execution itself drifts from the setup. Over time test writers start adding new cases without properly checking how the executor works and this leads to tests not doing what they are meant to

### How

We currently have issues with `unittest-xml-reporting` and `unittest`'s `subTest` feature. While we investigate this further, we recommend putting shared test setup into `setUp` or `setUpClass`, and defining additional helper methods to repeat any test execution. However, these should not impede legibility or the ability to understand what the test is asserting on.

## Vault Mocks

The test framework includes extensive mocks for unit tests, which are effectively indispensable.

### Why

Unit tests rely on mocks to isolate tests from external dependencies. The `vault` object is crucial in all contracts and mocking its methods and attributes accurately is therefore key to getting representative tests. However, it is not obvious how certain aspects should be mocked accurately without reverse engineering behaviour from simulator and/or end-to-end tests. This is compounded by the fact that the many `vault` methods and attribute behaviours are often derived from similar data (Posting Instructions and Client Transactions). Mocking these independently further adds to the risk that the mocks are not accurate and the tests do not actually provide good coverage.
To reduce this risk, we have developed mocks and associated helpers to get accurate tests and also reduce the burden on test writers/readers. We typically expose them via the `ContractTest` and `SupervisorContractTest` `TestCase` classes.

### How

The `create_mock()` methods on `ContractTest` and `SupervisorContractTest` (`inception_sdk/test_framework/unit/common.py` and `inception_sdk/test_framework/unit/supervisor/common.py`) let test writers pass in data and create a mock `vault` object for use in tests. In some cases, the input data is fairly self-explanatory, but the next sections clarify some of the more complicated areas.

#### Postings and ClientTransactions

Many tests revolve around processing `PostingInstruction` and `ClientTransaction` objects. Each instruction type has a corresponding method available on `ContractTest` which takes care of accurately creating `committed_postings` so that Contract API methods like `.balances()` behave as expected. For example, `outbound_auth()` or `inbound_hard_settlement()`. Note that:

   1. These methods are always directional as only one side of the instruction should be affecting the customer account
   2. Each method exposes unique/mandatory attributes for that instruction type, but there are a number of generic attributes that can be passed in as kwargs, such as `client_id`, `client_transaction_id`, `value_timestamp`, `instruction_details` etc
   3. In some cases there are multiple methods for a given instruction (e.g. `settle_outbound_auth()` and `settle_inbound_auth()`). This is to simplify some of the mocking logic, but may be improved upon in the future. Because each instruction is considered separately, rather than as a part of a client transaction, each method has to know what preceded it. For example, `settle_outbound_auth()` needs to know the `unsettled_amount` prior to the settlement to accurately portray the resulting balance changes (e.g. the amount that the `Phase.PENDING_OUTGOING` balance is credited/debited depends on how much is still there)
   4. In general, exceptions due to Contracts API validation is a sign that the mocked object is invalid. However, in some conditions the `_from_proto` kwarg can be used to bypass Contracts API validation. For example, zero-amount postings can be committed by the Vault, but not created inside a contract, so mocking these correctly requires bypassing validation (see documentation/implementation/requirements_fetching_and_processing.md for more information about zero-amount postings)

Since Contracts API 4.x was introduced we typically use utility helpers and/or features to manipulate posting classes. As we mock these helpers/features, we have a much smaller need to directly set up this type of data.

#### Other Data

Please refer to the `ContractTest.create_mock` doc strings for information on Flags and Calendar Events

## Testing Templates and Features

Templates and features should be tested individually at a unit level, mocking any features they depend on.

### Why

We consider templates and features to be the equivalent to a class in traditional programming. As such, we wish to test their public methods at a unit level, mocking dependencies on other classes. This helps keep the tests focused on what they actually need to test.
It also enables us to generate meaningful coverage metrics for all templates and features, which in turn gives us better confidence that changes do not introduce unintended side effects.

### How

As templates and features are syntactically valid python, contract writers should feel free to re-use the approaches they are familiar with.

Note: If you are patching the `vault` object, make sure that the test argument is passed into `create_mock()` using the `existing_mock` kwarg (e.g. `self.create_mock(existing_mock=mock_vault)`). Otherwise a new `Mock` object is created and your patched `vault` will not be set up as expected.

Note: if you need to assert on a value from a dependency of the feature or template you are testing, do so via the feature or template. This helps simplify dependency management, ensures you are asserting against the right value, and can help with refactoring (e.g. immediate highlighting of errors if the feature is removed from the contract). For example:

```python
# DO
from library.my_product.contracts.template import my_product
...
self.assertEqual(result, my_product.my_feature.A_CONSTANT)

# DON'T
from library.my_product.contracts.template import my_product
from library.features import my_feature
...
self.assertEqual(result, my_feature.A_CONSTANT)
```

## Contracts API 4.x and Classes

Ensure you use the appropriate classes/sub-classes in tests.

### Why

Contracts API 4.x comes with a number of enhancements, including the `contracts_api` package. The importable classes expose contract writers to the same validation that contracts use in simulation and end-to-end and enables them to write more accurate unit tests. However, there are a few complications:

- `contracts_api` classes don't currently have useful equality methods, which makes assertion failures in tests harder to understand
- The extra validation can make unit testing approaches such as using sentinels more complicated (sentinels will cause richer validations to fail)

As a result, the Inception SDK provides some additional classes:

- `inception_sdk.test_framework.contracts.unit.contracts_api_extension` exposes the classes from `contracts_api` that are sub-classed to add a generic `__eq__` methods to provide more useful information when comparisons fail.
- `inception_sdk.test_framework.contracts.unit.contracts_api_sentinels` exposes a subset of replacements for classes from `contracts_api` that can be used instead of a regular `unittest.sentinel`. This allows us to preserve `contracts_api` validation and benefit from a sentinel-like approach

### How

Follow this guidance when deciding which to use in a test:

- if the object is being provided to a contract or feature method, whether as an argument or via a mock, and the object is not simply passed-through, always use the original `contract_api` class. This ensures no one accidentally introduces a dependency on methods that aren't available in the actual API and that will fail in simulation or end-to-end execution. This is reflected in the types we use on the v4 `create_mock` function.
- if the object in the above scenario is not passed-through, or is passed into the constructor for another `contract_api` class, use the `contracts_api_sentinels` equivalent. These try to use `unittest.sentinel`s on the individual attributes in a way that will not fail validation. Please note we are still in the processing of building these out.
- if the object is solely being used in a test assertion, use the `contracts_api_extension` equivalent. Python 3.x's approach to evaluating `a == b` means that if one of the objects (say `b`) is a subclass of the other (say `a`), `b.__eq__` is evaluated first. We therefore only need the expected result to use the `contracts_api_extension` sub classes.
