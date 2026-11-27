# models.py
from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine(
    "sqlite:///./app.db",
    connect_args={"check_same_thread": False},  # SQLite 特有，见下方"坑 2"
)

# 类母版：所有"表类"都必须继承它
Base = declarative_base()

# 会话工厂：每次操作数据库前用 Session() 开一个会话
Session = sessionmaker(bind=engine)


class History(Base):
    """历史记录表：每次生成二维码存一行"""

    __tablename__ = "history"

    id = Column(Integer, primary_key=True, autoincrement=True)  # 主键：自增编号
    url = Column(String, nullable=False)  # 二维码内容
    color_dark = Column(String, nullable=False)  # 深色（十六进制）
    color_light = Column(String, nullable=False)  # 浅色（十六进制）
    error_correction = Column(String, nullable=False)  # 容错级别 L/M/Q/H
    has_logo = Column(Integer, default=0)  # 是否带 logo：1 有 0 无
    created_at = Column(DateTime, default=datetime.now)  # 创建时间
    user_id = Column(Integer, nullable=True)  # 谁生成的；旧数据没有主人，允许为空


class User(Base):
    """用户表：注册时存一行"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)  # 主键：自增编号
    username = Column(String, nullable=False, unique=True)  # 用户名：唯一，不能重复注册
    password_hash = Column(String, nullable=False)  # 只存哈希，明文永不落库
    created_at = Column(DateTime, default=datetime.now)  # 注册时间


class Token(Base):
    """登录令牌表：谁、拿着哪张通行证"""

    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String, nullable=False, unique=True)  # 通行证本身
    user_id = Column(Integer, nullable=False)  # 谁的通行证
    created_at = Column(DateTime, default=datetime.now)  # 签发时间
    expires_at = Column(DateTime, nullable=False)  # 过期时间：到期即失效
