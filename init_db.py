# init_db.py
# 一次性手动建表脚本：python3 init_db.py
from models import Base, engine

Base.metadata.create_all(engine)
print("数据库初始化完成")
