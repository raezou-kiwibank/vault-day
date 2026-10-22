# standard libs
import json
import logging
import os
import uuid
from datetime import datetime, timezone

# inception sdk
from inception_sdk.test_framework.contracts.simulation.utils import SimulationTestCase

# Mapping of logger name suffix to filename suffix
LOGGER_NAME_SUFFIX_TO_FILE_SUFFIX_MAPPING = {
    ".sim_test_request_logger": ".sim.request.debug",
    ".sim_test_response_logger": ".sim.response.debug",
}
VAULT_CALLER_PREFIX = "inception_sdk.test_framework.contracts.simulation.vault_caller"


class DebuggerTest(SimulationTestCase):
    def setUp(self):
        # store original state of loggers
        self._logger_original_state = {
            suffix: {"level": logging.INFO, "handlers": [], "propagate": True}
            for suffix in LOGGER_NAME_SUFFIX_TO_FILE_SUFFIX_MAPPING
        }
        self._logfile_prefix = uuid.uuid4().hex
        self._files_before_start = os.listdir("/tmp/")
        return super().setUp()

    def tearDown(self):
        # reset logger and handler and their levels
        for logger_suffix, state in self._logger_original_state.items():
            logger_name = VAULT_CALLER_PREFIX + logger_suffix
            logger = logging.getLogger(logger_name)
            logger.setLevel(state["level"])
            logger.propagate = state["propagate"]
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                logger.removeHandler(handler)
            for handler in state["handlers"]:
                logger.addHandler(handler)

        # clean up tempfile so as not to clutter the /tmp/ folder
        _files_after_test = os.listdir("/tmp/")
        difference_in_files = set(self._files_before_start).difference(set(_files_after_test))
        for new_filename in difference_in_files:
            if any(
                [
                    new_filename.endswith(log_filename_suffix)
                    for log_filename_suffix in LOGGER_NAME_SUFFIX_TO_FILE_SUFFIX_MAPPING.values()
                ]
            ):
                os.remove(f"/tmp/{new_filename}")
        return super().tearDown()

    def test_info_does_not_dump_response_to_file(self):
        """
        Test that simulation tests with INFO log level will not log responses
        """
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)
        events = []

        dumpfiles_before = os.listdir("/tmp/")

        for logger_suffix, logfile_suffix in LOGGER_NAME_SUFFIX_TO_FILE_SUFFIX_MAPPING.items():
            logger_name = VAULT_CALLER_PREFIX + logger_suffix
            logger = logging.getLogger(logger_name)

            handler = logging.FileHandler(
                f"/tmp/{self._logfile_prefix}{logfile_suffix}",
                mode="w",
            )  # whatever path the user wants to put
            handler.setLevel(logging.INFO)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

        self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids=["1"],
        )

        dumpfiles_after = os.listdir("/tmp/")
        difference_in_files = set(dumpfiles_after).difference(set(dumpfiles_before))

        # assert that if there are log files, they are empty
        for suffix in LOGGER_NAME_SUFFIX_TO_FILE_SUFFIX_MAPPING.values():
            relevant_files = [
                filename for filename in difference_in_files if filename.endswith(suffix)
            ]
            for filename in relevant_files:
                with open("/tmp/" + filename, "r") as f:
                    file_contents = f.read()
                self.assertTrue(file_contents == "")

    def test_debug_logs_request_and_response_to_file(self):
        """
        Test that simulation tests with DEBUG log level will log requests and responses
        """
        start = datetime(year=2019, month=1, day=1, tzinfo=timezone.utc)
        end = datetime(year=2019, month=1, day=2, tzinfo=timezone.utc)
        events = []

        dumpfiles_before = os.listdir("/tmp/")

        for logger_suffix, logfile_suffix in LOGGER_NAME_SUFFIX_TO_FILE_SUFFIX_MAPPING.items():
            logger_name = VAULT_CALLER_PREFIX + logger_suffix
            logger = logging.getLogger(logger_name)

            # clear handlers to prevent logging to terminal unnecessarily
            for old_handler in logger.handlers:
                logger.removeHandler(old_handler)

            file_handler = logging.FileHandler(
                f"/tmp/{self._logfile_prefix}{logfile_suffix}", mode="w"
            )  # can be set to any path the user wants, but we use /tmp/ in this case

            # set log levels of filehandler to DEBUG to trigger logging to file
            logger.setLevel(logging.DEBUG)
            file_handler.setLevel(logging.DEBUG)
            logger.propagate = False  # prevent file handler from being added to root logger
            logger.addHandler(file_handler)

        self.client.simulate_smart_contract(
            start_timestamp=start,
            end_timestamp=end,
            events=events,
            internal_account_ids=["1"],
        )

        # get logfile names
        dumpfiles_after = os.listdir("/tmp/")
        difference_in_files = set(dumpfiles_after).difference(set(dumpfiles_before))

        for suffix in LOGGER_NAME_SUFFIX_TO_FILE_SUFFIX_MAPPING.values():
            relevant_files = [
                filename for filename in difference_in_files if filename.endswith(suffix)
            ]
            for filename in relevant_files:
                with open("/tmp/" + filename, "r") as f:
                    file_contents = f.read().strip().split("\n")
                    is_parsable = True
                    for line in file_contents:
                        try:
                            json.loads(line)
                        except ValueError:
                            is_parsable = False
                        self.assertTrue(is_parsable)
