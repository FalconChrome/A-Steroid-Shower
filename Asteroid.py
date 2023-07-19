import pygame
import os
from random import randint
from itertools import product
from time import time

ARROWS = (pygame.K_UP, pygame.K_DOWN, pygame.K_RIGHT, pygame.K_LEFT)


class Quit(KeyboardInterrupt):
    """Исключение для завершения работы"""

    def __init__(self):
        pygame.quit()


class Restart(Exception):
    """Исключение для перезапуска"""


def load_image(name, colorkey=None):
    fullname = os.path.join('data', 'images', name)
    image = pygame.image.load(fullname)
    if colorkey is not None:
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
    else:
        image = image.convert_alpha()
    return image


def render_text(surface, text, text_coord, font, color=None):
    if color is None:
        color = pygame.color.Color('white')
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    text_rect.midtop = text_coord
    surface.blit(text_surface, text_rect)
    return text_rect.height


def bgmus_play(bgmus=None):
    if bgmus is None:
        bgmus = '0'
    bgmus_file = os.path.join('data', 'music', 'bgmus_' + bgmus + '.ogg')
    music.load(bgmus_file)
    if int(setter.get('music')):
        music.play(-1)


class SettingsFile:
    """
    Отдельный класс для безопасной работы с файлом настроек
    В файле хранятся настройки размера экрана и включённости музыки
    После завершения программы файл удаляется
    """
    NAME = '~temp'
    OPTIONS = {'size': 0, 'music': 1}

    def __init__(self):
        with open(self.NAME, 'w') as f:
            f.writelines(('size = 0x0\n', 'music = 1\n'))

    def __del__(self):
        os.remove(self.NAME)

    def set(self, option, value):
        with open(self.NAME) as f:
            lines = f.readlines()
        lines[self.OPTIONS[option]] = ' = '.join((option, value)) + '\n'
        with open(self.NAME, 'w') as set_f:
            set_f.writelines(lines)

    def get(self, option):
        with open(self.NAME) as f:
            lines = f.readlines()
        return lines[self.OPTIONS[option]].strip().split(' = ')[1]

    def get_all(self):
        with open(self.NAME) as f:
            return dict(line.strip().split(' = ') for line in f.readlines())


class StatisticsFile:
    """
    Отдельный класс для безопасной работы с файлом статистики
    При создании проверяет существование файла и соответствие формату (все int):
    deaths - количество смертей типов соответственно
    самоуничтожение, нехватка топлива, столконовение
    bestlevel - высший уровень
    highscores - 5 лучших резульатов
    """
    NAME = os.path.join('data', 'statistics.txt')
    OPTIONS = {'deaths': 0, 'bestlevel': 1, 'highscores': 2}

    def reset(self):
        with open(self.NAME, 'w') as f:
            f.writelines(('deaths = 0 0 0\n',
                          'bestlevel = 0\n',
                          'highscores = 0 0 0 0 0\n'))

    def __init__(self):
        try:
            stats = self.get_all()
            if not(len(stats['deaths']) == 3 and
                   len(stats['bestlevel']) == 1 and
                   len(stats['highscores']) == 5):
                self.reset()
        except (FileNotFoundError, ValueError, KeyError):
            self.reset()

    def add_stat(self, stat):
        death, level, vel, score = stat
        stats = self.get_all()

        stats['deaths'][death] += 1
        n = sum(stats['deaths'])

        if level > stats['bestlevel'][0]:
            stats['bestlevel'][0] = level

        stats['highscores'].append(score)
        stats['highscores'].sort(reverse=True)
        stats['highscores'].pop()  # Остаются только 5 лучших

        stats = tuple(' = '.join((key, ' '.join((str(x) for x in val)))) + '\n'
                      for (key, val) in stats.items())

        with open(self.NAME, 'w') as f:
            f.writelines(stats)

    def get(self, option):
        with open(self.NAME) as f:
            stats = f.readlines()
        return stats[self.OPTIONS[option]].strip().split(' = ')[1].split()

    def get_all(self, string=False):
        with open(self.NAME) as f:
            stats = f.readlines()
        stats = dict(line.strip().split(' = ') for line in stats)
        if not string:
            stats = {key: [int(x) for x in stats[key].split()] for key in stats}
        else:
            stats = {key: stats[key].split() for key in stats}
        return stats


class Camera:
    """
    Камера, привязанная к окну, которая обновляется на цель (цель оказывается в центре),
    применяется ко всем объектам (по вертикальному цилиндру на 50 px больше ширины экрана),
    и отдельно - к фону (фон саморегулируется независимо)
    """
    
    def __init__(self, window):
        self.window = window
        self.dx = 0
        self.dy = 0

    def apply(self, obj):
        obj.rect.x = (obj.rect.x + self.dx) % (self.window.width + 50)
        obj.rect.y += self.dy

    def apply_fon(self, fon):
        fon.rect.x += self.dx
        fon.rect.y += self.dy

    def update(self, target):
        self.dx = -(target.rect.x + target.rect.w // 2 -
                    self.window.width // 2)
        self.dy = -(target.rect.y + target.rect.h // 2 -
                    2 * self.window.height // 3)


class Fon:
    """
    Фон создаётся свой для каждого окна и привязан к нему
    Картинка замощает весь экран и отступ не больше размера картинки вокруг
    для соединения при движении
    Обновляется и сам блитируется на экран
    """
    
    def __init__(self, window):
        self.window = window
        self.image = load_image('sky.jpg')
        self.rect = self.image.get_rect()

    def update(self):
        self.rect.x = self.rect.x % self.rect.w
        self.rect.y = self.rect.y % self.rect.h

    def blit(self):
        for shift in product(range(-self.rect.w, self.window.width,
                                   self.rect.w),
                             range(-self.rect.h, self.window.height,
                                   self.rect.h)):
            self.window.screen.blit(self.image, self.rect.move(*shift))


class ScrollBar:
    """
    Ползунок в настройках. Может двигаться мышкой или стрелочками.
    Специфично сочетается с TableSet (для регулировки управления стрелочками)
    Обрабатывает события от мышки и рендерится вместе со значением
    """

    def __init__(self, pos, font, min_val=0, max_val=100, text=None):
        """
        Может иметь объединяющее название,
        требует шрифт, центр таблицы;
        может принимать граничные значения, по умолчанию от 0 до 100
        """
        self.scroll_image = load_image('scroll.png')
        self.scrollbar_image = load_image('scrollbar.png')
        self.bright_scroll_image = self.scroll_image.copy()
        self.bright_scroll_image.fill(pygame.color.Color('orange'))

        self.text = None
        if text is not None:
            # если объекту передана подпись, то она создается
            # в виде текста над ползунком
            self.text = (text, pos.copy())
            pos[1] += 20 + font.render(text, True, (0, 0, 0)).get_rect().h

        self.rect = self.scrollbar_image.get_rect()
        self.rect.midtop = pos
        self.val_pos = (self.rect.right + 30, pos[1])

        self.sc_rect = self.scroll_image.get_rect()
        self.sc_rect.move_ip(self.rect.topleft)

        self.min_val = min_val
        self.max_val = max_val
        self.font = font
        self.focused = None
        self.rows = -1
        self.val = 0
        self.step = ((self.rect.w - self.sc_rect.w) /
                     (self.max_val - self.min_val))

    def render(self, screen):
        screen.blit(self.scrollbar_image, self.rect.topleft)
        if self.focused is not None:
            screen.blit(self.bright_scroll_image, self.sc_rect.topleft)
        else:
            screen.blit(self.scroll_image, self.sc_rect.topleft)
        render_text(screen, str(round(self.val)), self.val_pos, self.font)
        if self.text:
            render_text(screen, *self.text, self.font,
                        pygame.color.Color('yellow'))

    def set_val(self, val):
        if val < self.min_val:
            val = self.min_val
        elif val > self.max_val:
            val = self.max_val
        self.val = val

        if val == self.max_val:
            self.sc_rect.x = self.rect.right - self.sc_rect.w
        elif val == self.min_val:
            self.sc_rect.x = self.rect.x
        else:
            self.sc_rect.x = self.rect.x + val * self.step

    def get_val(self):
        return self.val

    def events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.mouse_click(event.pos):
                self.focused = 0

        elif event.type == pygame.MOUSEMOTION:
            if self.focused is not None and event.buttons[0]:
                self.move(event.rel[0] / 2)
                return self.val

    def move_focuse(self, d):
        self.move(-d)
        return 0

    def move(self, d):
        self.sc_rect.x += d * 2
        self.set_val((self.sc_rect.x - self.rect.x) / self.step)

    def mouse_click(self, pos):
        """
        Метод проверяет, на какую часть ползунка кликнули.
        Если на левую, то ползунок смещается
        на единицу влево, если на правую, то на единицу вправо,
        если на середину, то ползунок
        начинает перетаскиваться
        """
        rect_left = pygame.Rect((self.sc_rect.x, self.sc_rect.y),
                                (self.sc_rect.w * 0.3, self.sc_rect.h))
        rect_right = pygame.Rect((self.sc_rect.x + self.sc_rect.w * 0.7,
                                  self.sc_rect.y),
                                 (self.sc_rect.w * 0.3, self.sc_rect.h))
        rect_center = pygame.Rect((self.sc_rect.x + self.sc_rect.w * 0.3,
                                   self.sc_rect.y),
                                  (self.sc_rect.w * 0.4, self.sc_rect.h))
        if rect_center.collidepoint(pos):
            return True
        if rect_left.collidepoint(pos):
            self.move(-1)
        elif rect_right.collidepoint(pos):
            self.move(1)
        return False

    def __len__(self):
        """Функция len для совместимости с таблицей кнопок в сете"""
        return 1

    def choose(self, i):
        if self.focused is not None:
            self.focused = None
            return True
        if i is not None:
            self.set_val(i)
            return i

    def get_button(self, pos):
        if self.sc_rect.collidepoint(pos):
            return 0
        else:
            return None

    def update(self, mouse):
        pass


class ButtonTable:
    """
    Таблица кнопок, может объединяться Сетом Кнопок или работать отдельно;
    имеет индиктор выбранного элемента и сфокусированного элемента,
    рендерит кнопки цветом в зависимости от этого.
    Поддерживает обращение как к списку;
    обрабатывает сигналы мышки и клавиатуры.
    Единичная кнопка реализуется как одноэлементная таблица.
    """
    WHITE = pygame.color.Color('white')
    ORANGE = pygame.color.Color('orange')
    YELLOW = pygame.color.Color('yellow')

    def __init__(self, text, pos, font, y_shift=20, x_shift=200,
                 title=None, rows=None, choice=None):
        """
        Может иметь объединяющее название,
        требует шрифт, центр таблицы и названия кнопок;
        может принимать количество строк в столбце
        """
        if rows is None:
            rows = len(text)
        self.rows = rows
        if title is not None:
            title_rect = font.render(title, True, self.WHITE).get_rect()
            title_rect.midtop = (pos[0] + ((len(text) - 1) // rows) *
                                 x_shift // 2, pos[1])
            self.title = (title, title_rect.midtop)
            pos[1] += title_rect.h + y_shift
        else:
            self.title = ('', (0, 0))
        self.buttons = []
        self.focused = None
        self.chosen = choice
        self.font = font
        pos0 = pos.copy()

        for (i, line) in enumerate(text):
            if i % rows == 0 and i != 0:
                pos[0] += x_shift
                pos[1] = pos0[1]
            rect = font.render(line, True, self.WHITE).get_rect()
            rect.midtop = pos
            self.buttons.append((line, rect))
            pos[1] += rect.h + y_shift

    def __getitem__(self, i):
        return self.buttons[i]

    def __len__(self):
        return len(self.buttons)

    def move_focuse(self, d):
        self.focused = ((self.focused + d) % len(self.buttons)
                        if self.focused is not None else 0)
        return self.focused

    def choose(self, i):
        self.chosen = i
        return i

    def update(self, mouse_pos):
        button_n = self.get_button(mouse_pos)
        if button_n is not None:
            self.focused = button_n

    def render(self, sheet):
        render_text(sheet, *self.title, self.font, self.YELLOW)
        for button in self.buttons:
            render_text(sheet, button[0], button[1].midtop,
                        self.font, self.WHITE)
        if self.chosen is not None:
            chosen = self.buttons[self.chosen]
            render_text(sheet, chosen[0], chosen[1].midtop,
                        self.font, self.YELLOW)
        if self.focused is not None:
            focused = self.buttons[self.focused]
            render_text(sheet, focused[0], focused[1].midtop,
                        self.font, self.ORANGE)

    def get_button(self, pos):
        for (i, b) in enumerate(self.buttons):
            if b[1].collidepoint(pos):
                return i
        else:
            return None


class TableSet:
    """
    Сет для синхронизации всех интерактивных элементов.
    Как и таблица кнопок, имеет индикатор сфокусированного элемента,
    но не позволяет иметь своим подсистемам больше одного сфокусированного.
    Поддерживает индексацию;
    обрабатывает сигналы мышки и клавиатуры.
    """
    
    def __init__(self, *tables):
        self.tables = tables
        self.sizes = tuple(len(table) for table in self.tables)
        self.size = len(tables)
        self.focused = (0, 0)
        self.moving = 0

    def set_focuse(self, i, b):
        self.tables[self.focused[0]].focused = None
        self.focused = (i, b)
        self.tables[i].focused = b

    def move_focuse(self, d):
        i, b = self.focused
        if d == 0:  # Вверх K_UP
            if b == 0:
                i = (i - 1) % self.size
                b = self.sizes[i] - 1
            else:
                b -= 1
        elif d == 1:  # Вниз K_DOWN
            if self.sizes[i] == b + 1:
                i = (i + 1) % self.size
                b = 0
            else:
                b += 1
        elif d == 2:  # Вправо K_RIGHT
            rows = self.tables[i].rows
            new = b + rows - self.sizes[i]
            if new >= 0:
                i = (i + 1) % self.size
                b = min(new, self.sizes[i] - 1)
            else:
                self.focused = (i, self.tables[i].move_focuse(rows))
                return rows
        elif d == 3:  # Влево K_LEFT
            rows = self.tables[i].rows
            new = b - rows
            if new < 0:
                i = (i - 1) % self.size
                b = max(new + self.sizes[i], 0)
            else:
                self.focused = (i, self.tables[i].move_focuse(-rows))
                return -rows
        else:
            return None
        self.set_focuse(i, b)

    def __getitem__(self, i):
        return self.tables[i]

    def choose(self, i, b=None):
        return self.tables[i].choose(b)

    def update(self, mouse_pos, arrow_pressed):
        for (key, val) in enumerate(arrow_pressed):
            if val:
                if self.moving < 8:
                    if self.moving == 0:
                        self.move_focuse(key)
                    self.moving += 1
                else:
                    self.move_focuse(key)
                break
        else:
            self.moving = 0
        index = self.get_button(mouse_pos)
        if index is not None:
            self.set_focuse(*index)

    def render(self, sheet):
        for table in self.tables:
            table.render(sheet)

    def get_button(self, pos):
        for (i, table) in enumerate(self.tables):
            b = table.get_button(pos)
            if b is not None:
                return i, b
        else:
            return None


class Settings:    
    """
    Окно настроек, создаёт сет с таблицами размера экрана и музыки,
    ползунком музыки и кнопкой назад.
    Создаётся независимо от других окон, перехватывая экран.
    """
    FONT_NAME = os.path.join('data', 'mr_AfronikG.ttf')
    SIZE_BUTTONS_TEXT = ("Полный экран", "1920x1080", "1600x1200",
                         "1440x1080", "1280x720", "960x540")
    MUS_BUTTONS_TEXT = ("Выкл", "Вкл")
    SIZE = width, height = 720, 480

    def __init__(self):
        self.screen = display.set_mode(self.SIZE)
        display.set_caption("Настройки")
        self.fon = Fon(self)
        self.fps = 25
        

        med_font = pygame.font.Font(self.FONT_NAME, 35)
        back_button = ButtonTable(("<= Назад",), [100, 30], med_font)
        h_inc = back_button[0][1].h
        start_h = 60 + h_inc + 20
        size_buttons = ButtonTable(self.SIZE_BUTTONS_TEXT,
                                   [self.width // 6, start_h], med_font,
                                   title="Размер экрана", rows=4)
        mus_scrollbar = ScrollBar([self.width * 3 // 4, start_h],
                                  med_font, text="Музыка")
        mus_buttons = ButtonTable(self.MUS_BUTTONS_TEXT,
                                  [mus_scrollbar.rect.x +
                                   mus_scrollbar.rect.w // 4,
                                   40 + mus_scrollbar.rect.bottom],
                                  med_font, x_shift=100, rows=1)
        self.buttons = TableSet(back_button, size_buttons,
                                mus_scrollbar, mus_buttons)
        self.size_choose()
        self.music_choose()
        self.run()

    def music_choose(self):
        self.buttons.choose(2, music.get_volume() * 100)
        self.buttons.choose(3, int(setter.get('music')))

    def size_choose(self):
        size = setter.get('size')
        if size == '0x0':
            self.buttons.choose(1, 0)
        else:
            try:
                self.buttons.choose(1, self.SIZE_BUTTONS_TEXT.index(size))
            except ValueError:
                setter.set('size', '0x0')
                self.buttons.choose(1, 0)

    def render(self):
        self.fon.blit()
        self.buttons.render(self.screen)
        display.flip()

    def events(self, event):
        if event.type == pygame.QUIT:
            return True
        elif event.type == pygame.MOUSEBUTTONUP:
            if self.buttons.choose(2) is not True:
                return self.mouse_click(event.pos)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return True
            elif event.key == pygame.K_RETURN:
                return self.act(self.buttons.focused)
        else:
            res = self.buttons[2].events(event)
            if res is not None:
                self.bgmus_vol(res)

    def run(self):
        running = True
        arrow_pressed = [False, False, False, False]  # Up, Down, Right, Left
        while running:
            for event in pygame.event.get():
                if self.events(event):
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key in ARROWS:
                        arrow_pressed[ARROWS.index(event.key)] = True  
                if event.type == pygame.KEYUP:
                    if event.key in ARROWS:
                        arrow_pressed[ARROWS.index(event.key)] = False

            self.buttons.update(mouse.get_pos(), arrow_pressed)
            if self.buttons.focused[0] == 2 and any(arrow_pressed):
                self.bgmus_vol(self.buttons[2].get_val())
            self.render()
            clock.tick(self.fps)
        display.quit()

    def act(self, button):
        """Возвращает bool -> надо ли завершать"""
        self.buttons.choose(*button)
        if button[0] == 0:
            return True
        elif button[0] == 1:
            button = button[1]
            if button != 0:
                setter.set('size', str(self.get_resolution(button)))
            else:
                setter.set('size', '0x0')
        elif button[0] == 3:
            if button[1] == 0:
                music.pause()
                setter.set('music', '0')
            else:
                music.rewind()
                music.unpause()
                setter.set('music', '1')
        return False

    def get_resolution(self, button):
        return self.buttons[1][button][0]

    def bgmus_vol(self, vol):
        music.set_volume(vol / 100)

    def mouse_click(self, pos):
        res = self.buttons.get_button(pos)
        if res is None:
            return False
        return self.act(res)


class Statistics:    
    """
    Окно статистики, выводит всю статистику и позволяет её сбросить,
    создаёт кнопки сброс и назад.
    Перед сбросом уточняет намерение (предосторожность от случайного сброса).
    Создаётся независимо от других окон, перехватывая экран.
    """
    FONT_NAME = os.path.join('data', 'mr_AfronikG.ttf')
    SIZE = width, height = 960, 540

    def __init__(self):
        self.screen = display.set_mode(self.SIZE)
        display.set_caption("Статистика")
        self.fon = Fon(self)
        self.fps = 25
        

        self.med_font = pygame.font.Font(self.FONT_NAME, 35)
        back_button = ButtonTable(("<= Назад",), [100, 30], self.med_font)
        reset_button = ButtonTable(("Сбросить статистику",),
                                   [self.width // 2, self.height * 5 // 6],
                                   self.med_font)
        self.buttons = TableSet(back_button, reset_button)
        self.stats = []
        self.get_stats()
        self.run()

    def get_stats(self):
        pos = [self.width // 2, self.height // 6]
        stats = StatisticsFile().get_all(string=True)
        text = ((f"Смертей от столкновения: {stats['deaths'][1]}",
                 f"    от нехватки энергии: {stats['deaths'][2]}",
                 f"        самоуничтожений: {stats['deaths'][0]}",
                 f"Высший достигнутый уровень: {stats['bestlevel'][0]}"),
                (f"Лучшие результаты:",
                 *(score.rjust(6, '0') for score in stats['highscores'])))
        pos0 = pos.copy()
        pos[0] -= self.width // 5
        for line in text[0]:
            self.stats.append((line, pos.copy()))
            pos[1] += 40 + self.med_font.render(line, True, (0, 0, 0)).get_rect().h
        pos = pos0
        pos[0] += self.width // 4
        for line in text[1]:
            self.stats.append((line, pos.copy()))
            pos[1] += 20 + self.med_font.render(line, True, (0, 0, 0)).get_rect().h

    def reset_stats(self):
        ask_surf = self.screen.subsurface((self.width // 6,
                                           self.height // 6,
                                           self.width * 4 // 6,
                                           self.height * 4 // 6))
        start = (-self.width // 6, -self.height // 6)
        question = []
        pos = [self.width // 6, self.height // 6]
        for line in ("Вы точно хотите     ",
                     "сбросить статистику?"):
            question.append((line, pos.copy()))
            pos[1] += render_text(ask_surf, line, pos, self.med_font) + 30
        ask_buttons = ButtonTable(("Да", "Нет"), pos,
                                  self.med_font, x_shift=250, rows=1)
        answer = False  # Подтверждение сброса
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONUP:
                    pos = event.pos
                    pos = tuple(pos[i] + start[i] for i in range(2))
                    button = ask_buttons.get_button(pos)
                    if button is not None:
                        answer = not bool(button)  # Порядок кнопок: Да, Нет
                        running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_RETURN:
                        answer = not bool(ask_buttons.choose(ask_buttons.focused))
                        running = False
                    elif event.key == pygame.K_RIGHT:
                        ask_buttons.move_focuse(1)
                    elif event.key == pygame.K_LEFT:
                        ask_buttons.move_focuse(-1)

            pos = mouse.get_pos()
            pos = tuple(pos[i] + start[i] for i in range(2))
            ask_buttons.update(pos)
            ask_surf.fill(pygame.color.Color('blueviolet'))
            for line in question:
                render_text(ask_surf, *line, self.med_font)
            ask_buttons.render(ask_surf)
            display.flip()
            clock.tick(self.fps)

        if answer:
            StatisticsFile().reset()
            self.get_stats()

    def render(self):
        self.fon.blit()
        self.buttons.render(self.screen)
        for line in self.stats:
            render_text(self.screen, *line, self.med_font)
        display.flip()

    def events(self, event):
        if event.type == pygame.QUIT:
            return True
        elif event.type == pygame.MOUSEBUTTONUP:
            return self.mouse_click(event.pos)

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return True
            elif event.key == pygame.K_RETURN:
                return self.act(self.buttons.focused)

    def run(self):
        running = True
        arrow_pressed = [False, False, False, False]  # Up, Down, Right, Left
        while running:
            for event in pygame.event.get():
                if self.events(event):
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key in ARROWS:
                        arrow_pressed[ARROWS.index(event.key)] = True  
                if event.type == pygame.KEYUP:
                    if event.key in ARROWS:
                        arrow_pressed[ARROWS.index(event.key)] = False
                        
            self.buttons.update(mouse.get_pos(), arrow_pressed)
            self.render()
            clock.tick(self.fps)
        display.quit()

    def act(self, button):
        """Возвращает bool -> надо ли завершать"""
        self.buttons.choose(*button)
        if button[0] == 0:
            return True
        elif button[0] == 1:
            self.reset_stats()
        return False

    def mouse_click(self, pos):
        res = self.buttons.get_button(pos)
        if res is None:
            return False
        return self.act(res)


class StartScreen:  
    """
    Главный экран, создаёт 4 кнопки для перемещения между остальными экранами.
    Создаётся независимо от других окон, перехватывая экран.
    """
    FONT_NAME = os.path.join('data', 'mr_AfronikG.ttf')
    BUTTONS_TEXT = ["Старт", "Настройки", "Статистика", "Выход"]
    SIZE = width, height = 640, 480

    def __init__(self):
        bgmus_play('menu')
        self.screen = display.set_mode(self.SIZE)
        display.set_caption("A Steroid Shower")
        self.fon = Fon(self)
        self.fps = 25
        

        self.title = ("A Steroid Shower", (self.width // 2, 30),
                      pygame.font.Font(self.FONT_NAME, 60),
                      pygame.color.Color('yellow'))
        h_inc = render_text(self.screen, *self.title)

        self.buttons = ButtonTable(self.BUTTONS_TEXT,
                                   [self.width // 2, 30 + h_inc + 40],
                                   pygame.font.Font(self.FONT_NAME, 55), 30)
        self.run()

    def render(self):
        self.fon.blit()
        render_text(self.screen, *self.title)
        self.buttons.render(self.screen)
        display.flip()

    def statistics(self):
        Statistics()
        self.screen = display.set_mode(self.SIZE)

    def settings(self):
        Settings()
        self.screen = display.set_mode(self.SIZE)

    def events(self, event):
        if event.type == pygame.QUIT:
            raise Quit
        if event.type == pygame.MOUSEBUTTONUP:
            if self.mouse_click(event.pos):
                return True
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if self.act(self.buttons.focused):
                    return True
            elif event.key == pygame.K_UP:
                self.buttons.move_focuse(-1)
            elif event.key == pygame.K_DOWN:
                self.buttons.move_focuse(1)

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if self.events(event):
                    running = False

            if mouse.get_focused():
                self.buttons.update(mouse.get_pos())

            self.render()
            clock.tick(self.fps)
        display.quit()

    def act(self, button):
        """Возвращает bool -> надо ли завершать"""
        if button == 0:
            return True
        if button == 1:
            self.settings()
            return False
        if button == 2:
            self.statistics()
            return False
        if button == 3:
            raise Quit

    def mouse_click(self, pos):
        res = self.buttons.get_button(pos)
        if res is None:
            return False
        return self.act(res)


class Rocket(pygame.sprite.Sprite):  
    """
    Ракета, управляемая пользователем стрелочками.
    Движение равномерное, моментальная смена вектора скорости,
    независимое движение по осям.
    При движении влево или вправо спрайт поворачивается соответственно.
    Теряет 10 энергии в секунду, при обнулении уничтожается, изначально 100 единиц.
    При сборе осколка пополняет энергию, при столкновении с астероидом
    уничтожается; оба пересечения задействуют уменьшенный вдвое спрайт
    (более точно отображает его форму, чем полный размер)
    """

    def __init__(self, game, *groups):
        self.game = game
        super().__init__(*groups)
        self.IMAGE = self.game.spr_images["rocket"]
        self.image = self.IMAGE  # картинка будет поворачиваться

        self.rect = self.image.get_rect()
        self.rect.x = self.game.width // 2
        self.rect.y = self.game.height // 2
        self.v = 500 / self.game.fps
        self.fuel_loss = 10 / self.game.fps

        self.fuel = 100
        self.destroyed = 0

    def collect(self, grab):
        if grab.profit[0] == 'F':
            self.fuel += float(grab.profit[1:])
            grab.collect()

    def update(self, *args):
        self.rotate(0)
        if not args:
            return None
        if type(args[0]) == list:
            self.drive(args[0])
        self.fuel = max(0, self.fuel - self.fuel_loss)

        # Уменьшение для лучшего соответствия размерам спрайта
        self.rect.inflate_ip(-self.rect.w // 2, -self.rect.h // 2)
        if pygame.sprite.spritecollideany(self, self.game.crash_sprites):
            self.destroyed = 1
        for grab in pygame.sprite.spritecollide(self,
                                                self.game.picked_sprites,
                                                False):
            self.collect(grab)
        self.rect.inflate_ip(self.rect.w, self.rect.h)

        if self.fuel <= 0:
            self.destroyed = 2

    def drive(self, arrows):
        if arrows[0]:
            self.rect.y -= self.v
        elif arrows[1]:
            self.rect.y += self.v
        if arrows[2]:
            self.rect.x += self.v
            self.rotate(-1)
        elif arrows[3]:
            self.rect.x -= self.v
            self.rotate(1)

    def rotate(self, r):
        if r != 0:
            self.image = pygame.transform.rotate(self.image, 45 * r)
        else:
            self.image = self.IMAGE


class StatusBar:
    """
    Выводит информацию о количестве энергии у ракеты и
    уровне, соответствующему количеству собранных осколков энергии.
    """
    POINTS = ['Уровень', 'Энергия']

    def __init__(self, game):
        self.game = game
        self.values = ['1', '100']
        self.x = 20
        self.y = 30
        shift = self.game.SMALL_FONT.render('Уровень: 1', True,
                                            self.game.WHITE).get_rect()
        self.x += shift.w // 2
        self.shift = shift.h

    def update(self, *args):
        self.values[0] = str(round(self.game.level))
        self.values[1] = str(round(self.game.rocket.fuel))

    def render(self):
        shift = 0
        for line in zip(self.POINTS, self.values):
            render_text(self.game.screen, ': '.join(line),
                        (self.x, self.y + shift),
                        self.game.SMALL_FONT, self.game.WHITE)
            shift += self.shift


class AnimatedSprite(pygame.sprite.Sprite):
    """
    Класс для реализации анимированных спрайтов;
    использует картинку, в которой все фреймы собраны в "таблицу"
    """
    
    def __init__(self, sheet, columns, rows, x, y, period, *groups):
        super().__init__(*groups)
        self.frames = []
        self.cut_sheet(sheet, columns, rows)
        self.cur_frame = 0
        self.image = self.frames[self.cur_frame]
        self.rect = self.rect.move(x, y)
        self.t0 = period
        self.i = 0

    def cut_sheet(self, sheet, columns, rows):
        """Разбивает исходную "табличную" картинку на фреймы и сохраняет в списке"""
        self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                sheet.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                frame_location = (self.rect.w * i, self.rect.h * j)
                self.frames.append(sheet.subsurface(pygame.Rect(
                    frame_location, self.rect.size)))

    def update(self):
        if self.i >= self.t0 - 1:
            self.i += 1 - self.t0
            self.cur_frame = (self.cur_frame + 1) % len(self.frames)
            self.image = self.frames[self.cur_frame]
        else:
            self.i += 1


class EnergyShatters(AnimatedSprite):
    """
    Осколки энергии, имеют ценность 40 единиц
    По сути реализованы в виде одного спрайта,
    перемещающегося при его сборе (пересечение с ракетой) в случайное место
    на следующем геометрическом уровне (задаётся в классе игры),
    после чего у игры обновляется уровень
    """

    def __init__(self, game, *groups):
        self.game = game
        super().__init__(self.game.spr_images["energy"], 6, 4,
                         randint(0, self.game.width + 50),
                         randint(-self.game.LEVEL_H + 50, 0),
                         self.game.fps / 24, *groups)
        self.profit = "F40"
        self.y0 = self.rect.y + self.game.LEVEL_H

    def collect(self):
        self.game.levelup()
        self.rect.x = randint(0, self.game.width + 50)
        level = self.rect.y - self.y0 - self.game.LEVEL_H
        self.rect.y = randint(level + 50, level + self.game.LEVEL_H - 50)
        self.y0 = self.rect.y - level


class Asteroids:
    """
    Класс управляет всеми астероидами. У всех одинаковая скорость.
    Генерация новых происходит не быстрее периода и
    ограничивается сверху концентрацией астероидов.
    Все три параметра усложняются с каждым уровнем.
    """

    def __init__(self, game, *groups):
        self.game = game
        self.groups = groups
        self.image = self.game.spr_images["asteroid"]
        self.IMAGE_H = self.image.get_height()
        self.asteroids = []
        self.v = 80 / self.game.fps
        self.n = self.game.width // 250
        self.t0 = self.game.fps / 2
        self.i = 0

    def gen_particle(self):
        new_ast = pygame.sprite.Sprite(*self.groups)
        new_ast.image = self.image
        new_ast.rect = new_ast.image.get_rect()
        new_ast.rect.move_ip(randint(0, self.game.width),
                             -self.IMAGE_H - randint(0, 200))
        self.asteroids.append(new_ast)

    def update(self):
        self.i += 1
        for ast in self.asteroids:
            ast.rect.y += self.v
            if ast.rect.y > self.game.height:
                ast.kill()
                self.asteroids.remove(ast)
        if self.i >= self.t0 and self.n > len(self.asteroids):
            self.i = 0
            self.gen_particle()

    def calculate_velocity_rate(self, level):
        x = level
        a = 0.3
        b = 20
        if level < 100:
            return x ** 0.7 + 0.2 * 2 ** (a * ((x / 10) + b)) - 0.21 * 2 ** (a * ((x // 10) + b))
        else:
            return (x - 50) ** 0.9

    def level_up(self, level):
        self.n = int(level ** 0.6 * self.game.width / 250)
        self.t0 = self.game.fps / (2 * level ** 0.7)
        self.v = self.calculate_velocity_rate(level) * 80 / self.game.fps


class Game:  
    """
    Класс самой игры, совмещающий игровой экран и поле для взаимодействия
    физических объектов. Реализует взаимодействие элементов друг с другом и
    с пользоваетелем. Контролирует музыку и размер экрана,
    сверяясь с файлом  настроек. Все спрайты объединяюся в группы спрайтов
    по значению.
    Объекты игры привязаны к объекту игры, обращаются к нему сами напрямую.
    Во время игры перехватывает Restart и выключает экран,
    но в главной функции вызывается снова до выброса Quit.
    Реализует паузу в виде отдельного цикла,
    также есть смена полноэкранного режима и самоуничтожение.
    После уничтожения подводит итог: тип смерти, уровень,
    скорость продвижения в пикселях в секунду и счёт
    (зависит от двух последних параметров и накопленной энергии),
    ждёт реакции пользователя и выбрасывает Restart.
    При движении камера перемещает всё в обратную сторону (относительное движение).
    """
    FONT_NAME = os.path.join('data', 'mr_AfronikG.ttf')
    WHITE = pygame.color.Color('white')
    LEVEL_H = 1600
    ARROWS = (pygame.K_UP, pygame.K_DOWN, pygame.K_RIGHT, pygame.K_LEFT)

    def set_params(self):
        size = tuple(int(x) for x in setter.get('size').split('x'))
        self.screen = display.set_mode(size)
        if size == (0, 0):
            self.sure_fullscreen()
        self.size = (self.width, self.height) = self.screen.get_size()

    def sure_fullscreen(self):
        full = display.toggle_fullscreen()
        if not full:
            display.toggle_fullscreen()

    def __init__(self):
        self.set_params()
        display.set_caption("A Steroid Shower")

        self.BIG_FONT = pygame.font.Font(self.FONT_NAME, 45)
        self.SMALL_FONT = pygame.font.Font(self.FONT_NAME, 32)

        self.fps = 30
        self.spr_images = {"energy": load_image("energy.png", -1),
                           "rocket": load_image("rocket.png"),
                           "asteroid": load_image("asteroid.png")}

        self.fon = Fon(self)
        self.fon.blit()

        self.all_sprites = pygame.sprite.Group()
        self.picked_sprites = pygame.sprite.Group()
        self.crash_sprites = pygame.sprite.Group()
        self.player_group = pygame.sprite.Group()

        self.level = 1
        self.rocket = Rocket(self, self.all_sprites, self.player_group)
        self.energy_shatters = EnergyShatters(self, self.all_sprites,
                                              self.picked_sprites)
        self.asteroids = Asteroids(self, self.all_sprites,
                                   self.crash_sprites)
        self.stat_bar = StatusBar(self)
        self.camera = Camera(self)
        try:
            self.run()
        except Restart:
            display.quit()

    def events(self, event):
        if event.type == pygame.QUIT:
            raise Quit
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                self.pause()
            if event.key == pygame.K_f:
                display.toggle_fullscreen()
            elif event.key == pygame.K_r:
                self.destroy(0)
            # Случай непредвиденного самоуничтожения клавишей R
        elif event.type == pygame.MOUSEBUTTONUP:
            if sum(mouse.get_pressed()) >= 1:
                # или 2-мя любыми кнопками мыши
                self.destroy(0)
            else:
                display.toggle_fullscreen()


    def blit(self):
        self.fon.blit()
        self.all_sprites.draw(self.screen)
        self.player_group.draw(self.screen)
        self.stat_bar.render()

    def run(self):
        running = True
        bgmus_play()
        self.START_TIME = time() % (60 * 60 * 24 * 30)
        arrow_pressed = [False, False, False, False]  # Up, Down, Right, Left
        while running:
            for event in pygame.event.get():
                self.events(event)
                if event.type == pygame.KEYDOWN:
                    if event.key in ARROWS:
                        arrow_pressed[ARROWS.index(event.key)] = True  
                if event.type == pygame.KEYUP:
                    if event.key in ARROWS:
                        arrow_pressed[ARROWS.index(event.key)] = False
            
            
            self.all_sprites.update()
            self.player_group.update(arrow_pressed)
            self.asteroids.update()
            if self.rocket.destroyed:
                self.destroy(self.rocket.destroyed)

            self.camera.update(self.rocket)
            self.camera.apply_fon(self.fon)
            for sprite in self.all_sprites:
                self.camera.apply(sprite)

            self.stat_bar.update()
            self.fon.update()

            self.blit()
            display.flip()
            clock.tick(self.fps)

    def pause(self):
        start_time = time() % (60 * 60 * 24 * 30)
        self.blit()
        font = pygame.font.Font(self.FONT_NAME, 400)
        render_text(self.screen, 'Пауза',
                    (self.width // 2,
                     (self.height -
                      font.render('Пауза', True, (0, 0, 0)).get_rect().h) // 2),
                    font)
        display.flip()
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise Quit
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_f, pygame.K_LSUPER,
                                     pygame.K_RSUPER):
                        display.toggle_fullscreen()
                    elif event.key in (pygame.K_p, pygame.K_RETURN,
                                     pygame.K_ESCAPE):
                        waiting = False
                elif event.type == pygame.MOUSEBUTTONUP:
                    if sum(mouse.get_pressed()) >= 1:
                        waiting = False
                    else:
                        display.toggle_fullscreen()
            clock.tick(self.fps)
        end_time = time() % (60 * 60 * 24 * 30)
        self.START_TIME -= end_time - start_time

    def levelup(self):
        self.level += 1
        self.asteroids.level_up(self.level)

    def score(self, play_time, death):
        score = [death, self.level,
                 int(self.fps * self.rocket.v * (self.level - 1) / play_time)]
        score.append(round(self.level ** 2 * score[2] / 100
                           + 10 * self.rocket.fuel * (self.level - 1) ** 0.5))
        return score

    def destroy(self, death):
        self.rocket.kill()
        self.end_game(self.rocket.rect.center, death)
        raise Restart

    def end_game(self, end_coord, death):
        play_time = time() % (60 * 60 * 24 * 30) - self.START_TIME
        music.stop()
        score = self.score(play_time, death)
        StatisticsFile().add_stat(score)
        died = ["самоуничтожились", "погибли от столкновения",
                "погибли от нехватки энергии"][score[0]]
        end_text = ["КОНЕЦ ИГРЫ",
                    f"Вы {died}",
                    f"Ваш прогресс: {score[1]}",
                    f"Средняя скорость продвижения: {score[2]}",
                    f"Счёт: {str(score[3])}",
                    " ",
                    "Нажмите дважды любую клавишу для выхода"]
        self.fon.blit()
        text_coord = list(end_coord)
        text_coord[0] += 10
        text_coord[1] += 50 - self.height // 2
        for line in end_text:
            text_coord[1] += 10 + render_text(self.screen, line,
                                              text_coord, self.BIG_FONT)
        waiting = 2
        while waiting > 0:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise Quit
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_f, pygame.K_LSUPER,
                                     pygame.K_RSUPER):
                        display.toggle_fullscreen()
                    else:
                        waiting -= 1
                elif event.type == pygame.MOUSEBUTTONUP:
                    if sum(mouse.get_pressed()) >= 1:
                        waiting = 0
                    else:
                        display.toggle_fullscreen()
            display.flip()
            clock.tick(self.fps)


if __name__ == "__main__":
    try:
        pygame.init()
        setter = SettingsFile()
        music = pygame.mixer.music
        music.set_volume(0.72)
        clock = pygame.time.Clock()
        display = pygame.display
        mouse = pygame.mouse
        while True:
            StartScreen()
            Game()
    except Quit:
        pass
    finally:
        setter.__del__()
        Quit()
