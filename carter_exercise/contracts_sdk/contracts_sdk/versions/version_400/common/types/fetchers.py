from functools import lru_cache
from typing import Optional, Union

from .enums import (
    DateTimeView,
    DefinedDateTime,
)
from ...common.docs import (
    _common_docs_path,
    _smart_contracts_docs_path,
    _supervisor_contracts_docs_path,
)
from .....utils import exceptions, symbols, types_utils
from .filters import (
    
    BalancesFilter,
    CalendarsFilter,
    EventTypesFilter,
    FlagsFilter,
    ParametersFilter,
)

from .periods import Period



from .time_operations import RelativeDateTime

# Data Fetcher classes.

TIMEZONE_DOCSTRING = f"""
    Evaluated in UTC, regardless of the `events_timezone` of the
    [Account]({_smart_contracts_docs_path}vault#events_timezone) or
    [Plan]({_supervisor_contracts_docs_path}vault#events_timezone).
"""
AT_ATTRIBUTE_COMMON_TEMPLATE = (
    lambda data_type: f"The time at which the {data_type} is observed. {TIMEZONE_DOCSTRING}"
)
END_ATTRIBUTE_COMMON_DOCSTRING = f"""
    The end time of the interval window. Can either be defined relative to the effective time or
    the interval start time (using
    [RelativeDateTime]({_common_docs_path}classes/#RelativeDateTime)), or as a time defined in Vault
    Core (using [DefinedDateTime]({_common_docs_path}enums/#DefinedDateTime)).{TIMEZONE_DOCSTRING}
    If no end datetime is set or if it is set to `None`, this will default to
    [DefinedDateTime]({_common_docs_path}enums/#DefinedDateTime).
    If set to `LIVE`, this will fetch data up to the hook's execution datetime. The value
    `DefinedDateTime.INTERVAL_START` is **not** allowed.
"""


class IntervalFetcher(types_utils.ContractsLanguageDunderMixin):
    def __init__(
        self,
        *,
        fetcher_id: str,
        start: Union[RelativeDateTime, DefinedDateTime],
        end: Optional[Union[RelativeDateTime, DefinedDateTime]] = DefinedDateTime.LIVE,
    ):
        self.fetcher_id = fetcher_id
        self.start = start
        self.end = end
        self._validate_attributes()

    def _validate_attributes(self):
        class_name = self.__class__.__name__

        types_utils.validate_type(
            self.fetcher_id,
            str,
            hint="str",
            check_empty=True,
            prefix=f"{class_name}.fetcher_id",
        )

        types_utils.validate_type(
            self.start,
            (DefinedDateTime, RelativeDateTime),
            hint="Union[DefinedDateTime, RelativeDateTime]",
            prefix=f"{class_name}.start",
        )
        if (
            isinstance(self.start, RelativeDateTime)
            and self.start.origin != DefinedDateTime.EFFECTIVE_DATETIME
        ):
            raise exceptions.InvalidSmartContractError(
                f"{class_name} 'start' origin value must be set to "
                "'DefinedDateTime.EFFECTIVE_DATETIME'"
            )

        if self.start == DefinedDateTime.LIVE:
            raise exceptions.InvalidSmartContractError(
                f"{class_name} 'start' cannot be set to 'DefinedDateTime.LIVE'"
            )

        if self.start == DefinedDateTime.INTERVAL_START:
            raise exceptions.InvalidSmartContractError(
                f"{class_name} 'start' cannot be set to 'DefinedDateTime.INTERVAL_START'"
            )

        types_utils.validate_type(
            self.end,
            (DefinedDateTime, RelativeDateTime),
            hint="Union[DefinedDateTime, RelativeDateTime]",
            is_optional=True,
            prefix=f"{class_name}.end",
        )
        if self.end == DefinedDateTime.INTERVAL_START:
            raise exceptions.InvalidSmartContractError(
                f"{class_name} 'end' cannot be set to 'DefinedDateTime.INTERVAL_START'"
            )

    @classmethod
    @lru_cache()
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return [
            types_utils.ValueSpec(
                name="fetcher_id",
                type="str",
                docstring=f"""
                    The ID for this fetcher. This can be used in the
                    [@fetch_account_data decorator]({_common_docs_path}decorators/#fetch_account_data)
                    to request the data window defined in this fetcher.
                """,
            ),
            types_utils.ValueSpec(
                name="start",
                type="Union[DefinedDateTime, RelativeDateTime]",
                
                docstring=f"""
                    The start time of the interval window. This can either be a
                    [DefinedDateTime]({_common_docs_path}enums/#DefinedDateTime)
                    or a [RelativeDateTime]({_common_docs_path}classes/#RelativeDateTime).
                    {TIMEZONE_DOCSTRING}
                    The values `DefinedDateTime.INTERVAL_START` and `DefinedDateTime.LIVE` are
                    **not** allowed. If the value is of type `RelativeDateTime`, its origin must
                    be set to `DefinedDateTime.EFFECTIVE_DATETIME`.
                """,
            ),
            types_utils.ValueSpec(
                name="end",
                type="Optional[Union[DefinedDateTime, RelativeDateTime]]",
                docstring=cls._get_end_attribute_docstring(),
            ),
        ]

    @classmethod
    def _get_end_attribute_docstring(cls):
        return f"""
            {END_ATTRIBUTE_COMMON_DOCSTRING} *Note*: `start` and `end` timestamps are evaluated
            at the execution time using the `effective_datetime` of the hook. If `start` is
            greater than `end`, an execution error is returned.
        """


class NonDegenerateIntervalFetcher(IntervalFetcher):
    def _validate_attributes(self):
        class_name = self.__class__.__name__
        super()._validate_attributes()
        if self.start == self.end:
            raise exceptions.InvalidSmartContractError(
                f"{class_name} 'start' cannot be equal to 'end'"
            )

    @classmethod
    def _get_end_attribute_docstring(cls):
        return f"""
            {END_ATTRIBUTE_COMMON_DOCSTRING} *Note*: if `start` is equal to `end`, an error will be
            raised at parse time. In addition, `start` and `end` timestamps are evaluated at the
            execution time using the `effective_datetime` of the hook. If `start` is greater
            than `end`, an execution error is returned.
        """


class BalancesIntervalFetcher(IntervalFetcher):
    def __init__(
        self,
        *,
        fetcher_id: str,
        start: Union[RelativeDateTime, DefinedDateTime],
        end: Optional[Union[RelativeDateTime, DefinedDateTime]] = DefinedDateTime.LIVE,
        filter: Optional[BalancesFilter] = None,
        datetime_view: Optional[DateTimeView] = None,
    ):
        self.class_name = self.__class__.__name__
        self.filter = filter
        self.datetime_view = (
            datetime_view if datetime_view is not None else DateTimeView.VALUE_DATETIME
        )
        super().__init__(fetcher_id=fetcher_id, start=start, end=end)

    def _validate_attributes(self):
        super()._validate_attributes()
        types_utils.validate_type(
            self.filter,
            BalancesFilter,
            is_optional=True,
            hint="BalancesFilter",
            prefix="BalancesIntervalFetcher.filter",
        )
        types_utils.validate_type(
            self.datetime_view,
            DateTimeView,
            is_optional=True,
            hint="DateTimeView",
            prefix="BalancesIntervalFetcher.datetime_view",
        )
        permitted_datetime_views = {
            DateTimeView.VALUE_DATETIME,
            DateTimeView.BOOKING_DATETIME,
        }
        if self.datetime_view not in permitted_datetime_views:
            raise exceptions.InvalidSmartContractError(
                f"{self.class_name} 'datetime_view' must be either "
                "DateTimeView.VALUE_DATETIME or DateTimeView.BOOKING_DATETIME"
            )

    @classmethod
    @lru_cache()
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        public_attributes = super()._public_attributes(language_code)
        public_attributes.append(
            types_utils.ValueSpec(
                name="filter",
                type="Optional[BalancesFilter]",
                docstring="An optional filter to refine the results returned by the fetcher.",
            )
        )
        public_attributes.append(
            types_utils.ValueSpec(
                name="datetime_view",
                type="Optional[DateTimeView]",
                docstring=f"""
                        The [DateTimeView]({_common_docs_path}enums/#DateTimeView) to fetch balances on,
                        must be one of `DateTimeView.VALUE_DATETIME` or `DateTimeView.BOOKING_DATETIME`.
                        If it is not set, it defaults to `DateTimeView.VALUE_DATETIME`.
                    """,
            )
        )
        return public_attributes

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name="BalancesIntervalFetcher",
            docstring="""
            A fetcher for retrieving balances data within a given interval window, inclusive of
            end time.
            """,
            public_attributes=cls._public_attributes(language_code),
            constructor=types_utils.ConstructorSpec(
                docstring="",
                args=cls._public_attributes(language_code),
            ),
        )

    @classmethod
    def _get_end_attribute_docstring(cls):
        return (
            super()._get_end_attribute_docstring()
            + f"""
            When the desired interval of the fetcher is a single timestamp (`start` == `end`), it
            is strongly advised to use a
            [BalancesObservationFetcher]({_common_docs_path}classes/#BalancesObservationFetcher)
            instead.
        """
        )


class BalancesDiscreteIntervalFetcher(NonDegenerateIntervalFetcher):
    def __init__(
        self,
        *,
        fetcher_id: str,
        start: Union[DefinedDateTime, RelativeDateTime],
        end: Optional[
            Union[DefinedDateTime, RelativeDateTime]
        ] = DefinedDateTime.EFFECTIVE_DATETIME,
        sampling_period: Period,
        filter: Optional[BalancesFilter] = None,
        datetime_view: Optional[DateTimeView] = None,
    ):
        self.class_name = self.__class__.__name__
        self.sampling_period = sampling_period
        self.filter = filter
        self.datetime_view = datetime_view if datetime_view else DateTimeView.VALUE_DATETIME
        super().__init__(fetcher_id=fetcher_id, start=start, end=end)

    def _validate_attributes(self):
        super()._validate_attributes()
        if self.end == DefinedDateTime.LIVE:
            raise exceptions.InvalidSmartContractError(
                f"{self.class_name} 'end' cannot be set to 'DefinedDateTime.LIVE'"
            )
        types_utils.validate_type(
            self.sampling_period,
            Period,
            hint="Period",
            prefix=f"{self.class_name}.sampling_period",
        )
        types_utils.validate_type(
            self.filter,
            BalancesFilter,
            is_optional=True,
            hint="BalancesFilter",
            prefix=f"{self.class_name}.filter",
        )
        types_utils.validate_type(
            self.datetime_view,
            DateTimeView,
            is_optional=True,
            hint="DateTimeView",
            prefix=f"{self.class_name}.datetime_view",
        )
        permitted_datetime_views = {
            DateTimeView.VALUE_DATETIME,
            DateTimeView.BOOKING_DATETIME,
        }
        if self.datetime_view not in permitted_datetime_views:
            raise exceptions.InvalidSmartContractError(
                f"{self.class_name} 'datetime_view' must be either "
                "DateTimeView.VALUE_DATETIME or DateTimeView.BOOKING_DATETIME"
            )

    @classmethod
    @lru_cache()
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        public_attributes = super()._public_attributes(language_code)
        public_attributes.append(
            types_utils.ValueSpec(
                name="sampling_period",
                type="Period",
                docstring=f"""
                    The [Period]({_common_docs_path}classes/#Period) that
                    specifies the fixed time between balance observations.
                """,
            )
        )
        public_attributes.append(
            types_utils.ValueSpec(
                name="filter",
                type="Optional[BalancesFilter]",
                docstring="An optional filter to refine the results returned by the fetcher.",
            )
        )
        public_attributes.append(
            types_utils.ValueSpec(
                name="datetime_view",
                type="Optional[DateTimeView]",
                docstring=f"""
                    The [DateTimeView]({_common_docs_path}enums/#DateTimeView) to fetch balances on,
                    must be one of `DateTimeView.VALUE_DATETIME` or `DateTimeView.BOOKING_DATETIME`.
                    If it is not set, it defaults to `DateTimeView.VALUE_DATETIME`.
                """,
            )
        )
        return public_attributes

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name=cls.__name__,
            docstring="""
                A fetcher for retrieving balances at periodic observation points
                within a given interval window. The observation points are determined
                by the `sampling_period`, starting from the start time (inclusive).
                If end time falls on the observation point, it is included.
            """,
            public_attributes=cls._public_attributes(language_code),
            constructor=types_utils.ConstructorSpec(
                docstring="",
                args=cls._public_attributes(language_code),
            ),
        )


class BalancesObservationFetcher(types_utils.ContractsLanguageDunderMixin):
    def __init__(
        self,
        fetcher_id: str,
        at: Union[DefinedDateTime, RelativeDateTime],
        filter: Optional[BalancesFilter] = None,
        datetime_view: Optional[DateTimeView] = None,
    ):
        self.fetcher_id = fetcher_id
        self.at = at
        self.filter = filter
        self.datetime_view = (
            datetime_view if datetime_view is not None else DateTimeView.VALUE_DATETIME
        )
        self._validate_attributes()

    def _validate_attributes(self):
        types_utils.validate_type(
            self.fetcher_id,
            str,
            check_empty=True,
            hint="str",
            prefix="BalancesObservationFetcher.fetcher_id",
        )

        types_utils.validate_type(
            self.at,
            (DefinedDateTime, RelativeDateTime),
            hint="Union[DefinedDateTime, RelativeDateTime]",
            prefix="BalancesObservationFetcher.at",
        )

        if self.at == DefinedDateTime.INTERVAL_START:
            raise exceptions.InvalidSmartContractError(
                "BalancesObservationFetcher 'at' cannot be set to 'DefinedDateTime.INTERVAL_START'"
            )
        if type(self.at) is RelativeDateTime and self.at.origin == DefinedDateTime.INTERVAL_START:
            raise exceptions.InvalidSmartContractError(
                "BalancesObservationFetcher 'at.origin' cannot be set to 'DefinedDateTime.INTERVAL_START'"
            )

        types_utils.validate_type(
            self.filter,
            BalancesFilter,
            hint="BalancesFilter",
            is_optional=True,
            prefix="BalancesObservationFetcher.filter",
        )

        types_utils.validate_type(
            self.datetime_view,
            DateTimeView,
            is_optional=True,
            hint="DateTimeView",
            prefix="BalancesObservationFetcher.datetime_view",
        )
        permitted_datetime_views = {
            DateTimeView.VALUE_DATETIME,
            DateTimeView.BOOKING_DATETIME,
            None,
        }
        if self.datetime_view not in permitted_datetime_views:
            raise exceptions.InvalidSmartContractError(
                "BalancesObservationFetcher 'datetime_view' must be either "
                "DateTimeView.VALUE_DATETIME or DateTimeView.BOOKING_DATETIME"
            )

    @classmethod
    @lru_cache()
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        public_attributes = [
            types_utils.ValueSpec(
                name="fetcher_id", type="str", docstring="The ID for this fetcher."
            ),
            types_utils.ValueSpec(
                name="at",
                type="Union[DefinedDateTime, RelativeDateTime]",
                docstring=f"""
                    {AT_ATTRIBUTE_COMMON_TEMPLATE("balances")} If the value is
                    of type `DefinedDateTime`, `DefinedDateTime.INTERVAL_START`
                    is **not** allowed. If the value is of type `RelativeDateTime`,
                    `DefinedDateTime.INTERVAL_START` is **not** allowed as the `origin`.
                """,
            ),
            types_utils.ValueSpec(
                name="filter",
                type="Optional[BalancesFilter]",
                docstring="An optional filter to refine the results returned by the fetcher.",
            ),
        ]
        public_attributes.append(
            types_utils.ValueSpec(
                name="datetime_view",
                type="Optional[DateTimeView]",
                docstring=f"""
                        The [DateTimeView]({_common_docs_path}enums/#DateTimeView) to fetch balances on,
                        must be one of `DateTimeView.VALUE_DATETIME` or `DateTimeView.BOOKING_DATETIME`.
                        If it is not set, it defaults to `DateTimeView.VALUE_DATETIME`.
                    """,
            )
        )
        return public_attributes

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name="BalancesObservationFetcher",
            docstring="A fetcher for observing balances at a given moment in time.",
            public_attributes=cls._public_attributes(language_code),
            constructor=types_utils.ConstructorSpec(
                docstring="",
                args=cls._public_attributes(language_code),
            ),
        )


class PostingsIntervalFetcher(IntervalFetcher):
    def __init__(
        self,
        *,
        fetcher_id: str,
        start: Union[RelativeDateTime, DefinedDateTime],
        end: Optional[Union[RelativeDateTime, DefinedDateTime]] = DefinedDateTime.LIVE,
    ):
        self.class_name = self.__class__.__name__
        super().__init__(fetcher_id=fetcher_id, start=start, end=end)

    def _validate_attributes(self):
        super()._validate_attributes()

    @classmethod
    @lru_cache()
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        return super()._public_attributes(language_code)

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name="PostingsIntervalFetcher",
            docstring="""
                A fetcher for retrieving postings data within a given interval window, inclusive
                of start and end time. Note that a `PostingIntervalFetcher` does not fetch postings
                that are not committed yet.
            """,
            public_attributes=cls._public_attributes(language_code),
            constructor=types_utils.ConstructorSpec(
                docstring="",
                args=cls._public_attributes(language_code),
            ),
        )


class ParametersIntervalFetcher(NonDegenerateIntervalFetcher):
    def __init__(
        self,
        *,
        fetcher_id: str,
        start: Union[RelativeDateTime, DefinedDateTime],
        end: Optional[Union[RelativeDateTime, DefinedDateTime]] = DefinedDateTime.LIVE,
        filter: Optional[ParametersFilter] = None,
    ):
        self.class_name = self.__class__.__name__
        self.filter = filter
        super().__init__(fetcher_id=fetcher_id, start=start, end=end)

    def _validate_attributes(self):
        super()._validate_attributes()  # noqa: SLF001
        if len(self.fetcher_id) > 0 and self.fetcher_id[0] == "_":
            raise exceptions.InvalidSmartContractError(
                "ParametersIntervalFetcher 'fetcher_id' cannot start with an underscore"
            )

        types_utils.validate_type(
            self.filter,
            ParametersFilter,
            hint="ParametersFilter",
            is_optional=True,
            prefix="ParametersIntervalFetcher.filter",
        )

    @classmethod
    @lru_cache()
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        public_attributes = super()._public_attributes(language_code)
        # public_attributes[0] corresponds to the fetcher_id ValueSpec
        public_attributes[0].docstring += " The fetcher ID must not start with an underscore."
        public_attributes.append(
            types_utils.ValueSpec(
                name="filter",
                type="Optional[ParametersFilter]",
                docstring="An optional filter to refine the results returned by the fetcher.",
            ),
        )
        return public_attributes

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name="ParametersIntervalFetcher",
            docstring="""
                Can only be used for `ExpectedParameters`. A fetcher for retrieving
                parameter values over an interval, inclusive of end time. In the
                `activation_hook`, if any expected parameter values are provided in the account
                creation request, these values will also be included in the parameter timeseries
                of the fetcher with `at_datetime` equal to the hook `effective_datetime`.
            """,
            public_attributes=cls._public_attributes(language_code),
            constructor=types_utils.ConstructorSpec(
                docstring="",
                args=cls._public_attributes(language_code),
            ),
        )


class ParametersObservationFetcher(types_utils.ContractsLanguageDunderMixin):
    def __init__(
        self,
        fetcher_id: str,
        at: Union[DefinedDateTime, RelativeDateTime],
        filter: Optional[ParametersFilter] = None,
    ):
        self.fetcher_id = fetcher_id
        self.at = at
        self.filter = filter
        self._validate_attributes()

    def _validate_attributes(self):
        types_utils.validate_type(
            self.fetcher_id,
            str,
            check_empty=True,
            hint="str",
            prefix="ParametersObservationFetcher.fetcher_id",
        )
        if len(self.fetcher_id) > 0 and self.fetcher_id[0] == "_":
            raise exceptions.InvalidSmartContractError(
                "ParametersObservationFetcher 'fetcher_id' cannot start with an underscore"
            )

        types_utils.validate_type(
            self.at,
            (DefinedDateTime, RelativeDateTime),
            hint="Union[DefinedDateTime, RelativeDateTime]",
            prefix="ParametersObservationFetcher.at",
        )

        if self.at == DefinedDateTime.INTERVAL_START:
            raise exceptions.InvalidSmartContractError(
                "ParametersObservationFetcher 'at' cannot be set to 'DefinedDateTime.INTERVAL_START'"
            )
        if type(self.at) is RelativeDateTime and self.at.origin == DefinedDateTime.INTERVAL_START:
            raise exceptions.InvalidSmartContractError(
                "ParametersObservationFetcher 'at.origin' cannot be set to 'DefinedDateTime.INTERVAL_START'"
            )

        types_utils.validate_type(
            self.filter,
            ParametersFilter,
            hint="ParametersFilter",
            is_optional=True,
            prefix="ParametersObservationFetcher.filter",
        )

    @classmethod
    @lru_cache()
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return [
            types_utils.ValueSpec(
                name="fetcher_id",
                type="str",
                docstring="""
                    The ID for this fetcher. The fetcher ID must not start with an underscore.
                """,
            ),
            types_utils.ValueSpec(
                name="at",
                type="Union[DefinedDateTime, RelativeDateTime]",
                docstring=f"""
                    {AT_ATTRIBUTE_COMMON_TEMPLATE("parameters")} If the value is
                    of type `DefinedDateTime`, `DefinedDateTime.INTERVAL_START`
                    is **not** allowed. If the value is of type `RelativeDateTime`,
                    `DefinedDateTime.INTERVAL_START` is **not** allowed as the `origin`.
                """,
            ),
            types_utils.ValueSpec(
                name="filter",
                type="Optional[ParametersFilter]",
                docstring="An optional filter to refine the results returned by the fetcher.",
            ),
        ]

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name="ParametersObservationFetcher",
            docstring="""
                Can only be used for `ExpectedParameters`. A fetcher for observing parameter values
                at a given moment in time. In the
                `activation_hook`, if any expected parameter values are provided in the account
                creation request and if the observation time is equal to or after the hook's
                effective time, these values will override any other values in the observation.
            """,
            public_attributes=cls._public_attributes(language_code),
            constructor=types_utils.ConstructorSpec(
                docstring="Constructs a new ParametersObservationFetcher object.",
                args=cls._public_attributes(language_code),
            ),
        )


class FlagsIntervalFetcher(NonDegenerateIntervalFetcher):
    def __init__(
        self,
        *,
        fetcher_id: str,
        start: Union[RelativeDateTime, DefinedDateTime],
        end: Optional[Union[RelativeDateTime, DefinedDateTime]] = DefinedDateTime.LIVE,
        filter: Optional[FlagsFilter] = None,
    ):
        self.class_name = self.__class__.__name__
        self.filter = filter
        super().__init__(fetcher_id=fetcher_id, start=start, end=end)
        self._validate_attributes()

    def _validate_attributes(self):
        super()._validate_attributes()
        types_utils.validate_type(
            self.filter,
            FlagsFilter,
            is_optional=True,
            hint="FlagsFilter",
            prefix="FlagsIntervalFetcher.filter",
        )

        types_utils.validate_type(
            self.end,
            (DefinedDateTime, RelativeDateTime),
            hint="Optional[Union[RelativeDateTime, DefinedDateTime]]",
            prefix="FlagsIntervalFetcher.end",
            is_optional=True,
        )

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name="FlagsIntervalFetcher",
            docstring="A fetcher for retrieving flags over an interval, inclusive of end time.",
            public_attributes=cls._public_attributes(language_code),
            constructor=types_utils.ConstructorSpec(
                docstring="Constructs a new FlagsIntervalFetcher object.",
                args=cls._public_attributes(language_code),
            ),
        )

    @classmethod
    @lru_cache()
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        public_attributes = super()._public_attributes(language_code)
        public_attributes.append(
            types_utils.ValueSpec(
                name="filter",
                type="Optional[FlagsFilter]",
                docstring="An optional filter to refine the results returned by the fetcher.",
            ),
        )
        return public_attributes


class FlagsObservationFetcher(types_utils.ContractsLanguageDunderMixin):
    def __init__(
        self,
        fetcher_id: str,
        at: Union[DefinedDateTime, RelativeDateTime],
        filter: Optional[FlagsFilter] = None,
    ):
        self.fetcher_id = fetcher_id
        self.at = at
        self.filter = filter
        self._validate_attributes()

    def _validate_attributes(self):
        types_utils.validate_type(
            self.fetcher_id,
            str,
            check_empty=True,
            hint="str",
            prefix="FlagsObservationFetcher.fetcher_id",
        )

        types_utils.validate_type(
            self.at,
            (DefinedDateTime, RelativeDateTime),
            hint="Union[DefinedDateTime, RelativeDateTime]",
            prefix="FlagsObservationFetcher.at",
        )

        if self.at is DefinedDateTime.INTERVAL_START:
            raise exceptions.InvalidSmartContractError(
                "FlagsObservationFetcher 'at' cannot be set to 'DefinedDateTime.INTERVAL_START'"
            )

        if type(self.at) is RelativeDateTime and self.at.origin == DefinedDateTime.INTERVAL_START:
            raise exceptions.InvalidSmartContractError(
                "FlagsObservationFetcher 'at.origin' cannot be set to 'DefinedDateTime.INTERVAL_START'"
            )

        types_utils.validate_type(
            self.filter,
            FlagsFilter,
            hint="FlagsFilter",
            is_optional=True,
            prefix="FlagsObservationFetcher.filter",
        )

    @classmethod
    @lru_cache()
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return [
            types_utils.ValueSpec(
                name="fetcher_id", type="str", docstring="The ID for this fetcher."
            ),
            types_utils.ValueSpec(
                name="at",
                type="Union[DefinedDateTime, RelativeDateTime]",
                docstring=f""" 
                    {AT_ATTRIBUTE_COMMON_TEMPLATE("flags")}  If the value is
                    of type `DefinedDateTime`, `DefinedDateTime.INTERVAL_START`
                    is **not** allowed. If the value is of type `RelativeDateTime`,
                    `DefinedDateTime.INTERVAL_START` is **not** allowed as the `origin`.
                """,
            ),
            types_utils.ValueSpec(
                name="filter",
                type="Optional[FlagsFilter]",
                docstring="An optional filter to refine the results returned by the fetcher.",
            ),
        ]

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name="FlagsObservationFetcher",
            docstring="A fetcher for observing flags at a given moment in time.",
            public_attributes=cls._public_attributes(language_code),
            constructor=types_utils.ConstructorSpec(
                docstring="Constructs a new FlagsObservationFetcher object.",
                args=cls._public_attributes(language_code),
            ),
        )





class CalendarsIntervalFetcher(NonDegenerateIntervalFetcher):
    def __init__(
        self,
        *,
        fetcher_id: str,
        filter: CalendarsFilter,
        start: Union[RelativeDateTime, DefinedDateTime],
        end: Optional[Union[RelativeDateTime, DefinedDateTime]] = DefinedDateTime.LIVE,
    ) -> None:
        self.filter = filter
        self._validate_filter()
        super().__init__(fetcher_id=fetcher_id, start=start, end=end)

    def _validate_filter(self):
        types_utils.validate_type(
            self.filter,
            CalendarsFilter,
            hint=f"{CalendarsFilter.__name__}",
            prefix=f"{self.__class__.__name__}.filter",
        )

    @classmethod
    @lru_cache()
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        # Order the attributes in the same order as the signature
        super__public_attributes = super()._public_attributes(language_code)
        return [
            super__public_attributes[0],  # fetcher_id
            types_utils.ValueSpec(
                name="filter",
                type=f"{CalendarsFilter.__name__}",
                docstring="A filter to refine the results returned by the fetcher.",
            ),
            super__public_attributes[1],  # start
            super__public_attributes[2],  # end
        ]

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name=f"{cls.__name__}",
            docstring=(
                "A fetcher for retrieving calendar events over an interval, inclusive of end time."
                "The `filter` attribute must be populated with a `CalendarsFilter` containing the "
                "calendar IDs to fetch for. "
            ),
            public_attributes=cls._public_attributes(language_code),
            constructor=types_utils.ConstructorSpec(
                docstring=f"Constructs a new {cls.__name__} object.",
                args=cls._public_attributes(language_code),
            ),
        )


class CalendarsObservationFetcher(types_utils.ContractsLanguageDunderMixin):
    def __init__(
        self,
        *,
        fetcher_id: str,
        filter: CalendarsFilter,
        at: Union[DefinedDateTime, RelativeDateTime],
    ) -> None:
        self.fetcher_id = fetcher_id
        self.at = at
        self.filter = filter
        self._validate_attributes()

    def _validate_attributes(self):
        types_utils.validate_type(
            self.fetcher_id,
            str,
            check_empty=True,
            hint="str",
            prefix=f"{self.__class__.__name__}.fetcher_id",
        )
        types_utils.validate_type(
            self.at,
            (DefinedDateTime, RelativeDateTime),
            check_empty=True,
            hint=f"Union[{DefinedDateTime.__name__}, {RelativeDateTime.__name__}]",
            prefix=f"{self.__class__.__name__}.at",
        )

        if self.at is DefinedDateTime.INTERVAL_START:
            raise exceptions.InvalidSmartContractError(
                f"{self.__class__.__name__} 'at' cannot be set to 'DefinedDateTime.INTERVAL_START'"
            )

        if type(self.at) is RelativeDateTime and self.at.origin == DefinedDateTime.INTERVAL_START:
            raise exceptions.InvalidSmartContractError(
                f"{self.__class__.__name__} 'at.origin' cannot be set to 'DefinedDateTime.INTERVAL_START'"
            )

        types_utils.validate_type(
            self.filter,
            CalendarsFilter,
            hint=f"{CalendarsFilter.__name__}",
            prefix=f"{self.__class__.__name__}.filter",
        )

    @classmethod
    @lru_cache()
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return [
            types_utils.ValueSpec(
                name="fetcher_id",
                type="str",
                docstring="The ID for this fetcher.",
            ),
            types_utils.ValueSpec(
                name="filter",
                type=f"{CalendarsFilter.__name__}",
                docstring="A filter to refine the results returned by the fetcher.",
            ),
            types_utils.ValueSpec(
                name="at",
                type=f"Union[{DefinedDateTime.__name__}, {RelativeDateTime.__name__}]",
                docstring=f"""
                    {AT_ATTRIBUTE_COMMON_TEMPLATE("calendars")}  If the value is
                    of type `DefinedDateTime`, `DefinedDateTime.INTERVAL_START`
                    is **not** allowed. If the value is of type `RelativeDateTime`,
                    `DefinedDateTime.INTERVAL_START` is **not** allowed as the `origin`.
                """,
            ),
        ]

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name=f"{CalendarsObservationFetcher.__name__}",
            docstring=(
                "A fetcher for observing calendars at a given moment in time. "
                "The `filter` attribute must be populated with a `CalendarsFilter` containing the "
                "calendar IDs to fetch for. "
            ),
            public_attributes=cls._public_attributes(language_code),
            constructor=types_utils.ConstructorSpec(
                docstring=f"Constructs a new {CalendarsObservationFetcher.__name__} object.",
                args=cls._public_attributes(language_code),
            ),
        )


class LastScheduledEventDateTimesObservationFetcher(types_utils.ContractsLanguageDunderMixin):
    def __init__(
        self,
        *,
        fetcher_id: str,
        filter: EventTypesFilter,
        at: DefinedDateTime,
    ) -> None:
        self.fetcher_id = fetcher_id
        self.at = at
        self.filter = filter
        self._validate_attributes()

    def _validate_attributes(self):
        types_utils.validate_type(
            self.fetcher_id,
            str,
            check_empty=True,
            hint="str",
            prefix=f"{self.__class__.__name__}.fetcher_id",
        )
        types_utils.validate_type(
            self.at,
            DefinedDateTime,
            check_empty=True,
            hint=f"{DefinedDateTime.__name__}",
            prefix=f"{self.__class__.__name__}.at",
        )

        if self.at is DefinedDateTime.INTERVAL_START:
            raise exceptions.InvalidSmartContractError(
                f"{self.__class__.__name__} 'at' cannot be set to 'DefinedDateTime.INTERVAL_START'"
            )

        types_utils.validate_type(
            self.filter,
            EventTypesFilter,
            hint=f"{EventTypesFilter.__name__}",
            prefix=f"{self.__class__.__name__}.filter",
        )

    @classmethod
    @lru_cache()
    def _public_attributes(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return [
            types_utils.ValueSpec(
                name="fetcher_id", type="str", docstring="The ID for this fetcher."
            ),
            types_utils.ValueSpec(
                name="at",
                type=f"{DefinedDateTime.__name__}",
                docstring=f"""
                    {AT_ATTRIBUTE_COMMON_TEMPLATE("last scheduled event date time")}
                    `DefinedDateTime.INTERVAL_START` is **not** allowed.
                """,
            ),
            types_utils.ValueSpec(
                name="filter",
                type=f"{EventTypesFilter.__name__}",
                docstring="A filter to refine the results returned by the fetcher.",
            ),
        ]

    @classmethod
    @lru_cache()
    def _spec(cls, language_code=symbols.Languages.ENGLISH):
        if language_code != symbols.Languages.ENGLISH:
            raise ValueError("Language not supported")

        return types_utils.ClassSpec(
            name=f"{LastScheduledEventDateTimesObservationFetcher.__name__}",
            docstring=f"""
                A fetcher for observing last scheduled event date times at a given moment in time.

                [IMPORTANT]
                ====
                Existing Customer Accounts cannot be converted to a Smart Contract with
                [LastScheduledEventDateTimesObservationFetcher]({_common_docs_path}classes/#LastScheduledEventDateTimesObservationFetcher)
                if their current Smart Contract is not already using it, due to data access limitations.
                Future Vault Core improvements aim to address these limitations.
                ====
            """,
            public_attributes=cls._public_attributes(language_code),
            constructor=types_utils.ConstructorSpec(
                docstring=f"Constructs a new {LastScheduledEventDateTimesObservationFetcher.__name__} object.",
                args=cls._public_attributes(language_code),
            ),
        )
