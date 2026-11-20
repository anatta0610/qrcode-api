from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse
import qrcode
from io import BytesIO
from PIL import Image

app = FastAPI()


@app.post('/generate')
async def generate(
    url: str = Form(),
    width: int = Form(default=256),
    error_correction: str = Form(default='H'),
    color_dark: str = Form(default='#000000'),
    color_light: str = Form(default='#ffffff'),
    logo: UploadFile = File(default=None),
):
    # 容错级别映射
    ec_map = {
        'L': qrcode.constants.ERROR_CORRECT_L,
        'M': qrcode.constants.ERROR_CORRECT_M,
        'Q': qrcode.constants.ERROR_CORRECT_Q,
        'H': qrcode.constants.ERROR_CORRECT_H,
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
    ).convert('RGBA')

    # 处理 Logo
    if logo:
        logo_img = Image.open(logo.file).convert('RGBA')
        qr_size = min(img.size)
        logo_size = int(qr_size * 0.2)
        logo_img = logo_img.resize((logo_size, logo_size))

        # 白色底板
        pad = int(logo_size * 0.1)
        bg = Image.new('RGBA', (logo_size + pad * 2, logo_size + pad * 2), '#ffffff')

        pos = ((qr_size - logo_size) // 2, (qr_size - logo_size) // 2)
        img.paste(bg, (pos[0] - pad, pos[1] - pad), bg)
        img.paste(logo_img, pos, logo_img)

    # 输出图片
    buf = BytesIO() 
    img.save(buf, format='PNG')
    buf.seek(0)

    return StreamingResponse(buf, media_type='image/png')