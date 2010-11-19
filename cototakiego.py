#!/usr/bin/python
# -*- coding: utf8 -*-

"""
    cototakiego.py - a clone of OpenAlchemist in Pygtk
    Copyright (C) 2007, 2010  rhn

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""


import gtk
import pygtk
pygtk.require('2.0')
import random
from sys import stdout
from pango import Layout
import traceback
import time


def safe_call(function, *args, **kwargs):
    if function is None:
        return
    try:
        return function(*args, **kwargs)
    except Exception, e:
        traceback.print_exc(e)
        
        
def running_event(method): # rename to user_action
    def event_method(self, *args, **kwargs):
        if not self.over:
            return method(self, *args, **kwargs)
        return False
    return event_method


def engine_interaction(method):
    def interaction_wrapper(self, *args, **kwargs):
        try:
            redraw = method(self, *args, **kwargs)
        except Exception, e:
            print e
            return False

        if redraw:
            self.redraw()
        return True
    return interaction_wrapper


def get_ball_styles(colormap):
    styles = {}
    for name in Game.Data.brands:
        styles[name] = colormap.alloc_color(name)
    return styles
 

class Game:
    class UI:
        class BallDisplay(gtk.DrawingArea):
            def __init__(self):
                gtk.DrawingArea.__init__(self)
                self.connect('realize', self.on_realize)
                self.connect('expose-event', self.on_expose)
                self.gc = None
                self.styles = {}

            def on_realize(self, widget, data=None):
                self.gc = self.window.new_gc()
                colormap = self.get_colormap()
                self.styles = get_ball_styles(colormap)
   
            def on_expose(self, widget, data=None):
                self.draw()
            
            def draw_ball(self, ball, size, x, y):
                self.gc.set_foreground(self.styles[ball])
                self.window.draw_arc(self.gc, True, x, y, \
                                                       size, size, 0, 360 * 64)

        class Preview(BallDisplay):
            BALL_SPACING = 0.25
            def __init__(self, pair=None):
                Game.UI.BallDisplay.__init__(self)
                self.pair = pair

            def draw(self):
                if self.pair is None:
                    return
                rect = self.get_allocation()
                ball_size = min(int(rect.width / (2 + self.BALL_SPACING)), rect.height)

                for i, ball in enumerate(self.pair):
                    x = int(i * ball_size * (1 + self.BALL_SPACING))
                    y = 0
                    self.draw_ball(ball, ball_size, x, y)
                
                
        class TypesView(BallDisplay):
            def __init__(self, level=0):
                Game.UI.BallDisplay.__init__(self)
                self.level = level
                
            def on_realize(self, widget, data=None):
                Game.UI.BallDisplay.on_realize(self, widget, data)
                context = self.get_pango_context()
                self.pango_layout = Layout(context)
                        
            def draw(self):
                # draw the brands
                rect = self.get_allocation()
                spacing = 10
                size = min(rect.width / 4, rect.height / len(Game.Data.brands) - spacing)
                #spacing = 10
                w = size + spacing
                for i, brand in enumerate(Game.Data.brands[:self.level + 1]):
                    
                    self.gc.set_foreground(self.styles[brand])
                    self.window.draw_arc(self.gc, True, 0, i * w, \
                                                            size, size, 0, 360 * 64)
                    self.pango_layout.set_text(str(Game.Data.brands_data[brand]))
                    self.window.draw_layout(self.gc, int(size * 1.5), \
                                            i * w + 3, self.pango_layout)
        
        class GraphicsData:
            def __init__(self, window, gc, pango_layout):
                self.styles = {}
                self.gc = gc
                self.window = window
                self.pango_layout = pango_layout
                self.cutoff_line_style = None

            
    class Data:
        width = 6
        height = 7
        brands = ['green', 'yellow', 'orange', 'purple', 'red', 'black', \
                'white', 'blue', 'turquoise', 'grey', 'violet', 'khaki']
        brands_data = {'green': 1, 'yellow': 3, 'orange': 9, 'purple': 30,
                'red': 90, 'black': 300, 'white': 900, 'blue': 3000,
                'turquoise': 9000, 'grey': 30000, 'violet': 90000,
                'khaki': 300000}
        positions = ['up', 'right', 'down', 'left'][::-1]
        level = 2
        def __init__(self):
            self.score = 0
            self.bonus = 0
            self.sequence = []
            self.balls = [[], [], [], [], [], []]
            self.direction = 'right'
            self.position = 0
            self.previous_balls = None
            self.last_drop = None
            self.last_score = None
            
        def get_score(self):
            return sum(sum(self.brands_data[ball] for ball in col) for col in self.balls)
            
        def backup(self):
            self.last_score = self.score, self.bonus
            self.last_drop = self.sequence.pop(0)
            self.previous_balls = [column[:] for column in self.balls]
        
        def restore(self):
            if self.last_drop is None or self.previous_balls is None:
                raise Exception('restore impossible')
            self.sequence[:0] = [self.last_drop]
            self.balls = self.previous_balls
            self.last_drop = None
            self.previous_balls = None
            self.score, self.bonus = self.last_score
        
        
    class Engine:
        POPPED = 0
        EMPTY = 1
        GAME_OVER = 2
        
        def __init__(self, data):
            self.data = data
            self.on_level_up = None
            self.on_level_change = None
            self.on_score_change = None
            self.on_preview_change = None
            self.on_endgame = None
            self.over = False # XXX: or False?
            
        @running_event
        def rotate(self):
            self.data.direction = Game.Data.positions[ \
                            Game.Data.positions.index(self.data.direction) - 1]
            if self.data.position == self.data.width - 1 \
                                and self.data.direction in ('right', 'left'):
                self.data.position = self.data.position - 1
            return True
            
        @running_event
        def shift_right(self):
            if self.data.position == self.data.width - 1 or \
                                (self.data.direction in ('right', 'left') and \
                                self.data.position == self.data.width - 2):
                return False
            self.data.position = self.data.position + 1
            return True
        
        @running_event
        def shift_left(self):
            if self.data.position == 0:
                return False
            self.data.position = self.data.position - 1
            return True
            
        def endgame(self):
            safe_call(self.on_endgame)
            
        def update_sequence(self):
            available = Game.Data.brands[:max(self.data.level, 3)]
            while len(self.data.sequence) < 3:
                self.data.sequence.append((random.choice(available), \
                                random.choice(available)))
            safe_call(self.on_preview_change, self.data.sequence)

        def start(self):
            self.update_sequence()
        
        def next_turn(self):
            self.update_sequence()
        
        @running_event
        def drop(self):
            position = self.data.position
            orientation = self.data.direction
            if orientation == 'right':
                first = (0, 0)
                second = (1, 1)
            elif orientation == 'up':
                first = (0, 0)
                second = (1, 0)
            elif orientation == 'left':
                first = (0, 1)
                second = (1, 0)
            else: # orientation == 'down'
                first = (1, 0)
                second = (0, 0)
            falling = self.data.sequence[0]
            self.data.backup()
            self.put(falling[first[0]], first[1] + position)
            self.put(falling[second[0]], second[1] + position)
            
            # enter main loop
            result = self.check()
            while result == Game.Engine.POPPED:
                safe_call(self.on_score_change, self.data.score, self.data.bonus)
                result = self.check()
            if result != Game.Engine.GAME_OVER:
                self.next_turn()
            else:
                self.over = True
                self.endgame()
            return True
        
        def put(self, brand, column):
            if len(self.data.balls[column]) < self.data.height:
                self.data.score = self.data.score + \
                                                self.data.brands_data[brand]
            self.data.balls[column].append(brand)
            
        def check(self):
            def choose_final(chain):
                chain.sort(key=lambda x: x[0])
                return min(chain, key=lambda x: x[1])
            
            def cleanup():
                for col in self.data.balls:
                    while None in col: # replace with something faster
                        col.remove(None)
            
            def morph(chain, score_per_ball):
                col, line = choose_final(chain)
                chain.remove((col, line))
                upgraded_score = self.upgrade(col, line)
                l = len(chain)
                self.data.score += upgraded_score - (l + 1) * score_per_ball
                self.data.bonus += score_per_ball * (l - 2)
                for col, line in chain:
                    self.data.balls[col][line] = None
            
            chains = self.find_chains()
            if not chains:
                if any(len(elem) > self.data.height for elem in self.data.balls):
                    return Game.Engine.GAME_OVER
                else:
                    return Game.Engine.EMPTY
            for chain, score in chains:
                morph(chain, score)
            cleanup()
            return Game.Engine.POPPED
                
        def upgrade(self, col, line):
            balls = self.data.balls
            brands = self.data.brands
            index = brands.index(balls[col][line]) + 1
            if index > self.data.level:
                self.data.level = index
                safe_call(self.on_level_up, index)
                safe_call(self.on_level_change, index)
            balls[col][line] = brands[index]
            return self.data.brands_data[brands[index]]
                
        def find_chains(self):
            def check_one(c, l, brand):
                if (c, l) in checked:
                    return []
                checked.append((c, l))
                frens = []
                if brand in self.data.balls[c][l - 1:l]:
                    ball = (c, l - 1)
                    frens.append(ball)
                if brand in self.data.balls[c][l + 1:l + 2]:
                    ball = (c, l + 1)
                    frens.append(ball)
                if c < self.data.width - 1 and \
                                    brand in self.data.balls[c + 1][l:l + 1]:
                    ball = (c + 1, l)
                    frens.append(ball)
                return [(c, l)] + sum((check_one(col, lin, brand) \
                                                    for col, lin in frens), [])
            checked = []
            chains = []
            for i, column in enumerate(self.data.balls):
                for y, ball in enumerate(column):
                    chain = check_one(i, y, ball)
                    if len(chain) >= 3:
                        chains.append((chain, self.data.brands_data[ball]))
            return chains
        
        def undo(self):
            self.data.restore()
            safe_call(self.on_preview_change, self.data.sequence)
            safe_call(self.on_level_change, self.data.level)
            return True
    
    MINIMUM_MOUSE_INTERVAL = 0.2
    
    def __init__(self):
        self.w = gtk.Window()
        hbox = gtk.HBox()
        self.w.add(hbox)
        self.da = gtk.DrawingArea()
        self.types_view = Game.UI.TypesView()
        vbox = gtk.VBox()
        hbox.pack_start(vbox)
        vbox.pack_start(self.types_view)
        self.score_label = gtk.Label('Score')
        self.bonus_label = gtk.Label('Bonus')
        vbox.pack_start(self.score_label, expand=False)
        vbox.pack_start(self.bonus_label, expand=False)
        vbox = gtk.VBox()
        hbox.pack_start(vbox)
        self.preview = Game.UI.Preview()
        vbox.pack_start(self.preview)
        vbox.pack_start(self.da)
        self.w.connect('destroy', self.on_destroy)
        self.da.connect('expose-event', self.on_expose)
        self.da.connect('realize', self.on_realize)
        self.da.set_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.w.connect('key-press-event', self.on_keydown)
        self.w.set_default_size(250, 350)
        self.last_mouse_event = time.time()
        
        self.game = None
        self.data = None
        self.graphics_data = None
  
                
    def on_destroy(self, widget,  data=None):
        gtk.main_quit()
        
    def on_expose(self, widget, data=None):
        # TODO: use a grid instead
        self.types_view.set_size_request(self.w.get_allocation().width / 4, 0)
        self.redraw()
        
    def on_realize(self, widget, data=None):
        window = widget.window
        gc = window.new_gc()
        if self.graphics_data is None:
            context = self.da.get_pango_context()
            pango_layout = Layout(context)
            self.graphics_data = Game.UI.GraphicsData(window, gc, pango_layout)
            colormap = self.da.get_colormap()
            for name in Game.Data.brands:
                print name
                self.graphics_data.styles[name] = colormap.alloc_color(name)
            self.graphics_data.cutoff_line_style = (colormap.alloc_color('white'), colormap.alloc_color('black'))
            
            # clickety portion
            self.da.connect('button-press-event', self.on_mouse_press)

        if not self.game or not self.data:
            self.data = Game.Data()
            self.game = Game.Engine(self.data)
            # keybindings return True if redraw is needed
            self.keybindings = {'Up': self.game.rotate,
                                'Right': self.game.shift_right,
                                'Left': self.game.shift_left,
                                'Down': self.game.drop,
                                'F5': self.game.undo}

            self.game.on_level_change = self.level_change
            self.game.on_preview_change = self.sequence_change
            self.game.on_score_change = self.set_score
            self.types_view.level = self.data.level
            self.game.start()
            
    def set_score(self, score, bonus):
        self.score_label.set_label(str(score))
        self.bonus_label.set_label(str(bonus))
    
    def sequence_change(self, sequence):
        self.preview.pair = sequence[1]
        self.preview.draw()

    @engine_interaction
    def on_mouse_press(self, widget, event, data=None):
        """top 1/3: rotation, bottom triangle: drop, sides: move"""
        now = time.time()
        prev_mouse_event = self.last_mouse_event
        self.last_mouse_event = now
        if now - prev_mouse_event < self.MINIMUM_MOUSE_INTERVAL:
            return False
            
        rect = self.da.get_allocation()
        x = event.x - rect.x
        y = event.y - rect.y
        
        if y < rect.height / 3:
            return self.game.rotate()
        if x > rect.width / 2:
            if rect.width - x < rect.height - y:
                return self.game.shift_right()
            else:
                return self.game.drop()
        else:
            if x < rect.height - y:
                return self.game.shift_left()
            else:
                return self.game.drop()

    def level_change(self, level):
        self.types_view.level = level
        self.types_view.draw()
        print 'LEVEL:', Game.Data.brands[level], '(' + str(level) + ')'

    @engine_interaction
    def on_keydown(self, widget, event, user_param1=None, *args):
        try:
            action = self.keybindings[gtk.gdk.keyval_name(event.keyval)]
        except Exception, e:
            return False
        return action()
    
    def run(self):
        self.w.show_all()
        gtk.main()
        
    def redraw(self):
        self.graphics_data.window.clear()
        next_y = 20
        pad_left = 12
        
        # draw next pair
        # TODO: ugly, change it
        rect = self.da.get_allocation()
        ball_spacing = 0.2
        ball_size = min(rect.width / (self.data.width * (1 + ball_spacing) - ball_spacing),
                        rect.height / ((self.data.width + 4) * (1 + ball_spacing) - ball_spacing))
        w = ball_size * (1 + ball_spacing)
        diff = self.data.position * w
        width, height = rect.width, rect.height
        next = self.data.sequence[0]
        coords = [None, None]
        if self.data.direction == 'up':
            coords[0] = 0, 1
            coords[1] = 0, 0
        elif self.data.direction == 'right':
            coords[0] = 0, 1
            coords[1] = 1, 1
        elif self.data.direction == 'down':
            coords[0] = 0, 0
            coords[1] = 0, 1
        else: # self.data.direction == 'left':
            coords[0] = 1, 1
            coords[1] = 0, 1
        
        for (x, y), ball in zip(coords, next):
            x, y = int(x * w + diff), int(y * w)
            # x2, y2 = x2 * w + diff + left, y2 * w + top
            self.graphics_data.gc.set_foreground(self.graphics_data.styles[ball])
            self.graphics_data.window.draw_arc(self.graphics_data.gc, True, x, y, int(ball_size), int(ball_size), 0, 360 * 64)
        
        # draw the field
        for c, column in enumerate(self.data.balls):
            x = int(c * w)
            for l, ball in enumerate(column):
                y = int(w * (self.data.height - l + 2))
                self.graphics_data.gc.set_foreground(self.graphics_data.styles[ball])
                self.graphics_data.window.draw_arc(self.graphics_data.gc, True, \
                                        x, y, int(ball_size), int(ball_size), 0, 360 * 64)
        
        # draw the cutoff line
        color_up, color_down = self.graphics_data.cutoff_line_style
        y = int(3 * w - ball_spacing / 2)
        x = int(self.data.width * w - ball_spacing)
        self.graphics_data.gc.set_foreground(color_up)
        self.graphics_data.window.draw_line(self.graphics_data.gc, 0, y - 1, x, y - 1)
        self.graphics_data.gc.set_foreground(color_down)
        self.graphics_data.window.draw_line(self.graphics_data.gc, 0, y, x, y)

        
Game().run()
