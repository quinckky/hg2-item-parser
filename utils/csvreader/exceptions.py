class BaseCSVException(Exception):
    ...


class RowNotFoundError(BaseCSVException):
    def __init__(self, column_name, column_value):
        super().__init__(f'Row with value \'{
            column_value}\' not found in column \'{column_name}\'')


class ColumnNotFoundError(BaseCSVException):
    def __init__(self, column_name):
        super().__init__(f'Column \'{column_name}\' not found')
