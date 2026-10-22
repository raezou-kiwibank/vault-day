# standard libs
from datetime import datetime
from typing import Generic, TypeVar

T = TypeVar("T")


class TimeSeries(list, Generic[T]):
    def __init__(self, items: list[tuple[datetime, T]], return_on_empty: T | None = None):
        super().__init__(items)
        self.return_on_empty = return_on_empty

    def at(self, timestamp, inclusive=True) -> T:
        for entry in reversed(self):
            if entry[0] <= timestamp:
                if inclusive or entry[0] < timestamp:
                    return entry[1]

        if self.return_on_empty is not None:
            return self.return_on_empty

        raise ValueError("No value in timeseries")

    def before(self, timestamp) -> T:
        return self.at(timestamp, inclusive=False)

    def latest(self) -> T:
        if not self:
            if self.return_on_empty is not None:
                return self.return_on_empty
            raise ValueError("No value in timeseries")
        return self[-1][1]

    def all(self) -> list[tuple[datetime, T]]:
        return [item for item in self]
