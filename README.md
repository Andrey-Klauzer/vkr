# Выпускная квалификационная работа (ВКР)

* **Название работы:** Разработка конвейера данных по мониторингу валютных пар (Development of a Data Pipeline for Monitoring Currency Pairs)
* **Студент:** Клаузер Андрей Сергеевич
* **Формат работы:** индивидуальная
* **Научный руководитель:** Паточенко Евгений Анатольевич
* **Научный соруководитель:** Заигрин Вадим Валерьевич

---

## Описание проекта

Целью выпускной квалификационной работы является разработка конвейера данных для мониторинга валютных пар, включающего сбор, обработку, анализ и визуализацию данных, а также построение моделей прогнозирования волатильности.

Итогом работы является программный сервис с API и дашбордом.

---

## Основные материалы проекта

* **Репозиторий:** [https://github.com/Andrey-Klauzer/vkr](https://github.com/Andrey-Klauzer/vkr)
* **Полный текст ВКР:** [https://github.com/Andrey-Klauzer/vkr/blob/main/files/VKR.pdf](https://github.com/Andrey-Klauzer/vkr/blob/main/files/VKR.pdf)
* **Отчет об антиплагиате:** [https://github.com/Andrey-Klauzer/vkr/blob/main/files/Report_1.pdf](https://github.com/Andrey-Klauzer/vkr/blob/main/files/Report_1.pdf)
* **Исследовательский ноутбук:** [https://github.com/Andrey-Klauzer/vkr/blob/main/files/Research.ipynb](https://github.com/Andrey-Klauzer/vkr/blob/main/files/Research.ipynb)
* **Программная реализация:** [https://github.com/Andrey-Klauzer/vkr/tree/main/program](https://github.com/Andrey-Klauzer/vkr/tree/main/program)
* **Тестирование API (endpoints):** [https://github.com/Andrey-Klauzer/vkr/blob/main/files/api_test.ipynb](https://github.com/Andrey-Klauzer/vkr/blob/main/files/api_test.ipynb)
* **Airflow (admin/admin):** [https://airflow.vkr-klauzer.ru](https://airflow.vkr-klauzer.ru)
* **Дашборд:** [https://vkr-klauzer.ru](https://vkr-klauzer.ru)
* **API домен:** [https://api.vkr-klauzer.ru](https://api.vkr-klauzer.ru)

---

# Этапы выполнения работы

## Этап 1. Постановка задачи и обзор предметной области

* Формулировка цели и задач ВКР
* Анализ литературы по финансовым временным рядам
* Обзор методов оценки волатильности
* Анализ существующих решений и сервисов

Результат: теоретическая база и постановка задачи (VKR.pdf)

---

## Этап 2. Сбор и подготовка данных

* Загрузка исторических данных валютных пар (yfinance)
* Очистка и нормализация данных
* Формирование датасета

Реализация:
[https://github.com/Andrey-Klauzer/vkr/blob/main/files/Research.ipynb](https://github.com/Andrey-Klauzer/vkr/blob/main/files/Research.ipynb)

---

## Этап 3. Исследовательский анализ данных (EDA)

* Анализ доходностей и распределений
* Исследование волатильности
* Корреляционный анализ
* Выявление аномалий и трендов

Реализация:
[https://github.com/Andrey-Klauzer/vkr/blob/main/files/Research.ipynb](https://github.com/Andrey-Klauzer/vkr/blob/main/files/Research.ipynb)

---

## Этап 4. Построение и оценка моделей

* Генерация признаков
* Построение бейзлайн модели
* Выбор и обоснование метрик
* Разработка продвинутой модели
* Сравнение моделей

Реализация:
[https://github.com/Andrey-Klauzer/vkr/blob/main/files/Research.ipynb](https://github.com/Andrey-Klauzer/vkr/blob/main/files/Research.ipynb)

---

## Этап 5. Разработка конвейера и сервиса

* Проектирование ETL/data pipeline
* Реализация обработки и обновления данных
* Интеграция модели
* Разработка API
* Тестирование API endpoints

Код:
[https://github.com/Andrey-Klauzer/vkr/tree/main/program](https://github.com/Andrey-Klauzer/vkr/tree/main/program)

Тесты API:
[https://github.com/Andrey-Klauzer/vkr/blob/main/files/api_test.ipynb](https://github.com/Andrey-Klauzer/vkr/blob/main/files/api_test.ipynb)

API:
[https://api.vkr-klauzer.ru](https://api.vkr-klauzer.ru)

---

## Этап 6. Визуализация, интеграция и финальные результаты

* Разработка дашборда (Streamlit)
* Визуализация данных и прогнозов
* Интеграция всех компонентов
* Тестирование и оптимизация
* Формирование итоговых выводов

Дашборд:
[https://vkr-klauzer.ru](https://vkr-klauzer.ru)
