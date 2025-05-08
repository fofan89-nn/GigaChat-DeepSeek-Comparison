import csv
import sys
import requests
import asyncio
from googletrans import Translator
import re
import pandas as pd

# URL API Ollama (deepseek)
OLLAMA_API_URL = "http://127.0.0.1:11434/api/chat"

# Инициализация переводчика
translator = Translator()

def parse_google_form_csv(file_path):
    """
    Парсит CSV файл, полученный из Google Формы.
    """
    with open(file_path, mode='r') as file:
        reader = csv.reader(file)
        questions = next(reader)
        answers = {}
        for row in reader:
            if row:
                identifier = row[0]
                answer_data = row[1:]
                answers[identifier] = answer_data
    return questions, answers

async def translate_word(text, src='ru', dest='en'):
    """
    Переводит текст с языка src на язык dest асинхронно.
    По умолчанию: с русского (ru) на английский (en).
    """
    translation = await translator.translate(text, src=src, dest=dest)
    return translation.text

async def create_messages(answer, question):
    """
    Создает список сообщений для отправки в API deepseek.
    """
    translated_question = await translate_word(question, src='ru', dest='en')
    translated_answer = await translate_word(answer, src='ru', dest='en')
    
    prompt = (
        f"Is the answer '{translated_answer}' to the question '{translated_question}'? "
        "Rate the answer and give answer which looks like this: 'Rating: X. Explanation: Y', where X is a rating between 1 to 10."
    )
    
    messages = [{'role': 'user', 'content': prompt}]
    return messages

def chat_with_ollama(model, messages):
    """
    Отправляет запрос к API Ollama (deepseek) и возвращает ответ ассистента.
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        if ('message' in result and
            'role' in result['message'] and
            result['message']['role'] == 'assistant'):
            return result['message']['content']
        else:
            return "Не удалось получить ответ от ассистента."
    except requests.exceptions.RequestException as e:
        return f"Error communicating with Ollama: {e}"

def parse_evaluation(evaluation):
    """
    Парсит ответ от модели deepseek, извлекая рейтинг и объяснение.
    Ожидается, что ответ будет в формате: 'Rating: X. Explanation: Y'.
    """
    try:
        rating_match = re.search(r'Rating:\s*(\d+)', evaluation, re.IGNORECASE)
        explanation_match = re.search(r'Explanation:\s*(.+)', evaluation, re.IGNORECASE)

        rating = int(rating_match.group(1)) if rating_match else "N/A"
        explanation = explanation_match.group(1).strip() if explanation_match else "N/A"

        return rating, explanation
    except Exception as e:
        print(f"Ошибка при парсинге ответа: {e}")
    return "N/A", "N/A"

def save_to_csv(data, output_file):
    """
    Сохраняет данные в CSV файл.
    """
    with open(output_file, mode='w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Identifier', 'Question', 'Answer', 'Rating', 'Explanation'])
        for row in data:
            writer.writerow(row)

async def main():
    # Если путь к CSV файлу передан через аргументы командной строки, используем его
    file_path = sys.argv[1] if len(sys.argv) > 1 else 'new_form+.csv'

    # Читаем CSV
    questions, answers_dict = parse_google_form_csv(file_path)
    print("Заголовки (questions):")
    print(questions)
    print("=" * 50)

    question_texts = questions[1:]
    model = "deepseek-r1:1.5b"

    results = []

    for identifier, answer_list in answers_dict.items():
        print(f"Оценка ответа для записи: {identifier}")

        for idx, answer in enumerate(answer_list):
            question = question_texts[idx]
            
            # Пропускаем запрос, если ответ пустой
            if not answer.strip():
                print(f"Пропущен пустой ответ для вопроса: {question}")
                continue
            
            messages = await create_messages(answer, question)
            evaluation = chat_with_ollama(model, messages)
            
            print(f"Вопрос: {question}")
            print(f"Ответ: {answer}")
            print("Оценка от deepseek:")
            print(evaluation)
            print("-" * 40)

            # Извлекаем рейтинг и объяснение
            rating, explanation = parse_evaluation(evaluation)

            # Сохраняем результаты
            results.append([identifier, question, answer, rating, explanation])

    # Сохраняем результаты в CSV
    output_file = 'evaluation_results.csv'
    save_to_csv(results, output_file)
    print(f"Результаты сохранены в файл {output_file}")

if __name__ == "__main__":
    asyncio.run(main())