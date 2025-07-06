import asyncio
import logging
from collections import defaultdict

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from config import TELEGRAM_TOKEN
from utils.yandex_upload import upload_bytes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

GROUP_TIMEOUT = 1.0  # секунды ожидания конца альбома

media_groups = defaultdict(list)          # buffer для сообщений по media_group_id
media_group_timers = dict()               # таймеры для отложенной обработки


class MediaProcessor:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def process(self, message: types.Message):
        media_info = await self.extract_media_info(message)
        if not media_info:
            return

        file_id, ext = media_info
        data = await self.download_file(file_id)
        if not data:
            logger.error("Не удалось скачать файл.")
            return

        topic_id = message.message_thread_id or "no_topic"
        chat_id = message.chat.id or "no_chat"
        filename = f"{message.from_user.id}_{message.message_id}_{int(message.date.timestamp())}.{ext}"
        remote_path = f"TelegramMedia/{chat_id}/{topic_id}/{filename}"

        logger.info(f"Начинаем загрузку файла: {remote_path}")
        try:
            upload_bytes(data, remote_path)
            logger.info(f"Файл успешно загружен: {remote_path}")
        except Exception as e:
            logger.error(f"Ошибка загрузки на Яндекс.Диск: {e}")
            await message.reply("Ошибка загрузки файла на диск.")

    async def extract_media_info(self, message: types.Message):
        if message.photo:
            return message.photo[-1].file_id, "jpg"
        if message.video:
            return message.video.file_id, "mp4"
        if message.document:
            mime = message.document.mime_type or ""
            if mime.startswith("image/") or mime.startswith("video/"):
                ext = mime.split("/")[-1]
                return message.document.file_id, ext
        return None

    async def download_file(self, file_id: str) -> bytes | None:
        try:
            file = await self.bot.get_file(file_id)
            file_bytes_io = await self.bot.download_file(file.file_path)
            return file_bytes_io.read()
        except Exception as e:
            logger.error(f"Ошибка скачивания файла: {e}")
            return None


media_processor = MediaProcessor(bot)


async def process_media_group(media_group_id: str):
    messages = media_groups.pop(media_group_id, [])
    media_group_timers.pop(media_group_id, None)

    if not messages:
        return

    logger.info(f"Обработка медиагруппы {media_group_id} из {len(messages)} файлов")
    for message in messages:
        await media_processor.process(message)


async def delayed_process_media_group(media_group_id: str):
    await asyncio.sleep(GROUP_TIMEOUT)
    await process_media_group(media_group_id)


@dp.message(Command(commands=["start", "help"]))
async def start_handler(message: types.Message):
    await message.answer(
        "Привет! Отправь фото, видео или документ с фото/видео — я сохраню их на Яндекс.Диск по топикам."
    )


@dp.message()
async def all_media_handler(message: types.Message):
    if message.media_group_id:
        # Кладём в буфер
        media_groups[message.media_group_id].append(message)

        # Сбрасываем таймер, если есть
        if message.media_group_id in media_group_timers:
            media_group_timers[message.media_group_id].cancel()

        # Запускаем новый таймер на обработку группы через GROUP_TIMEOUT секунд
        media_group_timers[message.media_group_id] = asyncio.create_task(
            delayed_process_media_group(message.media_group_id)
        )
    else:
        # Одиночные сообщения обрабатываем сразу
        await media_processor.process(message)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())