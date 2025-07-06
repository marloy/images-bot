from aiogram import Router, F
from aiogram.types import Message
from io import BytesIO
from datetime import datetime
from utils.yandex_upload import upload_bytes

router = Router()

async def upload_media_to_yandex(message: Message, file_id: str, suffix: str):
    thread_id = str(message.message_thread_id or "default")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{message.from_user.id}_{timestamp}{suffix}"
    remote_path = f"TelegramMedia/{thread_id}/{filename}"

    # Получаем файл в память
    file_bytes = BytesIO()
    await message.bot.download(file_id, destination=file_bytes)
    file_bytes.seek(0)

    try:
        upload_bytes(file_bytes.read(), remote_path)
        await message.reply(f"✅ Загружено: `{remote_path}`", parse_mode="Markdown")
    except Exception as e:
        await message.reply(f"❌ Ошибка загрузки: {e}")

@router.message(F.photo)
async def handle_photo(message: Message):
    photo = message.photo[-1]
    await upload_media_to_yandex(message, photo.file_id, ".jpg")

@router.message(F.video)
async def handle_video(message: Message):
    video = message.video
    await upload_media_to_yandex(message, video.file_id, ".mp4")