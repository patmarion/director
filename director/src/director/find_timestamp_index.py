import numpy as np


def find_timestamp_index(timestamps, query_timestamp, clamp: bool = True) -> int:
    """
    Return the index of the latest timestamp less than or equal to `query_timestamp`.
    Assumes the provided timestamps are in sorted order, otherwise the result will be incorrect.
    If `query_timestamp` is less than all values and clamp is True, return 0.
    If out of range and clamp is False, raise ValueError.
    Raises ValueError if `timestamps` is empty.
    """
    if len(timestamps) == 0:
        raise ValueError("Timestamps array is empty.")

    idx = np.searchsorted(timestamps, query_timestamp, side='right') - 1

    if idx < 0:
        if clamp:
            return 0
        else:
            raise ValueError(f"timestamp {query_timestamp} is before earliest time {timestamps[0]}")
    return idx