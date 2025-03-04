!pip install gigachat

with open('creds','r') as f:
  kkeys = f.read()
  
import re
import pandas as pd
from gigachat import GigaChat


def vopros(question, answer):
    with GigaChat(credentials=kkeys, verify_ssl_certs=False) as giga:
        prompt = (f"Является ли ответ '{answer}' на вопрос '{question}' правильным? "
                  "Оцени правильность ответа и напиши цифру от 1 до 10.")
        response = giga.chat(prompt)
        return response.choices[0].message.content

if __name__ == "__main__":
    file_path = 'new_form.csv'  # Укажите путь к вашему CSV файлу
    questions, answers = parse_google_form_csv(file_path)

    # Список для хранения данных
    data = []

    for identifier, participant_answers in answers.items():
        for question, answer in zip(questions[1:], participant_answers):
            # Если ответ пустой, сразу выставляем балл 0
            if not answer.strip():
                score = 0
            else:
                text = vopros(question, answer)
                try:
                    numbers = re.findall(r'\d+', text)
                    score = next(int(num) for num in numbers if 1 <= int(num) <= 10)
                except StopIteration:
                    score = 'N/A'
            data.append({
                'Identifier': identifier,
                'Question': question,
                'Answer': answer,
                'Score': score
            })

df = pd.DataFrame(data)
output_file = 'Giga_chat_results.csv'
df.to_csv(output_file, index=False, encoding='utf-8-sig')