import qrcode
from io import BytesIO
from PIL import Image
import bcrypt
import secrets
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import FastAPI, UploadFile, HTTPException, File, Form, Depends
from models import Base, Session, engine, User, Token, History

Base.metadata.create_all(engine)  # 启动时确保表存在（防呆）

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://codepractice.cn",
        "https://codepractice.cn",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    if not credentials:
        raise HTTPException(status_code=401, detail="未登录")
    db = Session()
    row = db.query(Token).filter(Token.token == credentials.credentials).first()
    db.close()
    if not row:
        raise HTTPException(status_code=401, detail="未登录")
    return row.user_id


@app.post("/register")
async def register(username: str = Form(), password: str = Form()):
    if not username or not password:
        return {"error": "用户名和密码不能为空"}

    db = Session()
    exists = db.query(User).filter(User.username == username).first()
    if exists:
        db.close()
        return {"error": "用户名已存在"}

    # 哈希后入库；decode 是把 bytes 转回 str，方便 SQLite 存取
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
    db.add(User(username=username, password_hash=hashed))
    db.commit()
    db.close()
    return {"ok": True}


@app.post("/login")
async def login(username: str = Form(), password: str = Form()):
    db = Session()
    user = db.query(User).filter(User.username == username).first()
    # 用户不存在 和 密码错误 返回同一句话：不告诉攻击者到底是哪一步错了
    if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        db.close()
        return {"error": "用户名或密码错误"}
    token = secrets.token_hex(32)  # 32 字节随机数 → 64 位十六进制
    db.add(Token(token=token, user_id=user.id))
    db.commit()
    db.close()
    return {"token": token}


@app.post("/register")
async def register(username: str = Form(), password: str = Form()):
    if not username or not password:
        return {"error": "用户名和密码不能为空"}

    db = Session()
    exists = db.query(User).filter(User.username == username).first()
    if exists:
        db.close()
        return {"error": "用户名已存在"}

    # 哈希后入库；decode 是把 bytes 转回 str，方便 SQLite 存取
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
    db.add(User(username=username, password_hash=hashed))
    db.commit()
    db.close()
    return {"ok": True}


@app.post("/login")
async def login(username: str = Form(), password: str = Form()):
    db = Session()
    user = db.query(User).filter(User.username == username).first()
    # 用户不存在 和 密码错误 返回同一句话：不告诉攻击者到底是哪一步错了
    if not user or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        db.close()
        return {"error": "用户名或密码错误"}
    token = secrets.token_hex(32)  # 32 字节随机数 → 64 位十六进制
    db.add(Token(token=token, user_id=user.id))
    db.commit()
    db.close()
    return {"token": token}


@app.post("/generate")
async def generate(
    url: str = Form(),
    width: int = Form(default=256),
    error_correction: str = Form(default="H"),
    color_dark: str = Form(default="#000000"),
    color_light: str = Form(default="#ffffff"),
    logo: UploadFile = File(default=None),
    user_id: int = Depends(get_current_user),
):
    # 容错级别映射
    ec_map = {
        "L": qrcode.constants.ERROR_CORRECT_L,
        "M": qrcode.constants.ERROR_CORRECT_M,
        "Q": qrcode.constants.ERROR_CORRECT_Q,
        "H": qrcode.constants.ERROR_CORRECT_H,
    }
    ec = ec_map.get(error_correction, qrcode.constants.ERROR_CORRECT_H)

    # 生成二维码
    qr = qrcode.QRCode(
        version=None,
        error_correction=ec,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(
        fill_color=color_dark,
        back_color=color_light,
    ).convert("RGBA")

    # 处理 Logo
    if logo:
        try:
            logo_img = Image.open(logo.file).convert("RGBA")
            qr_size = min(img.size)
            logo_size = int(qr_size * 0.2)
            logo_img = logo_img.resize((logo_size, logo_size))

            # 白色底板
            pad = int(logo_size * 0.1)
            bg = Image.new(
                "RGBA", (logo_size + pad * 2, logo_size + pad * 2), "#ffffff"
            )

            pos = ((qr_size - logo_size) // 2, (qr_size - logo_size) // 2)
            img.paste(bg, (pos[0] - pad, pos[1] - pad), bg)
            img.paste(logo_img, pos, logo_img)
        except Exception:
            pass

    # 输出图片
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    # 保存历史记录
    db = Session()
    db.add(
        History(
            url=url,
            color_dark=color_dark,
            color_light=color_light,
            error_correction=error_correction,
            has_logo=1 if logo else 0,
            user_id=user_id,
        )
    )
    db.commit()
    db.close()

    return StreamingResponse(buf, media_type="image/png")


@app.get("/history")
def history(user_id: int = Depends(get_current_user)):
    db = Session()
    rows = (
        db.query(History)
        .filter(History.user_id == user_id)
        .order_by(History.created_at.desc())
        .limit(20)
        .all()
    )
    db.close()
    return [
        {
            "id": r.id,
            "url": r.url,
            "color_dark": r.color_dark,
            "color_light": r.color_light,
            "error_correction": r.error_correction,
            "has_logo": r.has_logo,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@app.get("/me")
def me(user_id: int = Depends(get_current_user)):
    db = Session()
    user = db.query(User).filter(User.id == user_id).first()
    db.close()
    return {"username": user.username}
