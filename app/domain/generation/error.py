# app/domain/generation/errors.py
from dataclasses import dataclass

@dataclass
class GenerationError(Exception):
    code: str
    technical: str | None = None

# Короткие тексты только по делу (без советов/подсказок)
PUBLIC_MESSAGES_RU = {
    "INSUFFICIENT_CREDITS": "Пожалуйста, свяжитесь с поддержкой @guard_gpt.",
    "NON_ENGLISH_PROMPT":          "Не удалось сгенерировать видео. Измените промт или попробуйте другое фото..",
    "UNSAFE_CONTENT":              "Запрос отклонён правилами безопасности.",
    "PROMINENT_PEOPLE_UPLOAD":     "Нельзя использовать изображения с узнаваемыми публичными персонами.",
    "PHOTOREAL_UPLOAD":            "Фотореалистичные лица в загрузке не допускаются.",
    "MODERATION_FAILED":           "Запрос отклонён модерацией.\n\nИзмените промт",
    "GOOGLE_DECLINED": "Провайдер отказал в обработке.\nПотраченные генерации возвращены на ваш баланс.",
    "TASK_FAILED":                 "Не удалось сгенерировать видео. Измените промт или попробуйте другое фото..",
    "TASK_NOT_FOUND":              "Задача не найдена.",
    "INVALID_TASK_ID":             "Неверный формат ID.",
    "TIMEOUT":                     "Превышено время обработки,попробуйте еще раз.",
    "MAINTENANCE":                 "Сервис недоступен (техработы), генерации возвращены.",
    "INVALID_IMAGE":               "Файл не является корректным изображением.",
    "IMAGE_TOO_LARGE":             "Размер изображения превышает 20 МБ.",
    "UNSUPPORTED_IMAGE_FORMAT":    "Формат изображения не поддерживается.",
}

RETRYABLE = {
    "GOOGLE_DECLINED", "TIMEOUT", "MAINTENANCE", "TASK_FAILED"
}

def to_user_message(code: str) -> str:
    return PUBLIC_MESSAGES_RU.get(code, "Не удалось запустить генерацию. Попробуйте позже.")
