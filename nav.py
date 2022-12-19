from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

class Keyboards:
    def __init__(self, texts: dict):
        self.text = texts

    def start_1(self):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text=self.text['start_1'], callback_data='start_1'))
        return markup

    def start_2(self):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text=self.text['start_2'], callback_data='start_2'))
        return markup

    def start_3(self):
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.row(self.text['start_3'])
        return markup

    def start_4(self):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text=self.text['print_photo'], callback_data='start_1'))
        return markup

    def start_5(self):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text=self.text['back_to_print'], callback_data='start_1'))
        return markup

    def cancel_order(self):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text=self.text["cancel_order"], callback_data='cancel_order'))
        return markup

    def cancel_all(self):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text=self.text["cancel_all"], callback_data='cancel_all'))
        return markup

    def only_ru_cards(self):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text=self.text['only_ru_cards'], callback_data='russian_card'))
        return markup

    def main(self, kategory):
        markup = InlineKeyboardMarkup()
        for key, value in self.text[kategory].items():
            markup.add(InlineKeyboardButton(text=value, callback_data=key))
        return markup

    def cancel(self):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(text="Отмена", callback_data="cancel"))
        return markup

    def from_str(self, text: str):
        markup = InlineKeyboardMarkup()
        for line in text.split("\n"):
            sign, url = line.split(" - ")
            markup.add(InlineKeyboardButton(text=sign, url=url))
        markup.to_python()
        return markup




