# standard libs
from datetime import datetime

# inception sdk
import inception_sdk.vault.core_api as core_api
import inception_sdk.vault.sim_api.contract_sim as sim
from inception_sdk.vault.test.common import UTC, TestPydanticModelOutputForSimulation


class TestCreateParameterValueHierarchyNode(
    TestPydanticModelOutputForSimulation.Base[sim.Instruction]
):
    dictionary = dict(
        timestamp="2024-12-31T00:00:00+00:00",
        create_parameter_value_hierarchy_node=dict(
            parameter_value_hierarchy_node=dict(
                id="parameter_value_hierarchy_node_id",
                name="parameter_value_hierarchy_node_name",
                parent_id="parameter_value_hierarchy_node_parent_id",
                metadata={"some_key": "some-value"},
            ),
        ),
    )
    resource = sim.Instruction(
        timestamp=datetime(2024, 12, 31, tzinfo=UTC),
        instruction=sim.CreateParameterValueHierarchyNode(
            parameter_value_hierarchy_node=core_api.CreateParameterValueHierarchyNode(
                id="parameter_value_hierarchy_node_id",
                name="parameter_value_hierarchy_node_name",
                parent_id="parameter_value_hierarchy_node_parent_id",
                metadata={"some_key": "some-value"},
            ),
        ),
    )
