# standard libs
from typing import Any, Generic, TypeVar
from unittest import TestCase
from zoneinfo import ZoneInfo

# inception sdk
from inception_sdk.vault.pydantic_types import VaultBaseModel

UTC = ZoneInfo("UTC")

PydanticResource = TypeVar("PydanticResource", bound=VaultBaseModel)


class TestPydanticModels(TestCase):
    # All test classes that inherit from TestPydanticModels.Base will
    # get a test for parsing from dict and outputting to dict.
    # Using an inner class prevents the base itself from being discovered

    class Base(TestCase, Generic[PydanticResource]):
        dictionary: dict[str, Any]
        resource: PydanticResource
        maxDiff = None

        def _run_test_parse_resource(self):
            self.assertEqual(
                self.resource.model_validate(self.dictionary),
                self.resource,
            )

        def _run_test_output_resource(self):
            self.assertDictEqual(self.dictionary, self.resource.model_dump())

        @classmethod
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)
            if cls.__name__ != "Base":
                setattr(cls, f"test_parse_{cls.__name__}", cls._run_test_parse_resource)
                setattr(cls, f"test_output_{cls.__name__}", cls._run_test_output_resource)


class TestPydanticModelOutputForSimulation(TestCase):
    # This test class is used for Simulation models since they only get dumped to JSON
    # and never parsed from dict to models.
    # All test classes that inherit from TestPydanticModelOutputForSimulation.Base will
    # get a test for outputting to dict.
    # Using an inner class prevents the base itself from being discovered

    class Base(TestCase, Generic[PydanticResource]):
        dictionary: dict[str, Any]
        resource: PydanticResource
        maxDiff = None

        def _run_test_output_resource(self):
            self.assertDictEqual(self.dictionary, self.resource.model_dump())

        @classmethod
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)
            if cls.__name__ != "Base":
                method_name = f"test_output_{cls.__name__}"
                setattr(cls, method_name, cls._run_test_output_resource)
