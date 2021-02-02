import random
import numpy
import pygame
from .board import Board
from .gui import SelectionGroup, Input, Button, Label, InputDialogue


class BoardAxis:
    def __init__(self, board, font, color):
        self.font = font
        self.color = color

        self.x_axis = []
        self.y_axis = []

        self.set(board)

    def set(self, board):
        self.x_axis.clear()
        for i in range(board.n_cols):
            x = Label(self.font, self.color, chr(ord('A') + i))
            x.rect.centerx = board.rect.left + i * board.tile_size + board.tile_size / 2
            x.rect.centery = board.rect.bottom + board.tile_size / 2
            self.x_axis.append(x)

        self.y_axis.clear()
        for i in range(board.n_rows):
            y = Label(self.font, self.color, str(i))
            y.rect.centerx = board.rect.left - board.tile_size / 2
            y.rect.centery = board.rect.bottom - i * board.tile_size - board.tile_size / 2
            self.y_axis.append(y)

    def draw(self, other_surface):
        for x in self.x_axis:
            x.draw(other_surface)
        for y in self.y_axis:
            y.draw(other_surface)
