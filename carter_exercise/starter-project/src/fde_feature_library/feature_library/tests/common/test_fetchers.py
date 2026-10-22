import unittest

import pytest

from feature_library.common.fetchers import distinct_fetchers

from contracts_api import BalancesObservationFetcher, DefinedDateTime


class TestDistinctFetchers(unittest.TestCase):
    @pytest.mark.unit
    def test_distinct_fetchers_empty_list(self):
        self.assertEqual(distinct_fetchers([]), [])

    @pytest.mark.unit
    def test_distinct_fetchers_no_duplicates(self):
        fetcher1_bof = BalancesObservationFetcher(
            fetcher_id="f1_bof", at=DefinedDateTime.EFFECTIVE_DATETIME
        )
        fetcher2_bof = BalancesObservationFetcher(
            fetcher_id="f2_bof", at=DefinedDateTime.EFFECTIVE_DATETIME
        )

        result = distinct_fetchers([fetcher1_bof, fetcher2_bof])
        self.assertEqual(result, [fetcher1_bof, fetcher2_bof])

    @pytest.mark.unit
    def test_distinct_fetchers_with_duplicates(self):
        fetcher1_bof = BalancesObservationFetcher(
            fetcher_id="f1_bof", at=DefinedDateTime.EFFECTIVE_DATETIME
        )
        fetcher2_bof = BalancesObservationFetcher(
            fetcher_id="f2_bof", at=DefinedDateTime.EFFECTIVE_DATETIME
        )
        # Duplicate by ID but different attribute
        fetcher1_dup_bof = BalancesObservationFetcher(fetcher_id="f1_bof", at=DefinedDateTime.LIVE)

        # Pass a list with multiple duplicates
        input_list = [fetcher1_bof, fetcher2_bof, fetcher1_dup_bof, fetcher2_bof, fetcher1_bof]
        result = distinct_fetchers(input_list)

        # Should keep only the first occurrences of each fetcher_id
        self.assertEqual(len(result), 2)
        self.assertIs(result[0], fetcher1_bof)
        self.assertIs(result[1], fetcher2_bof)
