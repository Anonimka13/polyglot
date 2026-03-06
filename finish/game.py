import sys
import random
import time
import os
from datetime import datetime

import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import speech_recognition as sr

from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import *

# Словари для разных языков и уровней сложности
# Английский
english_easy = {
    "apple": "яблоко",
    "cat": "кот",
    "dog": "собака",
    "house": "дом",
    "book": "книга",
    "car": "машина",
    "sun": "солнце",
    "moon": "луна"
}

english_medium = {
    "computer": "компьютер",
    "garden": "сад",
    "library": "библиотека",
    "teacher": "учитель",
    "student": "ученик",
    "beautiful": "красивый",
    "mountain": "гора",
    "ocean": "океан"
}

english_hard = {
    "environment": "окружающая среда",
    "architecture": "архитектура",
    "responsibility": "ответственность",
    "communication": "общение",
    "international": "международный",
    "accommodation": "размещение",
    "accomplishment": "достижение",
    "acknowledgment": "признание"
}

# Итальянский
italian_easy = {
    "ciao": "привет",
    "gatto": "кот",
    "cane": "собака",
    "casa": "дом",
    "libro": "книга",
    "sole": "солнце",
    "luna": "луна",
    "acqua": "вода"
}

italian_medium = {
    "ragazzo": "мальчик",
    "ragazza": "девочка",
    "scuola": "школа",
    "amico": "друг",
    "famiglia": "семья",
    "viaggio": "путешествие",
    "città": "город",
    "montagna": "гора"
}

italian_hard = {
    "incredibile": "невероятный",
    "responsabilità": "ответственность",
    "comunicazione": "общение",
    "internazionale": "международный",
    "accomodamento": "размещение",
    "realizzazione": "достижение",
    "riconoscimento": "признание"
}

# Испанский
spanish_easy = {
    "hola": "привет",
    "gato": "кот",
    "perro": "собака",
    "casa": "дом",
    "libro": "книга",
    "sol": "солнце",
    "luna": "луна",
    "agua": "вода"
}

# Французский
french_easy = {
    "bonjour": "привет",
    "chat": "кот",
    "chien": "собака",
    "maison": "дом",
    "livre": "книга",
    "soleil": "солнце",
    "lune": "луна",
    "eau": "вода"
}

# Португальский
portuguese_easy = {
    "olá": "привет",
    "gato": "кот",
    "cachorro": "собака",
    "casa": "дом",
    "livro": "книга",
    "sol": "солнце",
    "lua": "луна",
    "água": "вода"
}

# Предложения для режима "Закончить предложение"
english_sentences = {
    "I like to read a _____": "book",
    "The sky is _____": "blue",
    "My name _____ John": "is",
    "I have two _____": "cats"
}

italian_sentences = {
    "Mi piace leggere un _____": "libro",
    "Il cielo è _____": "blu",
    "Mi _____ Mario": "chiamo",
    "Ho due _____": "gatti"
}

# Вопросы для тестов
english_tests = [
    {
        "question": "Как будет 'яблоко' по-английски?",
        "options": ["apple", "aple", "appple", "apel"],
        "answer": "apple"
    },
    {
        "question": "Как будет 'книга' по-английски?",
        "options": ["buk", "book", "boook", "boke"],
        "answer": "book"
    }
]

italian_tests = [
    {
        "question": "Как будет 'кот' по-итальянски?",
        "options": ["gato", "gatto", "gatoo", "gattto"],
        "answer": "gatto"
    }
]

class RecordThread(QThread):
    """Поток для записи голоса"""
    finished = pyqtSignal(str)
    progress = pyqtSignal(int)
    
    def __init__(self):
        super().__init__()
        self.duration = 3
        self.sample_rate = 44100
        
    def run(self):
        try:
            recording = sd.rec(
                int(self.duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype='int16'
            )
            
            for i in range(self.duration):
                self.progress.emit(i + 1)
                time.sleep(1)
            
            filename = 'recording.wav'
            wav.write(filename, self.sample_rate, recording)
            self.finished.emit(filename)
        except Exception as e:
            self.finished.emit(f"ERROR: {str(e)}")

class SpeechThread(QThread):
    """Поток для распознавания речи"""
    finished = pyqtSignal(str)
    
    def __init__(self, filename, language_code):
        super().__init__()
        self.filename = filename
        self.language_code = language_code
        
    def run(self):
        recognizer = sr.Recognizer()
        try:
            with sr.AudioFile(self.filename) as source:
                audio = recognizer.record(source)
                text = recognizer.recognize_google(audio, language=self.language_code)
                self.finished.emit(text.lower())
        except sr.UnknownValueError:
            self.finished.emit("ERROR: Не удалось распознать речь")
        except sr.RequestError:
            self.finished.emit("ERROR: Ошибка сервиса")
        except Exception as e:
            self.finished.emit(f"ERROR: {str(e)}")
        finally:
            if os.path.exists(self.filename):
                os.remove(self.filename)

class GameWindow(QWidget):
    """Главное окно игры"""
    
    def __init__(self):
        super().__init__()
        self.stats = []
        self.current_language = None
        self.current_mode = None
        self.current_difficulty = None
        self.current_words = []
        self.current_word_index = 0
        self.score = 0
        self.lives = 3
        self.waiting_for_next = False  # Флаг ожидания перехода к следующему слову
        self.initUI()
        
    def initUI(self):
        """Инициализация интерфейса"""
        self.setWindowTitle('🎮 POLYGLOT - Изучай языки играя')
        self.setGeometry(100, 100, 900, 600)
        self.setMinimumSize(800, 500)
        
        # Устанавливаем фиолетово-черный стиль
        self.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                font-family: Arial;
                color: #e0e0e0;
            }
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 14px;
                border-radius: 5px;
                min-width: 100px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
            QPushButton:pressed {
                background-color: #6c3483;
            }
            QPushButton:disabled {
                background-color: #4a4a4a;
                color: #888888;
            }
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                border: 2px solid #9b59b6;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                color: #e0e0e0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #9b59b6;
            }
            QLabel {
                font-size: 14px;
                color: #e0e0e0;
            }
            QRadioButton {
                font-size: 14px;
                padding: 5px;
                color: #e0e0e0;
            }
            QRadioButton::indicator {
                width: 15px;
                height: 15px;
            }
            QRadioButton::indicator:checked {
                background-color: #9b59b6;
                border: 2px solid #9b59b6;
                border-radius: 8px;
            }
            QLineEdit {
                padding: 8px;
                font-size: 14px;
                border: 2px solid #9b59b6;
                border-radius: 5px;
                background-color: #2d2d2d;
                color: #e0e0e0;
            }
            QLineEdit:focus {
                border-color: #e0e0e0;
            }
            QProgressBar {
                border: 2px solid #9b59b6;
                border-radius: 5px;
                text-align: center;
                color: #e0e0e0;
                background-color: #2d2d2d;
            }
            QProgressBar::chunk {
                background-color: #9b59b6;
                border-radius: 3px;
            }
            QTextEdit {
                background-color: #2d2d2d;
                border: 2px solid #9b59b6;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
                color: #e0e0e0;
            }
            QMenuBar {
                background-color: #1a1a1a;
                color: #e0e0e0;
            }
            QMenuBar::item {
                background-color: #1a1a1a;
                color: #e0e0e0;
                padding: 5px 10px;
            }
            QMenuBar::item:selected {
                background-color: #9b59b6;
                color: white;
            }
            QMenu {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #9b59b6;
            }
            QMenu::item:selected {
                background-color: #9b59b6;
                color: white;
            }
        """)
        
        # Главный layout
        main_layout = QVBoxLayout()
        
        # Заголовок
        title_label = QLabel('🎮 POLYGLOT')
        title_label.setStyleSheet("""
            font-size: 36px;
            font-weight: bold;
            color: #9b59b6;
            padding: 20px;
            qproperty-alignment: AlignCenter;
        """)
        main_layout.addWidget(title_label)
        
        subtitle = QLabel('Изучай языки в игровой форме!')
        subtitle.setStyleSheet("""
            font-size: 18px;
            color: #b0b0b0;
            padding: 10px;
            qproperty-alignment: AlignCenter;
        """)
        main_layout.addWidget(subtitle)
        
        # Создаем stacked widget для переключения между экранами
        self.stacked_widget = QStackedWidget()
        
        # Экран выбора
        self.selection_screen = self.create_selection_screen()
        self.stacked_widget.addWidget(self.selection_screen)
        
        # Экран игры
        self.game_screen = self.create_game_screen()
        self.stacked_widget.addWidget(self.game_screen)
        
        # Экран статистики
        self.stats_screen = self.create_stats_screen()
        self.stacked_widget.addWidget(self.stats_screen)
        
        main_layout.addWidget(self.stacked_widget)
        
        self.setLayout(main_layout)
        
    def create_selection_screen(self):
        """Создание экрана выбора"""
        screen = QWidget()
        layout = QVBoxLayout()
        
        # Группа выбора языка
        lang_group = QGroupBox("🌍 Выберите язык:")
        lang_layout = QVBoxLayout()
        
        self.lang_english = QRadioButton("🇬🇧 Английский")
        self.lang_italian = QRadioButton("🇮🇹 Итальянский")
        self.lang_spanish = QRadioButton("🇪🇸 Испанский")
        self.lang_french = QRadioButton("🇫🇷 Французский")
        self.lang_portuguese = QRadioButton("🇵🇹 Португальский")
        
        self.lang_english.setChecked(True)
        
        lang_layout.addWidget(self.lang_english)
        lang_layout.addWidget(self.lang_italian)
        lang_layout.addWidget(self.lang_spanish)
        lang_layout.addWidget(self.lang_french)
        lang_layout.addWidget(self.lang_portuguese)
        
        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)
        
        # Группа выбора режима
        mode_group = QGroupBox("🎮 Выберите режим:")
        mode_layout = QVBoxLayout()
        
        self.mode_oral = QRadioButton("🗣️ Устный (говори слова)")
        self.mode_writing = QRadioButton("✍️ Письменный (пиши слова)")
        self.mode_test = QRadioButton("📝 Тесты (выбирай ответ)")
        self.mode_sentence = QRadioButton("🔤 Закончить предложение")
        
        self.mode_oral.setChecked(True)
        
        mode_layout.addWidget(self.mode_oral)
        mode_layout.addWidget(self.mode_writing)
        mode_layout.addWidget(self.mode_test)
        mode_layout.addWidget(self.mode_sentence)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Группа выбора сложности
        diff_group = QGroupBox("📊 Уровень сложности:")
        diff_layout = QVBoxLayout()
        
        self.diff_easy = QRadioButton("🟢 Легкий")
        self.diff_medium = QRadioButton("🟡 Средний")
        self.diff_hard = QRadioButton("🔴 Сложный")
        
        self.diff_easy.setChecked(True)
        
        diff_layout.addWidget(self.diff_easy)
        diff_layout.addWidget(self.diff_medium)
        diff_layout.addWidget(self.diff_hard)
        
        diff_group.setLayout(diff_layout)
        layout.addWidget(diff_group)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        start_btn = QPushButton("🚀 Начать игру")
        start_btn.clicked.connect(self.start_game)
        
        stats_btn = QPushButton("📊 Статистика")
        stats_btn.clicked.connect(self.show_stats)
        
        quit_btn = QPushButton("🚪 Выход")
        quit_btn.clicked.connect(QApplication.quit)
        
        button_layout.addWidget(start_btn)
        button_layout.addWidget(stats_btn)
        button_layout.addWidget(quit_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        screen.setLayout(layout)
        return screen
    
    def create_game_screen(self):
        """Создание экрана игры"""
        screen = QWidget()
        layout = QVBoxLayout()
        
        # Верхняя панель с информацией
        info_layout = QHBoxLayout()
        
        self.score_label = QLabel("Счет: 0")
        self.score_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #9b59b6;")
        
        self.lives_label = QLabel("Жизни: ❤️❤️❤️")
        self.lives_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ff6b6b;")
        
        self.progress_label = QLabel("Слово 0/0")
        self.progress_label.setStyleSheet("font-size: 16px; color: #b0b0b0;")
        
        info_layout.addWidget(self.score_label)
        info_layout.addStretch()
        info_layout.addWidget(self.progress_label)
        info_layout.addStretch()
        info_layout.addWidget(self.lives_label)
        
        layout.addLayout(info_layout)
        
        # Карточка с заданием
        card_widget = QFrame()
        card_widget.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 2px solid #9b59b6;
                border-radius: 10px;
                padding: 20px;
                margin: 20px;
            }
        """)
        card_layout = QVBoxLayout()
        
        self.task_label = QLabel("Задание появится здесь")
        self.task_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #b0b0b0; qproperty-alignment: AlignCenter;")
        
        self.word_label = QLabel("")
        self.word_label.setStyleSheet("font-size: 36px; font-weight: bold; color: #9b59b6; qproperty-alignment: AlignCenter;")
        
        card_layout.addWidget(self.task_label)
        card_layout.addWidget(self.word_label)
        card_widget.setLayout(card_layout)
        layout.addWidget(card_widget)
        
        # Область для ввода/выбора ответа
        self.input_widget = QStackedWidget()
        
        # Для устного режима
        oral_widget = QWidget()
        oral_layout = QVBoxLayout()
        
        self.record_btn = QPushButton("🎤 Начать запись")
        self.record_btn.setStyleSheet("font-size: 18px; padding: 15px;")
        self.record_btn.clicked.connect(self.start_recording)
        
        self.record_progress = QProgressBar()
        self.record_progress.setVisible(False)
        
        self.record_status = QLabel("")
        self.record_status.setStyleSheet("font-size: 14px; color: #b0b0b0; qproperty-alignment: AlignCenter;")
        
        oral_layout.addWidget(self.record_btn)
        oral_layout.addWidget(self.record_progress)
        oral_layout.addWidget(self.record_status)
        oral_widget.setLayout(oral_layout)
        
        # Для письменного режима
        writing_widget = QWidget()
        writing_layout = QVBoxLayout()
        
        self.answer_input = QLineEdit()
        self.answer_input.setPlaceholderText("Введите ваш ответ...")
        self.answer_input.returnPressed.connect(self.check_writing_answer)
        
        self.submit_btn = QPushButton("✅ Проверить")
        self.submit_btn.clicked.connect(self.check_writing_answer)
        
        writing_layout.addWidget(self.answer_input)
        writing_layout.addWidget(self.submit_btn)
        writing_widget.setLayout(writing_layout)
        
        # Для тестов
        test_widget = QWidget()
        test_layout = QVBoxLayout()
        
        self.options_group = QButtonGroup()
        self.option_buttons = []
        
        test_layout.addWidget(QLabel("Выберите правильный ответ:"))
        
        for i in range(4):
            btn = QRadioButton(f"Вариант {i+1}")
            self.options_group.addButton(btn, i)
            test_layout.addWidget(btn)
            self.option_buttons.append(btn)
        
        self.test_submit = QPushButton("✅ Ответить")
        self.test_submit.clicked.connect(self.check_test_answer)
        test_layout.addWidget(self.test_submit)
        
        test_widget.setLayout(test_layout)
        
        # Для предложений
        sentence_widget = QWidget()
        sentence_layout = QVBoxLayout()
        
        self.sentence_input = QLineEdit()
        self.sentence_input.setPlaceholderText("Введите пропущенное слово...")
        self.sentence_input.returnPressed.connect(self.check_sentence_answer)
        
        self.sentence_submit = QPushButton("✅ Проверить")
        self.sentence_submit.clicked.connect(self.check_sentence_answer)
        
        sentence_layout.addWidget(self.sentence_input)
        sentence_layout.addWidget(self.sentence_submit)
        sentence_widget.setLayout(sentence_layout)
        
        self.input_widget.addWidget(oral_widget)
        self.input_widget.addWidget(writing_widget)
        self.input_widget.addWidget(test_widget)
        self.input_widget.addWidget(sentence_widget)
        
        layout.addWidget(self.input_widget)
        
        # Кнопки управления
        control_layout = QHBoxLayout()
        
        self.next_btn = QPushButton("⏭️ Следующее слово")
        self.next_btn.clicked.connect(self.next_word)
        self.next_btn.setVisible(False)
        
        back_btn = QPushButton("🏠 В меню")
        back_btn.clicked.connect(self.back_to_menu)
        
        control_layout.addWidget(self.next_btn)
        control_layout.addStretch()
        control_layout.addWidget(back_btn)
        
        layout.addLayout(control_layout)
        layout.addStretch()
        
        screen.setLayout(layout)
        return screen
    
    def create_stats_screen(self):
        """Создание экрана статистики"""
        screen = QWidget()
        layout = QVBoxLayout()
        
        title = QLabel("📊 Статистика игр")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #9b59b6; qproperty-alignment: AlignCenter;")
        layout.addWidget(title)
        
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setStyleSheet("""
            QTextEdit {
                background-color: #2d2d2d;
                border: 2px solid #9b59b6;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
                color: #e0e0e0;
            }
        """)
        layout.addWidget(self.stats_text)
        
        back_btn = QPushButton("🔙 Назад")
        back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        layout.addWidget(back_btn)
        
        screen.setLayout(layout)
        return screen
    
    def start_game(self):
        """Начало игры"""
        # Определяем выбранный язык
        if self.lang_english.isChecked():
            self.current_language = ('Английский', 'en', english_easy, english_medium, english_hard,
                                    english_sentences, english_tests, english_easy, english_easy)
        elif self.lang_italian.isChecked():
            self.current_language = ('Итальянский', 'it', italian_easy, italian_medium, italian_hard,
                                    italian_sentences, italian_tests, italian_easy, italian_easy)
        elif self.lang_spanish.isChecked():
            self.current_language = ('Испанский', 'es', spanish_easy, spanish_easy, spanish_easy,
                                    english_sentences, english_tests, spanish_easy, spanish_easy)
        elif self.lang_french.isChecked():
            self.current_language = ('Французский', 'fr', french_easy, french_easy, french_easy,
                                    english_sentences, english_tests, french_easy, french_easy)
        else:
            self.current_language = ('Португальский', 'pt', portuguese_easy, portuguese_easy, portuguese_easy,
                                    english_sentences, english_tests, portuguese_easy, portuguese_easy)
        
        # Определяем режим
        if self.mode_oral.isChecked():
            self.current_mode = 1
        elif self.mode_writing.isChecked():
            self.current_mode = 2
        elif self.mode_test.isChecked():
            self.current_mode = 3
        else:
            self.current_mode = 4
        
        # Определяем сложность
        if self.diff_easy.isChecked():
            self.current_difficulty = 1
        elif self.diff_medium.isChecked():
            self.current_difficulty = 2
        else:
            self.current_difficulty = 3
        
        # Загружаем слова
        self.load_words()
        
        # Сбрасываем счет
        self.score = 0
        self.lives = 3
        self.current_word_index = 0
        self.waiting_for_next = False
        
        # Обновляем интерфейс
        self.update_game_display()
        
        # Переключаемся на экран игры
        self.stacked_widget.setCurrentIndex(1)
    
    def load_words(self):
        """Загрузка слов для текущего режима"""
        language_name, code, easy, medium, hard, sentences, tests, writing, oral = self.current_language
        
        if self.current_difficulty == 1:
            words_dict = easy
        elif self.current_difficulty == 2:
            words_dict = medium
        else:
            words_dict = hard
        
        if self.current_mode == 1:  # Устный
            self.current_words = list(oral.items())
        elif self.current_mode == 2:  # Письменный
            self.current_words = list(writing.items())
        elif self.current_mode == 3:  # Тесты
            self.current_words = tests
        else:  # Предложения
            self.current_words = list(sentences.items())
        
        random.shuffle(self.current_words)
    
    def update_game_display(self):
        """Обновление интерфейса игры"""
        # Обновляем счет и жизни
        self.score_label.setText(f"Счет: {self.score}")
        self.lives_label.setText(f"Жизни: {'❤️' * self.lives}")
        self.progress_label.setText(f"Слово {self.current_word_index + 1}/{len(self.current_words)}")
        
        # Показываем правильный режим ввода
        self.input_widget.setCurrentIndex(self.current_mode - 1)
        self.next_btn.setVisible(False)
        self.waiting_for_next = False
        
        # Показываем текущее задание
        if self.current_mode == 1:  # Устный
            eng_word, ru_word = self.current_words[self.current_word_index]
            self.task_label.setText("Произнесите слово:")
            self.word_label.setText(f"🔤 {ru_word}")
            self.record_status.setText("")
            self.record_btn.setEnabled(True)
            
        elif self.current_mode == 2:  # Письменный
            ru_word, eng_word = self.current_words[self.current_word_index]
            self.task_label.setText("Переведите слово:")
            self.word_label.setText(f"🔤 {ru_word}")
            self.answer_input.clear()
            self.answer_input.setFocus()
            
        elif self.current_mode == 3:  # Тесты
            test = self.current_words[self.current_word_index]
            self.task_label.setText(test['question'])
            self.word_label.setText("")
            
            for i, btn in enumerate(self.option_buttons):
                if i < len(test['options']):
                    btn.setText(test['options'][i])
                    btn.setVisible(True)
                else:
                    btn.setVisible(False)
            
            # Снимаем выделение
            self.options_group.setExclusive(False)
            for btn in self.option_buttons:
                btn.setChecked(False)
            self.options_group.setExclusive(True)
            
        else:  # Предложения
            sentence, word = self.current_words[self.current_word_index]
            self.task_label.setText("Закончите предложение:")
            self.word_label.setText(f"📝 {sentence}")
            self.sentence_input.clear()
            self.sentence_input.setFocus()
    
    def start_recording(self):
        """Начать запись голоса"""
        self.record_btn.setEnabled(False)
        self.record_progress.setVisible(True)
        self.record_progress.setValue(0)
        self.record_status.setText("🎤 Говорите!")
        
        # Запускаем запись в отдельном потоке
        self.record_thread = RecordThread()
        self.record_thread.progress.connect(self.update_record_progress)
        self.record_thread.finished.connect(self.recording_finished)
        self.record_thread.start()
    
    def update_record_progress(self, second):
        """Обновление прогресса записи"""
        self.record_progress.setValue(second * 33)  # примерно 33% в секунду
    
    def recording_finished(self, filename):
        """Запись завершена"""
        self.record_progress.setVisible(False)
        
        if filename.startswith("ERROR"):
            self.record_status.setText(f"❌ {filename[6:]}")
            self.record_btn.setEnabled(True)
        else:
            self.record_status.setText("🔄 Распознаю речь...")
            
            # Распознаем речь в отдельном потоке
            language_code = self.current_language[1]
            self.speech_thread = SpeechThread(filename, f'{language_code}-{language_code.upper()}')
            self.speech_thread.finished.connect(self.speech_recognized)
            self.speech_thread.start()
    
    def speech_recognized(self, result):
        """Речь распознана"""
        if result.startswith("ERROR"):
            self.record_status.setText(f"❌ {result[6:]}")
            self.record_btn.setEnabled(True)
            return
        
        eng_word, ru_word = self.current_words[self.current_word_index]
        
        self.record_status.setText(f"📢 Вы сказали: '{result}'")
        
        # Проверяем произношение
        if result.lower() == eng_word.lower():
            self.score += 10
            QMessageBox.information(self, "Отлично!", f"✅ Правильно! +10 баллов")
            # Автоматически переходим к следующему слову
            self.next_word()
        elif eng_word.lower() in result.lower() or result.lower() in eng_word.lower():
            self.score += 5
            QMessageBox.information(self, "Почти!", f"⚠️ Почти правильно! +5 баллов\nПравильно: {eng_word}")
            # Автоматически переходим к следующему слову
            self.next_word()
        else:
            self.lives -= 1
            QMessageBox.warning(self, "Ошибка!", f"❌ Неправильно!\nПравильно: {eng_word}")
            
            if self.lives <= 0:
                self.game_over()
            else:
                # Автоматически переходим к следующему слову
                self.next_word()
    
    def check_writing_answer(self):
        """Проверка письменного ответа"""
        if self.waiting_for_next:
            return
            
        ru_word, eng_word = self.current_words[self.current_word_index]
        answer = self.answer_input.text().lower().strip()
        
        if answer == eng_word:
            self.score += 10
            QMessageBox.information(self, "Отлично!", f"✅ Правильно! +10 баллов")
            self.next_word()
        else:
            self.lives -= 1
            QMessageBox.warning(self, "Ошибка!", f"❌ Неправильно!\nПравильно: {eng_word}")
            
            if self.lives <= 0:
                self.game_over()
            else:
                self.next_word()
    
    def check_test_answer(self):
        """Проверка ответа в тесте"""
        if self.waiting_for_next:
            return
            
        checked_id = self.options_group.checkedId()
        if checked_id == -1:
            QMessageBox.warning(self, "Ошибка!", "Выберите ответ!")
            return
        
        test = self.current_words[self.current_word_index]
        answer = self.option_buttons[checked_id].text()
        
        if answer == test['answer']:
            self.score += 10
            QMessageBox.information(self, "Отлично!", f"✅ Правильно! +10 баллов")
            self.next_word()
        else:
            self.lives -= 1
            QMessageBox.warning(self, "Ошибка!", f"❌ Неправильно!\nПравильно: {test['answer']}")
            
            if self.lives <= 0:
                self.game_over()
            else:
                self.next_word()
    
    def check_sentence_answer(self):
        """Проверка ответа в предложении"""
        if self.waiting_for_next:
            return
            
        sentence, correct_word = self.current_words[self.current_word_index]
        answer = self.sentence_input.text().lower().strip()
        
        if answer == correct_word:
            self.score += 10
            QMessageBox.information(self, "Отлично!", f"✅ Правильно! +10 баллов")
            self.next_word()
        else:
            self.lives -= 1
            QMessageBox.warning(self, "Ошибка!", f"❌ Неправильно!\nПравильно: {correct_word}")
            
            if self.lives <= 0:
                self.game_over()
            else:
                self.next_word()
    
    def next_word(self):
        """Переход к следующему слову"""
        self.waiting_for_next = True
        self.current_word_index += 1
        
        if self.current_word_index >= len(self.current_words):
            self.game_finished()
        else:
            self.update_game_display()
    
    def game_over(self):
        """Игра окончена (проигрыш)"""
        QMessageBox.critical(self, "Game Over!", f"💀 Вы проиграли!\nСчет: {self.score}")
        self.save_stats()
        self.stacked_widget.setCurrentIndex(0)
    
    def game_finished(self):
        """Игра успешно завершена"""
        max_score = len(self.current_words) * 10
        percent = (self.score / max_score) * 100 if max_score > 0 else 0
        
        if percent >= 80:
            message = f"🏆 Отлично! Счет: {self.score}/{max_score}"
        elif percent >= 60:
            message = f"👍 Хорошо! Счет: {self.score}/{max_score}"
        elif percent >= 40:
            message = f"💪 Неплохо! Счет: {self.score}/{max_score}"
        else:
            message = f"🚀 Тренируйся! Счет: {self.score}/{max_score}"
        
        QMessageBox.information(self, "Игра завершена!", message)
        self.save_stats()
        self.stacked_widget.setCurrentIndex(0)
    
    def save_stats(self):
        """Сохранение статистики"""
        language_name = self.current_language[0]
        
        mode_names = ["Устный", "Письменный", "Тест", "Предложения"]
        mode_name = mode_names[self.current_mode - 1]
        
        self.stats.append({
            'date': datetime.now().strftime("%d.%m.%Y %H:%M"),
            'language': language_name,
            'mode': mode_name,
            'score': self.score,
            'total': len(self.current_words) * 10
        })
    
    def show_stats(self):
        """Показать статистику"""
        if not self.stats:
            self.stats_text.setText("📊 Пока нет сыгранных игр")
        else:
            text = ""
            total_score = 0
            games_played = len(self.stats)
            
            for stat in self.stats:
                text += f"\n📅 {stat['date']}\n"
                text += f"   Язык: {stat['language']}\n"
                text += f"   Режим: {stat['mode']}\n"
                text += f"   Счет: {stat['score']}/{stat['total']}\n"
                text += "-" * 40 + "\n"
                total_score += stat['score']
            
            text += f"\n📊 ВСЕГО:\n"
            text += f"   Игр сыграно: {games_played}\n"
            text += f"   Общий счет: {total_score}\n"
            text += f"   Средний счет: {total_score/games_played:.1f}"
            
            self.stats_text.setText(text)
        
        self.stacked_widget.setCurrentIndex(2)
    
    def back_to_menu(self):
        """Возврат в меню"""
        self.stacked_widget.setCurrentIndex(0)

class PolyglotGame(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('🎮 POLYGLOT - Изучай языки играя')
        self.setGeometry(100, 100, 900, 600)
        
        # Центральный виджет
        central_widget = GameWindow()
        self.setCentralWidget(central_widget)
        
        # Меню
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu('📁 Файл')
        
        new_game_action = QAction('🆕 Новая игра', self)
        new_game_action.triggered.connect(central_widget.back_to_menu)
        file_menu.addAction(new_game_action)
        
        stats_action = QAction('📊 Статистика', self)
        stats_action.triggered.connect(central_widget.show_stats)
        file_menu.addAction(stats_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('🚪 Выход', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        help_menu = menubar.addMenu('❓ Помощь')
        
        about_action = QAction('ℹ️ О программе', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def show_about(self):
        """Показать информацию о программе"""
        QMessageBox.about(self, "О программе",
                         "🎮 POLYGLOT\n\n"
                         "Версия: 1.0\n\n"
                         "Изучайте языки в игровой форме!\n"
                         "Доступные языки:\n"
                         "🇬🇧 Английский\n"
                         "🇮🇹 Итальянский\n"
                         "🇪🇸 Испанский\n"
                         "🇫🇷 Французский\n"
                         "🇵🇹 Португальский\n\n"
                         "Режимы игры:\n"
                         "🗣️ Устный\n"
                         "✍️ Письменный\n"
                         "📝 Тесты\n"
                         "🔤 Закончить предложение")

def main():
    app = QApplication(sys.argv)
    
    # Устанавливаем иконку приложения
    app.setWindowIcon(QIcon())
    
    # Стиль приложения
    app.setStyle('Fusion')
    
    game = PolyglotGame()
    game.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
