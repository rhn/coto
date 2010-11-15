#!/usr/bin/python
# -*- coding: utf8 -*-
import gtk
import pygtk
pygtk.require('2.0')
import random
from sys import stdout
from pango import Layout

__version__ = '0.1.3'

"""
    cototakiego.py - a clone of OpenAlchemist in Pygtk
    Copyright (C) 2007  Paweł Czaplejewicz

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

class Game:
    class UI:
        class Preview:
            # minimum offset from the borders (fraction of the ball size)
            border_x = 0.25
            border_y = 0.25
            # distance between ball edges (fraction of the ball size)
            ball_distance = 0.25
            
            def get_coords(self, xsize, ysize):
                """Justified to the left/up.
                Returns a tuple consisting of balls' coords and ball size.
                """
                ball_size = min(xsize / (2 + self.border_x * 2 + \
                                                      self.ball_distance), \
                            ysize / (1 + self.border_y * 2))
                border_x = int(ball_size * self.border_x)
                border_y = int(ball_size * self.border_y)
                distance = int(ball_size * self.ball_distance)
                ball_size = int(ball_size)
                return ((border_x, border_y), 
                        (border_x + ball_size + distance, border_y)), ball_size
                       
        # TODO: switch to relative values
        preview_rectangle = (80, 0, 200, 20)
        board_rectangle = (80, 20, 200, 300)
        brands_rectangle = (0, 0, 80, 300)
        scores_rectangle = (200, 0, 250, 300)
            
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
        
    class Anim:
        lasts = False
    
    class Engine:
        POPPED = 0
        EMPTY = 1
        GAME_OVER = 2
        
        def __init__(self, data):
            self.data = data
            # keybindings return True if redraw is needed
            self.keybindings = {'Up': self.on_key_up,
                                'Right': self.on_key_right,
                                'Left': self.on_key_left,
                                'Down': lambda: any((True, self.drop())),
                                'F5': lambda: any((True, self.undo()))}
            
        def on_key_up(self):
            self.data.direction = Game.Data.positions[ \
                            Game.Data.positions.index(self.data.direction) - 1]
            if self.data.position == self.data.width - 1 \
                                and self.data.direction in ('right', 'left'):
                self.data.position = self.data.position - 1
            return True
            
        def on_key_right(self):
            if self.data.position == self.data.width - 1 or \
                                (self.data.direction in ('right', 'left') and \
                                self.data.position == self.data.width - 2):
                return False
            self.data.position = self.data.position + 1
            return True
        
        def on_key_left(self):
            if self.data.position == 0:
                return False
            self.data.position = self.data.position - 1
            return True
        
        def lock_keys(self):
            self.keybindings_backup = self.keybindings
            self.keybindings = {}
            
        def unlock_keys(self):
            self.keybindings = self.keybindings_backup
            
        def endgame(self):
            print '\nGAME OVER'
            
        def next_turn(self):
            available = Game.Data.brands[:max(self.data.level, 3)]
            while len(self.data.sequence) < 3:
                self.data.sequence.append((random.choice(available), \
                                random.choice(available)))
        
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
            self.lock_keys()
            result = self.check()
            while result == Game.Engine.POPPED:
                result = self.check()
            if result != Game.Engine.GAME_OVER:
                self.next_turn()
                self.unlock_keys()
            else:
                self.endgame()
            stdout.write('\rscore: ' + str(self.data.score) + \
                                            ' bonus: ' + str(self.data.bonus))
            stdout.flush()
        
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
                print 'LEVEL:', brands[index], '(' + str(index) + ')'
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
            
    def __init__(self):
        self.w = gtk.Window()
        self.da = gtk.DrawingArea()
        self.w.add(self.da)
        self.w.connect('destroy', self.on_destroy)
        self.da.connect('expose-event', self.on_expose)
        self.da.connect('realize', self.on_realize)
        self.w.connect('key-press-event', self.on_keydown)
        self.w.set_default_size(250, 350)
        
        self.game = None
        self.data = None
        
    def on_destroy(self, widget,  data=None):
        gtk.main_quit()
        
    def on_expose(self, widget, data=None):
        self.redraw()
        
    def on_realize(self, widget, data=None):
        self.window = widget.window
        self.gc = self.window.new_gc()
        if not self.game or not self.data:
            self.data = Game.Data()
            self.game = Game.Engine(self.data)
            self.data.styles = {}
            context = self.da.get_pango_context()
            self.data.layout = Layout(context)
            self.preview = Game.UI.Preview()
            colormap = self.da.get_colormap()
            for name in self.data.brands:
                print name
                self.data.styles[name] = colormap.alloc_color(name)
            self.game.next_turn()

    def on_keydown(self, widget, event, user_param1=None, *args):
        try:
            action = self.game.keybindings[gtk.gdk.keyval_name(event.keyval)]
        except:
            print gtk.gdk.keyval_name(event.keyval)
            return False
        if action():
            self.redraw()
        return True
    
    def run(self):
        self.w.show_all()
        gtk.main()
        
    def redraw(self):
        self.window.clear()
        next_y = 20
        pad_left = 12
        
        # draw preview
        next = self.data.sequence[1]
        left, top, width, height = Game.UI.preview_rectangle
        coords_list, size = self.preview.get_coords(width, height)
        for i, xy in enumerate(coords_list):
            x, y = xy
            ball = next[i]
            self.gc.set_foreground(self.data.styles[ball])
            self.window.draw_arc(self.gc, True, left + x, top + y, \
                                                    size, size, 0, 360 * 64)
        
        # draw next pair
        # TODO: ugly, change it
        size = 20
        distance = 4
        w = size + distance
        diff = self.data.position * w
        left, top, width, height = Game.UI.board_rectangle
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
        
        for xy, ball in zip(coords, next):
            x, y = xy[0], xy[1]
            x, y = x * w + diff + left, y * w + top
            # x2, y2 = x2 * w + diff + left, y2 * w + top
            self.gc.set_foreground(self.data.styles[ball])
            self.window.draw_arc(self.gc, True, x, y, size, size, 0, 360 * 64)
        
        # draw the field
        for c, column in enumerate(self.data.balls):
            for l, ball in enumerate(column):
                self.gc.set_foreground(self.data.styles[ball])
                self.window.draw_arc(self.gc, True, \
                                        left + c * w, top + height - l * w, \
                                        size, size, 0, 360 * 64)
        
        # draw the brands
        left, top, width, height = Game.UI.brands_rectangle
        yoffset = top + 10
        xoffset = left + 5
        size = 15
        distance = 10
        w = size + distance
        for i, brand in enumerate(self.data.brands[:self.data.level + 1]):
            self.gc.set_foreground(self.data.styles[brand])
            self.window.draw_arc(self.gc, True, xoffset, yoffset + i * w, \
                                                    size, size, 0, 360 * 64)
            self.data.layout.set_text(str(self.data.brands_data[brand]))
            self.window.draw_layout(self.gc, xoffset + int(size * 1.5), \
                                    yoffset + i * w + 3, self.data.layout)

Game().run()