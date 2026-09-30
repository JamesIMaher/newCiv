"""Immediate-mode buttons: rebuilt every frame, clicked against last frame's layout."""
import pygame

from . import theme


class Button:
    def __init__(self, rect, label, callback, enabled=True, selected=False, tooltip=None, size=20):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.callback = callback
        self.enabled = enabled
        self.selected = selected
        self.tooltip = tooltip
        self.size = size

    def draw(self, surf, mouse):
        hover = self.enabled and self.rect.collidepoint(mouse)
        if not self.enabled:
            col = theme.BUTTON_DISABLED
        elif self.selected:
            col = theme.BUTTON_SELECTED
        elif hover:
            col = theme.BUTTON_HOVER
        else:
            col = theme.BUTTON
        pygame.draw.rect(surf, col, self.rect, border_radius=4)
        pygame.draw.rect(surf, theme.PANEL_BORDER if self.enabled else (50, 58, 62), self.rect, 1, border_radius=4)
        color = theme.TEXT if self.enabled else theme.TEXT_DIM
        img = theme.font(self.size).render(self.label, True, color)
        r = img.get_rect(center=self.rect.center)
        if r.width > self.rect.width - 6:
            r.left = self.rect.left + 4
            surf.set_clip(self.rect.inflate(-4, 0))
            surf.blit(img, r)
            surf.set_clip(None)
        else:
            surf.blit(img, r)


class UI:
    """Collects the buttons drawn this frame so clicks can be routed to them."""

    def __init__(self):
        self.buttons = []
        self.prev_buttons = []
        self.mouse = (0, 0)

    def begin(self, mouse):
        self.prev_buttons = self.buttons
        self.buttons = []
        self.mouse = mouse

    def button(self, surf, rect, label, callback, enabled=True, selected=False, tooltip=None, size=20):
        b = Button(rect, label, callback, enabled, selected, tooltip, size)
        b.draw(surf, self.mouse)
        self.buttons.append(b)
        return b

    def hotspot(self, rect, tooltip):
        """An invisible, non-clickable area that shows a tooltip on hover."""
        self.buttons.append(Button(rect, "", lambda: None, enabled=False, tooltip=tooltip))

    def click(self, pos):
        for b in reversed(self.buttons):
            if b.enabled and b.rect.collidepoint(pos):
                b.callback()
                return True
        return False

    def hovered_tooltip(self):
        for b in reversed(self.buttons):
            if b.tooltip and b.rect.collidepoint(self.mouse):
                return b.tooltip
        return None

    def over_button(self, pos):
        return any(b.rect.collidepoint(pos) for b in self.buttons)
