import os

class Config:
    SECRET_KEY = "supersecretkey"

    MYSQL_HOST = os.getenv("MYSQLHOST")
    MYSQL_USER = os.getenv("MYSQLUSER")
    MYSQL_PASSWORD = os.getenv("MYSQLPASSWORD")
    MYSQL_DB = os.getenv("MYSQLDATABASE")
    MYSQL_PORT = int(os.getenv("MYSQLPORT", 3306))