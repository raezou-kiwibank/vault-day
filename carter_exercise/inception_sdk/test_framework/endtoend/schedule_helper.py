# Copyright @ 2021 Thought Machine Group Limited. All rights reserved.
# standard libs
import logging
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from dateutil import parser
from dateutil.relativedelta import relativedelta
from enum import Enum
from typing import overload

# third party
from semantic_version import Version

# inception sdk
import inception_sdk.test_framework.endtoend as endtoend
import inception_sdk.vault.core_api as core_api
from inception_sdk.test_framework.endtoend.kafka_helper import kafka_only_helper, wait_for_messages

log = logging.getLogger(__name__)
logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"),
    format="%(asctime)s.%(msecs)03d - %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


SCHEDULER_OPERATION_EVENTS_TOPIC = "vault.core_api.v1.scheduler.operation.events"
SCHEDULER_TICK_TIME = 20
SCHEDULE_STATUS_OVERRIDE_START_TIMESTAMP = datetime.min.replace(tzinfo=timezone.utc).isoformat()
SCHEDULE_STATUS_OVERRIDE_END_TIMESTAMP = datetime.max.replace(
    microsecond=0, tzinfo=timezone.utc
).isoformat()


class ResourceType(str, Enum):
    PLAN = "PLAN"
    ACCOUNT = "ACCOUNT"


class AccountScheduleTagStatusOverride(str, Enum):
    NO_OVERRIDE = "ACCOUNT_SCHEDULE_TAG_SCHEDULE_STATUS_OVERRIDE_NO_OVERRIDE"
    ENABLED = "ACCOUNT_SCHEDULE_TAG_SCHEDULE_STATUS_OVERRIDE_TO_ENABLED"
    FAST_FORWARD = "ACCOUNT_SCHEDULE_TAG_SCHEDULE_STATUS_OVERRIDE_TO_FAST_FORWARDED"
    SKIPPED = "ACCOUNT_SCHEDULE_TAG_SCHEDULE_STATUS_OVERRIDE_TO_SKIPPED"


def _filter_and_transform_schedules(
    schedules: dict[str, dict[str, str]],
    resource_id: str,
    resource_type: ResourceType,
    statuses_to_exclude: list[str] | None = None,
) -> dict[str, dict[str, str]]:
    """
    Transforms schedules into a dictionary keyed by contract/supervisor contract event_type,
    removing schedules with specified statuses in the process. If multiple schedules have the same
    name, only the latest schedule with that name is returned.
    :param schedules: The schedules to filter/transform.
    :param resource_id: The schedules' account id or plan id.
    :param resource_type: The ResourceType of the id that was passed in.
    :param statuses_to_exclude: Optional list of schedules statuses to exclude.
     None Defaults to ["SCHEDULE_STATUS_DISABLED"]
    """

    # Schedule display name for v4 is of format "<RESOURCE_ID>:<EVENT_TYPE>"
    display_name_format = f"{resource_id or ''}:"

    if statuses_to_exclude is None:
        statuses_to_exclude = statuses_to_exclude or ["SCHEDULE_STATUS_DISABLED"]

    output_schedules = {}
    sorted_schedules = dict(
        sorted(
            schedules.items(),
            key=lambda x: parser.parse(x[1]["create_timestamp"]).timestamp(),
        )
    )
    for _, schedule_details in sorted_schedules.items():
        if schedule_details["status"] not in statuses_to_exclude:
            if schedule_details["display_name"].startswith(display_name_format):
                account_schedule_name = schedule_details["display_name"].replace(
                    f"{display_name_format}", ""
                )
                output_schedules[account_schedule_name] = schedule_details

    return output_schedules


def get_account_schedules(
    account_id: str, statuses_to_exclude: list[str] | None = None
) -> dict[str, dict[str, str]]:
    """
    Fetches all schedules for a given account, optionally excluding certain schedule statuses
    :param account_id: the account to fetch schedules for
    :param statuses_to_exclude: the statuses to exclude from the response. Set to empty list to
    disable filtering. None Defaults to ["SCHEDULE_STATUS_DISABLED"]
    :return: a dictionary of schedules keyed by their event type
    """

    account_schedule_assocs = endtoend.core_api_helper.get_account_schedule_assocs(account_id)
    if not account_schedule_assocs:
        return {}

    account_schedule_ids = set(assoc["schedule_id"] for assoc in account_schedule_assocs)
    response_account_schedules = endtoend.core_api_helper.batch_get_schedules(account_schedule_ids)

    return _filter_and_transform_schedules(
        response_account_schedules,
        resource_id=account_id,
        resource_type=ResourceType.ACCOUNT,
        statuses_to_exclude=statuses_to_exclude,
    )


def get_plan_schedules(
    plan_id: str, statuses_to_exclude: list[str] | None = None
) -> dict[str, dict[str, str]]:
    """
    Fetches all schedules for a given plan, optionally excluding certain schedule statuses
    :param plan_id: the plan to fetch schedules for
    :param statuses_to_exclude: the statuses to exclude from the response. Set to empty list to
    disable filtering. None Defaults to ["SCHEDULE_STATUS_DISABLED"]
    :return: a dictionary of schedules keyed by their event type
    """

    plan_schedules = endtoend.core_api_helper.get_plan_schedules(plan_id)
    if not plan_schedules:
        return {}

    # plan-schedules endpoint returns partial schedule info, so we still want to enrich from
    # schedule endpoint
    schedule_ids = set(schedule["id"] for schedule in plan_schedules)
    enriched_plan_schedules = endtoend.core_api_helper.batch_get_schedules(schedule_ids)

    return _filter_and_transform_schedules(
        enriched_plan_schedules,
        resource_id=plan_id,
        resource_type=ResourceType.PLAN,
        statuses_to_exclude=statuses_to_exclude,
    )


@kafka_only_helper
def wait_for_schedule_operation_events(
    tag_names: list[str],
    wait_for_timestamp: datetime | None = None,
    inter_message_timeout: int = 90,
    matched_message_timeout: int = 90,
):
    """
    Listen to the vault.core_api.v1.scheduler.operation.events Kafka topic for updates to schedule
    execution. A response from this topic indicates that all schedules associated with an account
    schedule tag have finished being processed by the scheduler.
    :param tag_names: Account schedule tag names to listen for a completion event
    :param wait_for_timestamp: Set an expected completion timestamp for the completion event. E.g.
    if you are skipping multiple months worth of schedules and only want the response for a specific
    date.
    :param inter_message_timeout: a maximum time to wait between receiving any messages from the
    consumer (0 for no timeout)
    :param matched_message_timeout: a maximum time to wait between receiving matched messages from
    the consumer (0 for no timeout)
    """
    consumer = endtoend.testhandle.kafka_consumers[SCHEDULER_OPERATION_EVENTS_TOPIC]

    mapped_tags = {tag: None for tag in set(tag_names)}

    def matcher(event_msg, unique_message_ids):
        # we also get account_update_created events on this topic
        tag_name = event_msg["operation_created"]["operation"]["tag_name"]
        event_request_id = event_msg["event_id"]
        if tag_name in unique_message_ids:
            if wait_for_timestamp:
                completed_run_timestamp = parser.parse(
                    event_msg["operation_created"]["operation"]["completed_run_timestamp"]
                )
                if completed_run_timestamp == wait_for_timestamp:
                    return tag_name, event_request_id, True
            else:
                return tag_name, event_request_id, True
        return "", event_request_id, False

    log.info(f"Waiting for {len(mapped_tags)} operation events: {mapped_tags}")

    unmatched_events = wait_for_messages(
        consumer,
        matcher=matcher,
        callback=None,
        unique_message_ids=mapped_tags,
        inter_message_timeout=inter_message_timeout,
        matched_message_timeout=matched_message_timeout,
    )

    if len(unmatched_events) > 0:
        raise Exception(
            f"Failed to retrieve {len(unmatched_events)} operation events"
            f" for tags: {', '.join(unmatched_events.keys())}"
        )

    log.info("Got all operation events")


def fast_forward_tag(paused_tag_id: str, fast_forward_to_date: datetime) -> None:
    """
    Fast forward a tag to the specified date
    :param paused_tag_id: unmapped id of the paused tag to fast forward.
    :param fast_forward_to_date: the date to fast forward to
    """
    fast_forward_to_date = fast_forward_to_date.replace(tzinfo=timezone.utc)
    log.info(f"Fast-forwarding {paused_tag_id} to {fast_forward_to_date}")
    endtoend.core_api_helper.update_account_schedule_tag(
        account_schedule_tag_id=paused_tag_id,
        schedule_status_override=AccountScheduleTagStatusOverride.FAST_FORWARD.value,
        schedule_status_override_end_timestamp=fast_forward_to_date.isoformat(),
    )


def skip_scheduled_jobs_and_wait(
    schedule_name: str,
    skip_start_date: datetime,
    skip_end_date: datetime,
    resource_id: str,
    resource_type: ResourceType,
    initial_wait: int = 0,
) -> None:
    """
    Skips jobs for a certain schedule tag between two dates and waits until this action is complete
    :param schedule_name: Name of the Schedule, as per the contract/supervisor contract event type
    :param skip_start_date: The timestamp from which to begin skipping execution.
    :param skip_end_date: The timestamp at which to stop skipping execution. This should match the
    logical timestamp for the last skipped job and is used to verify the expected jobs were skipped.
    :param resource_id: The account or plan id that the schedule belongs to
    :param resource_type: Indicates whether the schedule belongs to an account or plan
    :param initial_wait: an initial number of seconds to wait for before starting to poll. This is
    useful if we know there is a long delay before the results will ever be met. For example, if
    waiting for 30 jobs to skip, we know there is a 30*20 wait just for those jobs to be published.
    This is only applicable when using the REST API, not when using Kafka
    """
    # TODO: could we refactor this a bit as we repeatedly fetch schedules for a given name and
    # account/plan id?
    id_and_type = f"{resource_type.value=} {resource_id=}"
    log.info(
        f"Skipping jobs for {schedule_name=} between {skip_start_date=} and {skip_end_date=} for "
        f"{id_and_type}"
    )

    if resource_type == ResourceType.ACCOUNT:
        schedules = get_account_schedules(resource_id)
    else:
        schedules = get_plan_schedules(resource_id)

    if schedule_name not in schedules:
        raise KeyError(f"No enabled {schedule_name=} for {id_and_type}")

    schedule = schedules[schedule_name]
    schedule_id = schedule["id"]

    if len(schedule["tags"]) == 0:
        raise ValueError(f"No tags found on {schedule_name=} {schedule_id=} for {id_and_type}")
    elif len(schedule["tags"]) > 1:
        log.info(
            f"Found multiple tags on {schedule_name=} {schedule_id=} for {id_and_type}. First "
            f"will be used"
        )
    schedule_tag_id = schedule["tags"][0]

    skip_scheduled_jobs_between_dates(
        schedule_tag_id=schedule_tag_id,
        skip_start_date=skip_start_date,
        skip_end_date=skip_end_date,
    )

    wait_for_schedule_job(
        schedule_tag_id=schedule_tag_id,
        schedule_id=schedule_id,
        job_statuses=["JOB_STATUS_SKIPPED"],
        initial_wait=initial_wait,
        expected_run_time=skip_end_date,
    )


@dataclass
class Job:
    tag_id: str
    schedule_id: str
    effective_date: datetime


def trigger_and_wait_for_schedule_jobs_until(
    schedule_name: str,
    resource_id: str,
    resource_type: ResourceType,
    trigger_until: datetime,
) -> list[Job]:
    """Triggers execution and waits for completion of jobs for a schedule belonging to an account
    or plan, until the specified datetime, inclusive. Each job is triggered and waited for
    individually.

    :param schedule_name: schedule name to trigger jobs for (EventType name in contract API)
    :param resource_id: the id of the account/plan that the schedule belongs to
    :param resource_type: whether the resource is an account or plan
    :param trigger_until: the upper limit for triggered jobs' effective datetime, inclusive
    :return: A list of all the triggered jobs. This could be empty if the next run time of the
    schedule is > trigger_until before this function is called.
    """

    triggered_jobs: list[Job] = []
    log.info(
        f"Triggering jobs for {schedule_name=} for {resource_type.value=} {resource_id=}"
        f" until {trigger_until}"
    )

    while True:
        triggered_job = trigger_next_schedule_job(
            schedule_name=schedule_name,
            resource_id=resource_id,
            resource_type=resource_type,
            max_effective_date=trigger_until,
        )

        # No job is triggered if the schedule has no more runs (e.g. disabled) or
        # the next run timestamp is > trigger_until
        if triggered_job:
            triggered_jobs.append(triggered_job)
            wait_for_schedule_job(job=triggered_job)
        else:
            return triggered_jobs


def trigger_next_schedule_job_and_wait(
    schedule_name: str,
    account_id: str | None = None,
    plan_id: str | None = None,
    effective_date: datetime | None = None,
) -> Job:
    """
    Triggers the next execution of a specified schedule dependent on its current next_run_timestamp
    and waits until the associated job reaches a terminal status
    :param schedule_name: schedule name to trigger jobs for (EventType name in contract API)
    :param account_id: The schedule's account id. Only one of account_id or plan_id can be passed in
    :param plan_id: The schedule's plan id. Only one of account_id or plan_id can be passed in
    :param effective_date: An optional expected effective date for the job to trigger. If this does
    not match the next_run_timestamp for the schedule, a ValueError is raised
    :return: The triggered job
    :raises: ValueError if no job was triggered
    """

    # TODO(INC-6971): remove this logic and update method interface instead
    if account_id:
        resource_id = account_id
        resource_type = ResourceType.ACCOUNT
    elif plan_id:
        resource_id = plan_id
        resource_type = ResourceType.PLAN
    else:
        raise ValueError(f"Must specify an account_id or plan_id. Got {plan_id=} and {account_id=}")

    triggered_job = trigger_next_schedule_job(
        schedule_name=schedule_name,
        resource_id=resource_id,
        resource_type=resource_type,
        effective_date=effective_date,
    )

    # it's possible no job was triggered (e.g. schedule has None next_run_timestamp)
    if triggered_job is None:
        raise ValueError(
            f"No job to wait for found on {schedule_name=} for {resource_type.value} {resource_id}"
        )

    wait_for_schedule_job(job=triggered_job)
    return triggered_job


def trigger_next_schedule_job_or_raise(
    *,
    schedule_name: str,
    resource_id: str,
    resource_type: ResourceType,
    effective_date: datetime | None = None,
    max_effective_date: datetime | None = None,
) -> Job:
    """
    Triggers the next execution of a specified schedule dependent on its current next_run_timestamp.

    :param schedule_name: Name of the Schedule, as per the contract/supervisor contract event type
    :param account_id: The schedule's account id. Only one of account_id or plan_id can be passed in
    :param plan_id: The schedule's plan id. Only one of account_id or plan_id can be passed in
    :param effective_date: An optional expected effective date for the job to trigger. If this does
    not match the next_run_timestamp for the schedule, a ValueError is raised
    :param max_effective_date: An optional max value for the effective date for the job to trigger.
    If this is less than the schedule's next_run_timestamp, no job is triggered and None is returned
    :return: The triggered job, or None if no job was triggered
    :return: The triggered job
    :raises: ValueError if no job was triggered
    """
    triggered_job = trigger_next_schedule_job(
        schedule_name=schedule_name,
        resource_id=resource_id,
        resource_type=resource_type,
        effective_date=effective_date,
        max_effective_date=max_effective_date,
    )

    # it's possible no job was triggered (e.g. schedule has None next_run_timestamp)
    if triggered_job is None:
        raise ValueError(
            f"No job to wait for found on {schedule_name=} for {resource_type.value} {resource_id}"
        )

    return triggered_job


def trigger_next_schedule_job(
    schedule_name: str,
    resource_id: str,
    resource_type: ResourceType,
    effective_date: datetime | None = None,
    max_effective_date: datetime | None = None,
) -> Job | None:
    """
    Triggers the next execution of a specified schedule dependent on its current next_run_timestamp.
    If possible use the `trigger_next_schedule_job_and_wait` wrapper.
    :param schedule_name: Name of the Schedule, as per the contract/supervisor contract event type
    :param account_id: The schedule's account id. Only one of account_id or plan_id can be passed in
    :param plan_id: The schedule's plan id. Only one of account_id or plan_id can be passed in
    :param effective_date: An optional expected effective date for the job to trigger. If this does
    not match the next_run_timestamp for the schedule, a ValueError is raised
    :param max_effective_date: An optional max value for the effective date for the job to trigger.
    If this is less than the schedule's next_run_timestamp, no job is triggered and None is returned
    :return: The triggered job, or None if no job was triggered
    """
    id_and_type = f"{resource_type.value=} {resource_id=}"
    log.info(f"Triggering next job for {schedule_name=} for {id_and_type}")

    if resource_type == ResourceType.ACCOUNT:
        schedules = get_account_schedules(resource_id)
    else:
        schedules = get_plan_schedules(resource_id)

    if schedule_name not in schedules:
        raise KeyError(f"No enabled {schedule_name=} for {id_and_type}")

    schedule = schedules[schedule_name]
    schedule_id = schedule["id"]

    if not schedule["next_run_timestamp"]:
        log.info(
            f"No next run timestamp on schedule {schedule['id']} in status {schedule['status']}"
        )
        return None

    next_run_time = parser.parse(schedule["next_run_timestamp"]).replace(tzinfo=timezone.utc)

    if max_effective_date and next_run_time > max_effective_date:
        log.info(f"No job to trigger as {next_run_time=} > {max_effective_date=}")
        return None
    elif effective_date and effective_date != next_run_time:
        raise ValueError(f"{effective_date=} does not match the actual {next_run_time=}")

    # We could use the tags as per endtoend.testhandle.controlled_schedule_tags, but there's also
    # value in using the actual value we found on the schedule
    if len(schedule["tags"]) == 0:
        raise ValueError(f"No tags found on {schedule_name=} {schedule_id=} for {id_and_type}")
    elif len(schedule["tags"]) > 1:
        log.info(
            f"Found multiple tags on {schedule_name=} {schedule_id=} for {id_and_type}. "
            f"First will be used"
        )
    schedule_tag_id = schedule["tags"][0]

    if effective_date and effective_date != next_run_time:
        raise ValueError(f"{effective_date=} does not match the actual {next_run_time=}")

    if endtoend.testhandle.vault_version >= Version("5.3.0"):
        # Do this before the tag is updated so the job is guaranteed to get the minimum obs time
        update_processing_group_minimum_observation_timestamp(processing_group_id="DEFAULT")

    # max granularity in scheduler is 1 second
    after_next_run_time = next_run_time + relativedelta(seconds=1)
    if after_next_run_time > datetime.now(tz=timezone.utc):
        fast_forward_tag(paused_tag_id=schedule_tag_id, fast_forward_to_date=after_next_run_time)
    else:
        update_tag_test_pause_at_timestamp(
            schedule_tag_id=schedule_tag_id, test_pause_at_timestamp=after_next_run_time
        )
    return Job(schedule_tag_id, schedule_id, next_run_time)


def update_processing_group_minimum_observation_timestamp(
    processing_group_id: str,
) -> core_api.ProcessingGroup:
    """
    Updates a processing group's minimum observation timestamp by updating it to ACTIVE
    and `schedules_observe_balances_at_unpause_time` set to True. This works regardless of
    whether the group is currently PAUSED or ACTIVE, but will also update the group's status if it
    is currently PAUSED. This isn't considered an issue for testing purposes, because we rely on
    account schedule tags to prevent schedule jobs from being published.

    :param processing_group_id: id of the processing group to update
    :return: the processing group after relevant updates
    """
    log.info(f"Updating processing group {processing_group_id} observation time to ~now")
    return endtoend.core_api_helper.update_processing_group(
        processing_group_id=processing_group_id,
        update_request=core_api.UpdateProcessingGroupRequestBody(
            request_id=str(uuid.uuid4()),
            processing_group=core_api.ProcessingGroupUpdate(
                status=core_api.ProcessingGroupStatus.ACTIVE
            ),
            minimum_observation_timestamp_update_options=(
                core_api.MinimumObservationTimestampUpdateOptions(
                    schedules_observe_balances_at_unpause_time=True
                )
            ),
            update_mask=core_api.UpdateMask(paths=["status"]),
        ),
    )


@overload
def wait_for_schedule_job(
    *,
    schedule_tag_id: str | None = None,
    schedule_id: str | None = None,
    expected_run_time: datetime | None = None,
    initial_wait: int = 70,
    job_statuses: list[str] | None = None,
) -> None: ...
@overload
def wait_for_schedule_job(
    *,
    job: Job,
    initial_wait: int = 70,
    job_statuses: list[str] | None = None,
) -> None: ...
def wait_for_schedule_job(
    schedule_tag_id: str | None = None,
    schedule_id: str | None = None,
    expected_run_time: datetime | None = None,
    initial_wait: int = 70,
    job_statuses: list[str] | None = None,
    job: Job | None = None,
) -> None:
    """
    Waits for a schedule job to reach a terminal status, via schedule operation event if kafka
    is in use, or by polling the REST API for job status.
    If possible use the `trigger_next_schedule_job_and_wait` wrapper.

    :param schedule_tag_id: id of the schedule tag that the operation event should be emitted for.
    Must be provided to use kafka-based helpers. If omitted, defaults to REST API-based helper
    :param schedule_id: id of the schedule that the job should be emitted for. Only used if kafka
    is not in use.
    :param expected_run_time: the expected run time for the job to wait for
    :param initial_wait: time in seconds to wait before expecting the job with logical timestamp
    equal to expected_run_time to complete.
    :param job_statuses: jobs to consider as terminal when polling. Only used if kafka is not in
    use. Defaults to JOB_STATUS_SUCCEEDED and JOB_STATUS_FAILED
    """

    if job is not None:
        schedule_tag_id = job.tag_id
        schedule_id = job.schedule_id
        expected_run_time = job.effective_date

    if endtoend.testhandle.use_kafka and schedule_tag_id:
        wait_for_schedule_operation_events(
            tag_names=[schedule_tag_id],
            wait_for_timestamp=expected_run_time,
            # provides similar max wait to the retry approach with initial_wait and then x retries
            inter_message_timeout=initial_wait + 20,
            matched_message_timeout=initial_wait + 20,
        )
    else:
        if not schedule_id:
            raise ValueError(
                f"Not using kafka to wait for schedule job ({endtoend.testhandle.use_kafka=} and "
                f"{schedule_tag_id=} and no schedule_id provided {schedule_id=}"
            )
        if initial_wait > 0:
            time.sleep(initial_wait)
        job_statuses = job_statuses or ["JOB_STATUS_SUCCEEDED", "JOB_STATUS_FAILED"]
        endtoend.helper.retry_call(
            func=_check_jobs_status,
            f_args=[schedule_id, expected_run_time, job_statuses],
            expected_result=True,
            back_off=2,
            max_retries=7,
        )


def _check_jobs_status(
    schedule_id: str,
    effective_date: datetime | None = None,
    expected_status: list[str] | None = None,
) -> bool:
    """
    Checks status of all jobs in a schedule.
    :param schedule_id: The ID of the Schedule.
    :param expected_status: All jobs must be of this status.
    :param effective_date: An optional job effective date, helps filter further in case multiple.
    jobs are triggered in the test. if left blank it will check all the dates.
    :return: True if jobs with schedule_timestamp == effective date status is present in
    expected_status else return False, in case no valid jobs were found will also return false.
    """

    expected_status = expected_status or ["JOB_STATUS_SUCCEEDED", "JOB_STATUS_FAILED"]
    result = endtoend.core_api_helper.get_jobs(schedule_id)
    flag_no_jobs = True

    for job in result:
        job_time_stamp = job["schedule_timestamp"]
        job_time_stamp = parser.parse(job_time_stamp)
        if effective_date is None or effective_date == job_time_stamp:
            flag_no_jobs = False
            if job["status"].upper() not in expected_status:
                return False
    if flag_no_jobs:
        return False
    return True


def update_tag_test_pause_at_timestamp(schedule_tag_id: str, test_pause_at_timestamp: datetime):
    """
    Updates the test_pause_at_timestamp for a given schedule tag ID as defined in the Smart
    Contract. Maps the provided schedule tag to the actual E2E schedule tag used in the test
    before sending the request.
    :param schedule_tag_id: The schedule tag ID as defined in the Smart Contract.
    :param test_pause_at_timestamp: The timestamp to which normal execution should run
    before pausing.
    """
    test_pause_at_timestamp = test_pause_at_timestamp.replace(tzinfo=timezone.utc)
    log.info(f"Updating test_pause_at_timestamp to {test_pause_at_timestamp} for {schedule_tag_id}")
    endtoend.core_api_helper.update_account_schedule_tag(
        account_schedule_tag_id=schedule_tag_id,
        test_pause_at_timestamp=test_pause_at_timestamp.isoformat(),
    )


def skip_scheduled_jobs_between_dates(
    schedule_tag_id: str,
    skip_start_date: datetime,
    skip_end_date: datetime,
) -> None:
    """
    Skips all schedule executions for given schedule tag between the provided dates. Execution will
    be paused at the skip_end_date.
    :param schedule_tag_id: The schedule tag ID as defined in the Smart Contract.
    :param skip_start_date: The timestamp from which to begin skipping execution.
    :param skip_end_date: The timestamp at which to stop skipping execution.
    """

    log.info(f"Skipping {schedule_tag_id} from {skip_start_date}" f" to {skip_end_date}")

    endtoend.core_api_helper.update_account_schedule_tag(
        account_schedule_tag_id=schedule_tag_id,
        schedule_status_override_start_timestamp=skip_start_date.isoformat(),
        schedule_status_override_end_timestamp=skip_end_date.isoformat(),
        schedule_status_override=AccountScheduleTagStatusOverride.SKIPPED,
        # the pause_at_timestamp must be == skip end timestamp to not interfere
        test_pause_at_timestamp=skip_end_date.isoformat(),
    )
