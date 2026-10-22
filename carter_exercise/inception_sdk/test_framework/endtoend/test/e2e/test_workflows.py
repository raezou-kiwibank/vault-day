# standard libs
import logging
import os

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend

log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

endtoend.testhandle.WORKFLOWS = {
    "simple_workflow": "inception_sdk/test_framework/endtoend/test/e2e/input/"
    "workflows/simple_workflow.yaml"
}


class TestWorkflowHelper(endtoend.End2Endtest):

    def test_workflow_definition_is_created(self):
        workflow_definition_id = endtoend.testhandle.workflow_definition_id_mapping[
            "simple_workflow"
        ]
        workflow_definition_version_id = endtoend.testhandle.uploaded_workflows[
            workflow_definition_id
        ]
        workflow_definition_version = endtoend.workflows_api_helper.get_workflow_definition_version(
            definition_version_id=workflow_definition_version_id
        )
        self.assertNotEqual("", workflow_definition_version)
