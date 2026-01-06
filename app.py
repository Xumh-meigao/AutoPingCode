# --*-- conding:utf-8 --*--
# @Time : 2025/11/05 13:54
# @Author : Xumh
from flask_app.sync_bugs_app import app

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5432,
        debug=True
    )
