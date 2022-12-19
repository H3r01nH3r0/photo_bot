import datetime
import sqlite3
from pyairtable import Table

class DataBase:
    def __init__(self, api, base_api, table, db_file):
        self.table = Table(api, base_api, table)
        self.connection = sqlite3.connect(db_file, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_order (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            recipient VARCHAR,
            address VARCHAR,
            photos VARCHAR,
            picture_text VARCHAR,
            price INTEGER,
            user_name VARCHAR
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE
            )
            """
        )


    def check_user(self, user_id):
        with self.connection:
            res = self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchall()
            return bool(len(res))

    def add_user(self, user_id):
        with self.connection:
            return self.cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))

    def get_users(self):
        with self.connection:
            res = self.cursor.execute("SELECT user_id FROM users").fetchall()
            print(res)
            return res

    def get_users_count(self):
        with self.connection:
            res = self.cursor.execute("SELECT user_id FROM users").fetchall()
            return len(res)

    def check_user_order(self, user_id):
        with self.connection:
            res = self.cursor.execute("SELECT * FROM user_order WHERE user_id = ?", (user_id,)).fetchall()
            return bool(len(res))

    def add_user_order(self, user_id, user_name):
        with self.connection:
            return self.cursor.execute("INSERT INTO user_order (user_id, user_name) VALUES (?, ?)", (user_id, user_name,))

    def update_user_name(self, name, user_id):
        with self.connection:
            return self.cursor.execute("UPDATE user_order SET recipient = ? WHERE user_id = ?", (name, user_id,))

    def get_user_name(self, user_id):
        with self.connection:
            res = self.cursor.execute("SELECT recipient FROM user_order WHERE user_id = ?", (user_id,)).fetchone()
            return res[0]

    def update_user_address(self, address, user_id):
        with self.connection:
            return self.cursor.execute("UPDATE user_order SET address = ? WHERE user_id = ?", (address, user_id,))

    def update_user_picture_text(self, text, user_id):
        with self.connection:
            return self.cursor.execute("UPDATE user_order SET picture_text = ? WHERE user_id = ?", (text, user_id,))

    def get_user_address(self, user_id):
        with self.connection:
            res = self.cursor.execute("SELECT address FROM user_order WHERE user_id = ?", (user_id,)).fetchone()
            return res[0]

    def update_users_photos(self, user_id, photos):
        with self.connection:
            return self.cursor.execute("UPDATE user_order SET photos = ? WHERE user_id = ?", (photos, user_id,))

    def get_users_photos(self, user_id):
        with self.connection:
            res = self.cursor.execute("SELECT photos FROM user_order WHERE user_id = ?", (user_id,)).fetchall()
            return res[0][0]

    def add_user_price(self, user_id, price):
        with self.connection:
            return self.cursor.execute("UPDATE user_order SET price = ? WHERE user_id = ?", (price, user_id,))

    def get_user_order(self, user_id):
        with self.connection:
            res = self.cursor.execute("SELECT * FROM user_order WHERE user_id = ?", (user_id,)).fetchall()
            return res[0]

    def del_order(self, user_id):
        with self.connection:
            return self.cursor.execute("DELETE FROM user_order WHERE user_id = ?", (user_id,))

    def save_to_air_table (self, user_id, user_name, recipient, address, price, photos_links, picture_text):
        dateFormater = "%Y/%m/%d"
        date = datetime.datetime.now()
        date = date.strftime(dateFormater)
        photos = []
        for i in photos_links:
            photo = {"url": f"https://api.telegram.org/file/bot5340023397:AAEYueWUZzEZCW9MCZO0Qwa7eKZTZzhP5Xw/{i}"}
            photos.append(photo)
        self.table.create(
            {"Date": date,
             "user_id": user_id,
             "user_name": user_name,
             "recipient": recipient,
             "address": address,
             "postcard_text": picture_text,
             "order_price": price,
             "picture_link": photos,
             "Status": "Todo"
             }
        )
