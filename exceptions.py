class BaseParserException(Exception):
    ...


class ItemNotFoundError(BaseParserException):
    def __init__(self, item_id):
        self.item_id = item_id
        super().__init__(f'Item with ID \'{item_id}\' not found')


class ItemSkillNotFoundError(BaseParserException):
    def __init__(self, item_skill_id):
        self.item_skill_id = item_skill_id
        super().__init__(f'Item skill with ID \'{item_skill_id}\' not found')
