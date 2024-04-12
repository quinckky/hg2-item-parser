import os
import re
from typing import Literal

import requests

from .constants import *
from .utils.csvreader import CSVReader
from .utils.csvreader.exceptions import *

Server = Literal['JP', 'CN']
ItemCategory = Literal['weapon', 'costume', 'badge', 'pet']
SkillCategory = Literal['pet', 'not_pet']
ItemAttrs = Literal['ID', 'Title ID', 'Title', 'Icon ID', 'Icon URL', 'Damage Type', 'Rarity']
ItemSkillAttrs = Literal['ID', 'Damage Type', 'Title ID', 'Title', 'Description Template ID', 'Description Template', 'Description']

_current_folder = os.path.dirname(__file__)

class HG2ItemParser:

    _textmap_old = CSVReader(f'{_current_folder}/data/{TEXTMAP_OLD_FILENAME}', delimiter='\t')
    _textmap_new: dict = requests.get(TEXTMAP_NEW_URL).json()

    _cached_items_data = {
        'JP': dict(),
        'CN': dict()
    }

    _cached_items_skills_data = {
        'JP': dict(),
        'CN': dict()
    }

    @classmethod
    def parse_item_all(cls, item_id: int) -> tuple[dict, dict, list[dict]] | tuple[None]:
        item_main_info = cls.parse_item_main_info(item_id)
        item_properties = cls.parse_item_properties(item_id)
        item_skills = cls.parse_item_skills(item_id)

        return item_main_info, item_properties, item_skills

    @classmethod
    def parse_item_main_info(cls, item_id: int) -> dict[ItemAttrs, str | int] | None:
        item_main_info = dict()
        item_data = cls._search_item_data(item_id)
        if item_data is None:
            return None

        item_main_info['ID'] = item_id

        item_title_id = item_main_info['Title ID'] = int(
            item_data['DisplayTitle'])
        item_main_info['Title'] = cls._parse_text(item_title_id)

        item_icon_id = item_main_info['Icon ID'] = int(
            item_data['DisplayImage'])
        trailing_zero = '0' * (3 - len(str(item_icon_id)))
        item_main_info['Icon URL'] = f'{IMAGES_URL}{
            trailing_zero}{item_icon_id}.png'

        item_damage_type = item_data.get('DamageType', 'none')
        item_main_info['Damage Type'] = DAMAGE_TYPE_NAMES[item_damage_type]

        item_main_info['Rarity'] = int(item_data['Rarity'])

        return item_main_info

    @classmethod
    def parse_item_properties(cls, item_id: int) -> dict[str, str | int | float] | None:
        item_properties = dict()
        item_data = cls._search_item_data(item_id)
        if item_data is None:
            return None
        
        match item_data['Category']:
            case 'weapon':
                item_properties = cls._parse_weapon_properties(item_data)
            case 'costume':
                item_properties = cls._parse_costume_properties(item_data)
            case 'badge':
                item_properties = cls._parse_badge_properties(item_data)
            case 'pet':
                item_properties = cls._parse_pet_properties(item_data)

        item_properties = {key: value for key,
                           value in item_properties.items() if value}

        return item_properties

    @classmethod
    def parse_item_skills(cls, item_id: int) -> list[dict[ItemSkillAttrs, str | int]] | None:
        item_skills = []
        item_data = cls._search_item_data(item_id)
        if item_data is None:
            return None
        
        item_skills_data = cls._parse_item_skills_data(item_data)
        item_skills_description = cls._parse_item_skills_description(item_data)

        for item_skill_data, item_skill_description in zip(item_skills_data, item_skills_description):
            item_skill = dict()
            item_skill['ID'] = int(item_skill_data['ID'])
            item_skill_damage_type = item_skill_data.get('Feature', 'none')
            item_skill['Damage Type'] = DAMAGE_TYPE_NAMES[item_skill_damage_type]
            item_skill_title_id = item_skill['Title ID'] = int(
                item_skill_data['DisplayTitle'].replace('TEXT', ''))
            item_skill['Title'] = cls._parse_text(item_skill_title_id)
            item_skill_description_template_id = item_skill['Description Template ID'] = int(
                item_skill_data['DisplayDescription'].replace('TEXT', ''))
            item_skill['Description Template'] = cls._parse_text(
                item_skill_description_template_id)
            item_skill['Description'] = item_skill_description
            item_skills.append(item_skill)

        return item_skills

    @staticmethod
    def _parse_weapon_properties(item_data: dict) -> dict:
        weapon_properties = dict()
        weapon_max_lvl = weapon_properties['Max Lvl'] = int(item_data['MaxLv'])
        weapon_properties['Carry Load'] = int(item_data['Cost'])
        weapon_properties['Max Lvl HP'] = round(
            float(item_data['HPBase']) + float(item_data['HPAdd']) * (weapon_max_lvl - 1))
        weapon_properties['Type'] = WEAPON_TYPE_NAMES[item_data['BaseType']]
        weapon_properties['Max Lvl Damage'] = round(float(
            item_data['DamageBase']) + float(item_data['DamageAdd']) * (weapon_max_lvl - 1))
        weapon_properties['Max Lvl Ammo'] = round(float(
            item_data['AmmoBase']) + float(item_data['AmmoAdd']) * (weapon_max_lvl - 1))
        if weapon_properties['Max Lvl Ammo'] == -1:
            weapon_properties['Max Lvl Ammo'] = '∞'
        weapon_properties['Max Lvl ASPD'] = round(float(
            item_data['FireRateBase']) + float(item_data['FireRateAdd']) * (weapon_max_lvl - 1), 3)
        weapon_properties['Deploy Limit'] = int(item_data['LimitedNumber'])
        weapon_properties['Duration'] = round(float(
            item_data['CountDownTime']) + float(item_data['CountDownTimeAdd']) * (weapon_max_lvl - 1), 2)
        weapon_properties['Crit Rate'] = int(
            float(item_data['CriticalRate']) * 100)

        return weapon_properties

    @staticmethod
    def _parse_costume_properties(item_data: dict) -> dict:
        costume_properties = dict()
        costume_max_lvl = costume_properties['Max Lvl'] = int(
            item_data['MaxLv'])
        costume_properties['Carry Load'] = int(item_data['Cost'])
        costume_properties['Max Lvl HP'] = round(
            float(item_data['HPBase']) + float(item_data['HPAdd']) * (costume_max_lvl - 1))

        return costume_properties

    @staticmethod
    def _parse_badge_properties(item_data: dict) -> dict:
        badge_properties = dict()
        badge_properties['Max Lvl'] = int(item_data['MaxLv'])
        badge_properties['Carry Load'] = int(item_data['Cost'])

        return badge_properties

    @staticmethod
    def _parse_pet_properties(item_data: dict) -> dict:
        pet_properties = dict()
        pet_max_lvl = pet_properties['Max Lvl'] = int(item_data['MaxLv'])
        pet_properties['Max Lvl Damage'] = round(
            float(item_data['Attack']) + float(item_data['Attack_Add']) * (pet_max_lvl - 1))
        pet_properties['Crit Rate'] = int(
            float(item_data['initCritRate']) * 100)
        pet_properties['Base Sync'] = int(item_data['SynInit'])
        pet_properties['Max Sync'] = int(
            item_data['SynInit']) + int(item_data['SynAdd']) * int(item_data['SynMaxLevel'])

        return pet_properties

    @classmethod
    def _parse_item_skills_max_break_values(cls, item_data: dict) -> list[list[float]]:
        if item_data['Category'] == 'pet':
            item_skills_max_break_values = cls._parse_pet_skills_max_break_values(
                item_data)
        else:
            item_skills_max_break_values = cls._parse_not_pet_skills_max_break_values(
                item_data)

        return item_skills_max_break_values

    @classmethod
    def _parse_pet_skills_max_break_values(cls, item_data: dict) -> list[list[float]]:
        pet_skills_max_break_values = []
        pet_skills_data = cls._parse_pet_skills_data(item_data)
        pet_skills_max_lvl_values = cls._parse_pet_skills_max_lvl_values(
            item_data)

        for i, pet_skill_data in enumerate(pet_skills_data):
            pet_skill_max_break_values = []
            for j in range(1, 7):
                pet_skill_max_lvl_value = pet_skills_max_lvl_values[i][j-1]
                pet_skill_max_lvl = int(pet_skill_data[f'Maxlevel'])
                pet_skill_add = float(pet_skill_data[f'Para{j}SkillUpAdd'])
                pet_skill_max_break_values.append(
                    pet_skill_max_lvl_value + pet_skill_add * pet_skill_max_lvl)
            pet_skills_max_break_values.append(pet_skill_max_break_values)

        return pet_skills_max_break_values

    @classmethod
    def _parse_not_pet_skills_max_break_values(cls, item_data: dict) -> list[list[float]]:
        item_skills_max_break_values = []
        item_skills_data = cls._parse_not_pet_skills_data(item_data)
        item_skills_max_lvl_values = cls._parse_not_pet_skills_max_lvl_values(
            item_data)

        for i, item_skill_data in enumerate(item_skills_data):
            item_skill_slots_amount = int(item_skill_data['SlotCount'])
            item_skill_slots_equip: list[str] = [item_skill_data[f'Slot{j}Equips'] 
                                                 for j in range(1, item_skill_slots_amount + 1)]

            for skill_slot_used, skill_slot_equip in enumerate(item_skill_slots_equip, start=1):
                if str(item_data['DisplayNumber']) in skill_slot_equip.split(';'):
                    break
            else:
                skill_slot_used = 1

            item_skill_max_break_values = []
            for j in range(1, 6):
                item_skill_max_lvl_value = item_skills_max_lvl_values[i][j-1]
                item_skill_slot_add = float(
                    item_skill_data[f'Slot{skill_slot_used}Para{j}Add'])
                item_skill_slot_max_lvl = float(
                    item_skill_data[f'Slot{skill_slot_used}MaxLevel'])
                item_skill_max_break_values.append(
                    item_skill_max_lvl_value + item_skill_slot_add * item_skill_slot_max_lvl)

            item_skills_max_break_values.append(item_skill_max_break_values)

        return item_skills_max_break_values

    @classmethod
    def _parse_item_skills_max_lvl_values(cls, item_data: dict) -> list[list[float]]:
        if item_data['Category'] == 'pet':
            item_skills_max_lvl_values = cls._parse_pet_skills_max_lvl_values(
                item_data)
        else:
            item_skills_max_lvl_values = cls._parse_not_pet_skills_max_lvl_values(
                item_data)

        return item_skills_max_lvl_values

    @classmethod
    def _parse_pet_skills_max_lvl_values(cls, item_data: dict) -> list[list[float]]:
        pet_skills_max_lvl_values = []
        pet_skills_data = cls._parse_pet_skills_data(item_data)

        for pet_skill_data in pet_skills_data:
            pet_skill_max_lvl_values = []
            for j in range(1, 7):
                pet_skill_max_lvl_value = float(pet_skill_data[f'Para{j}'])
                pet_skill_max_lvl_values.append(pet_skill_max_lvl_value)
            pet_skills_max_lvl_values.append(pet_skill_max_lvl_values)

        return pet_skills_max_lvl_values

    @staticmethod
    def _parse_not_pet_skills_max_lvl_values(item_data: dict) -> list[list[float]]:
        item_skills_max_lvl_values = []
        item_skills_amount = int(item_data['NumProps'])
        item_max_lvl = int(item_data['MaxLv'])

        item_skills_range = list(range(1, item_skills_amount + 1))
        if int(item_data['DisplayNumber']) in FANTASY_LEGEND_IDS:
            item_skills_range += [6, 7]

        for i in item_skills_range:
            item_skill_max_lvl_values = []
            for j in range(1, 6):
                item_skill_value = float(item_data[f'Prop{i}Param{j}'])
                item_skill_value_add = float(item_data[f'Prop{i}Param{j}Add'])
                item_skill_max_lvl_value = item_skill_value + \
                    item_skill_value_add * (item_max_lvl - 1)
                item_skill_max_lvl_values.append(item_skill_max_lvl_value)
            item_skills_max_lvl_values.append(item_skill_max_lvl_values)

        return item_skills_max_lvl_values

    @classmethod
    def _parse_item_skills_description(cls, item_data: dict) -> list[str]:
        item_skills_description = []
        item_skills_data = cls._parse_item_skills_data(item_data)
        item_skills_max_lvl_values = cls._parse_item_skills_max_lvl_values(
            item_data)
        item_skills_max_break_values = cls._parse_item_skills_max_break_values(
            item_data)

        for i, item_skill_data in enumerate(item_skills_data):
            item_skill_description_template_id = int(
                item_skill_data['DisplayDescription'].replace('TEXT', ''))
            item_skill_description_template = cls._parse_text(
                item_skill_description_template_id)
            item_skill_description = cls._fill_item_skill_description_template(
                item_skill_description_template, item_skills_max_lvl_values[i], item_skills_max_break_values[i])
            item_skills_description.append(item_skill_description)

        return item_skills_description

    @staticmethod
    def _fill_item_skill_description_template(item_skill_description_template: str, item_skill_max_lvl_values: list[float], item_skill_max_break_values: list[float]) -> str:
        item_skill_description = re.sub(
            r'# ?!?ALB ?\(\d+\)', '', item_skill_description_template)
        item_skill_description = item_skill_description.replace('#n', '')
        item_skill_description = item_skill_description.replace(' %', '%')

        for i, item_skill_max_lvl_value, item_skill_max_break_value in zip(range(1, 7), item_skill_max_lvl_values, item_skill_max_break_values):
            if f'#{i}%' in item_skill_description:
                item_skill_max_lvl_value *= 100
                item_skill_max_break_value *= 100

            match = re.search(fr'([1-9]+)#{i}', item_skill_description)
            if match is not None:
                mul = int(match.group(1))
                item_skill_max_lvl_value *= mul
                item_skill_max_break_value *= mul
            else:
                mul = ''

            item_skill_fill_value = f'{item_skill_max_lvl_value:g}'
            if item_skill_max_lvl_value != item_skill_max_break_value:
                item_skill_fill_value += f'({item_skill_max_break_value:g})'

            item_skill_description = item_skill_description.replace(
                f'{mul}#{i}', item_skill_fill_value)

        item_skill_description = item_skill_description.strip()

        return item_skill_description

    @classmethod
    def _parse_item_skills_data(cls, item_data: dict) -> list[dict]:
        if item_data['Category'] == 'pet':
            item_skills_data = cls._parse_pet_skills_data(item_data)
        else:
            item_skills_data = cls._parse_not_pet_skills_data(item_data)

        return item_skills_data

    @classmethod
    def _parse_pet_skills_data(cls, item_data: dict) -> list[dict]:
        pet_skills_data = []
        pet_skills_id = cls._parse_pet_skills_id(item_data)

        for pet_skill_id in pet_skills_id:
            try:
                pets_skills_data = cls._cached_items_skills_data[item_data['Server']]['pet']
            except KeyError:
                cls._cache_items_skills_data(item_data['Server'], 'pet')
                pets_skills_data = cls._cached_items_skills_data[item_data['Server']]['pet']

            try:
                pet_skill = pets_skills_data.get_row('ID', pet_skill_id)
                pet_skills_data.append(pet_skill)

            except RowNotFoundError:
                pass

        return pet_skills_data

    @classmethod
    def _parse_not_pet_skills_data(cls, item_data: dict) -> list[dict]:
        item_skills_data = []
        item_skills_id = cls._parse_not_pet_skills_id(item_data)
        try:
            items_skills_data = cls._cached_items_skills_data[item_data['Server']]['not_pet']
        except KeyError:
            cls._cache_items_skills_data(item_data['Server'], 'not_pet')
            items_skills_data = cls._cached_items_skills_data[item_data['Server']]['not_pet']

        for item_skill_id in item_skills_id:
            try:
                item_skill_data = items_skills_data.get_row(
                    'ID', item_skill_id)
                if item_skill_data['DisplayTitle'] == '0':
                    continue
                item_skills_data.append(item_skill_data)

            except RowNotFoundError:
                pass

        return item_skills_data

    @staticmethod
    def _parse_pet_skills_id(item_data: dict) -> list[int]:
        pet_skills_id = []
        for pet_skill_name in ('UltraSkillid', 'HiddenUltraSkillid', 'normalSkill1Id', 'normalSkill2Id'):
            pet_skill_id = int(item_data[pet_skill_name])
            pet_skills_id.append(pet_skill_id)

        return pet_skills_id

    @staticmethod
    def _parse_not_pet_skills_id(item_data: dict) -> list[int]:
        item_skills_amount = int(item_data['NumProps'])
        item_skills_id = [int(item_data[f'Prop{i}id'])
                          for i in range(1, item_skills_amount + 1)]
        if int(item_data['DisplayNumber']) in FANTASY_LEGEND_IDS:
            item_skills_id.append(int(item_data[f'Prop6id']))
            item_skills_id.append(int(item_data[f'Prop7id']))

        return item_skills_id

    @classmethod
    def _cache_items_skills_data(cls, server: Server, category: SkillCategory) -> None:
        filename = SKILL_FILENAMES[category]
        items_skills_data = CSVReader(
            f'{_current_folder}/data/{server}/{filename}', delimiter='\t')
        cls._cached_items_skills_data[server][category] = items_skills_data

    @classmethod
    def _search_item_data(cls, item_id: int) -> dict | None:
        for category in ('weapon', 'costume', 'badge', 'pet'):
            for server in ('JP', 'CN'):
                item_data = cls._parse_item_data(item_id, server, category)
                if item_data is not None:
                    return item_data
                

    @classmethod
    def _parse_item_data(cls, item_id: int, server: Server, category: ItemCategory) -> dict | None:
        try:
            items_data = cls._cached_items_data[server][category]
        except KeyError:
            cls._cache_items_data(server, category)
            items_data = cls._cached_items_data[server][category]

        try:
            item_data = items_data.get_row('DisplayNumber', item_id)
            item_data['Server'] = server
            item_data['Category'] = category
        except RowNotFoundError:
            return None

        return item_data

    @classmethod
    def _cache_items_data(cls, server: Server, category: ItemCategory) -> None:
        filename = ITEM_FILENAMES[category]
        items_data = CSVReader(f'{_current_folder}/data/{server}/{filename}', delimiter='\t')
        cls._cached_items_data[server][category] = items_data

    @classmethod
    def _parse_text(cls, text_id: int) -> str:
        try:
            text = cls._textmap_new[str(text_id)]
        except KeyError:
            try:
                text = cls._textmap_old.get_row('TEXT_ID', text_id)['EN']
            except RowNotFoundError:
                text = 'TEXT'

        return text
