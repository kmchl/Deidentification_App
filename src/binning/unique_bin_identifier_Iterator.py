# unique_bin_identifier_Iterator.py

import pandas as pd
from itertools import combinations
from typing import Tuple, List, Dict, Optional
import warnings

class UniqueBinIdentifierIterator:
    """
    A class to identify small groups in the binned DataFrame based on combinations
    of bin columns, in order to assess k-anonymity.
    """

    def __init__(self, original_df: pd.DataFrame, binned_df: pd.DataFrame):
        """
        Initializes the UniqueBinIdentifier with original and binned DataFrames.

        Parameters:
            original_df (pd.DataFrame): The original DataFrame with full data.
            binned_df (pd.DataFrame): The binned DataFrame with reduced bin counts.
        """
        self.original_df = original_df.reset_index(drop=True)
        self.binned_df = binned_df.reset_index(drop=True)
        self.results = pd.DataFrame()

        self._validate_dataframes()

    def _validate_dataframes(self):
        """
        Validates that the original and binned DataFrames have the same number of rows.
        """
        if len(self.original_df) != len(self.binned_df):
            raise ValueError("Original and binned DataFrames must have the same number of rows.")

    def find_small_groups(
        self,
        k: int,
        min_comb_size: int = 1,
        max_comb_size: Optional[int] = None,
        columns: Optional[List[str]] = None,
        progress_callback: Optional[callable] = None
    ) -> pd.DataFrame:
        if columns is None:
            columns = list(self.binned_df.columns)
        else:
            # Validate that provided columns exist in the binned DataFrame
            missing_cols = set(columns) - set(self.binned_df.columns)
            if missing_cols:
                raise ValueError(f"The following columns are not in the binned DataFrame: {missing_cols}")

        if max_comb_size is None:
            max_comb_size = len(columns)
        else:
            max_comb_size = min(max_comb_size, len(columns))

        if min_comb_size < 1:
            raise ValueError("min_comb_size must be at least 1.")

        if max_comb_size < min_comb_size:
            raise ValueError("max_comb_size must be greater than or equal to min_comb_size.")

        results = []

        total_combinations = sum(
            [self._nCr(len(columns), r) for r in range(min_comb_size, max_comb_size + 1)]
        )

        print(f"Total combinations to analyze: {total_combinations}")

        combination_counter = 0

        for comb_size in range(min_comb_size, max_comb_size + 1):
            for comb in combinations(columns, comb_size):
                combination_counter += 1
                if progress_callback and combination_counter % 1000 == 0:
                    progress_callback(combination_counter, total_combinations)
                # Create a temporary DataFrame with the combination of bins
                temp_df = self.binned_df[list(comb)]

                # Group by the combination and count the number of occurrences
                group_counts = temp_df.groupby(list(comb)).size()

                # Number of small groups is the number of groups with size < k
                small_groups = (group_counts < k).sum()

                # Append the result
                results.append({
                    'Combination': comb,
                    'Small_Groups': small_groups
                })

        # Create a DataFrame from the results
        self.results = pd.DataFrame(results)

        # Sort the results by 'Small_Groups' ascending
        self.results.sort_values(by='Small_Groups', ascending=True, inplace=True)
        self.results.reset_index(drop=True, inplace=True)

        print("k-anonymity analysis complete.")

        return self.results

    @staticmethod
    def _nCr(n: int, r: int) -> int:
        """
        Computes the number of combinations (n choose r).

        Parameters:
            n (int): Total number of items.
            r (int): Number of items to choose.

        Returns:
            int: Number of combinations.
        """
        from math import comb
        return comb(n, r)

    def get_results(self) -> pd.DataFrame:
        """
        Retrieves the results of the k-anonymity analysis.

        Returns:
            pd.DataFrame: DataFrame with columns 'Combination' and 'Small_Groups'.
        """
        if self.results.empty:
            raise ValueError("No results found. Please run 'find_small_groups' first.")
        return self.results.copy()

    def save_results(self, filepath: str):
        """
        Saves the k-anonymity results to a CSV file.

        Parameters:
            filepath (str): The path where the results will be saved.
        """
        if self.results.empty:
            raise ValueError("No results to save. Please run 'find_small_groups' first.")
        self.results.to_csv(filepath, index=False)
        print(f"📄 k-anonymity results saved to {filepath}")
