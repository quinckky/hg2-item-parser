import csv

from .exceptions import *


class CSVReader:
    def __init__(self, filename, delimiter=','):
        self._filename = filename
        self._delimiter = delimiter
        self._data = self._cache_data()

    def get_row(self, column_name: str, column_value: str | int | float) -> dict:
        for row in self._data:
            try:
                if str(row[column_name]) == str(column_value):
                    return row
            except KeyError:
                raise ColumnNotFoundError(column_name)

        raise RowNotFoundError(column_name, column_value)

    def _cache_data(self):
        data = []
        with open(self._filename, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter=self._delimiter)
            for row in reader:
                data.append(row)
        return data
