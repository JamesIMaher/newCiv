"""Colours, fonts and small drawing helpers shared by the UI."""
import pygame

BG = (12, 16, 22)
PANEL = (22, 30, 40)
PANEL_LIGHT = (34, 46, 60)
PANEL_BORDER = (70, 110, 120)
TEXT = (220, 230, 225)
TEXT_DIM = (140, 155, 150)
ACCENT = (110, 210, 170)
WARN = (235, 120, 90)
GOOD = (120, 220, 120)
GOLD = (240, 210, 110)
NUTRIENT = (120, 210, 90)
MINERAL = (170, 170, 200)
ENERGY = (240, 210, 80)
BUTTON = (40, 62, 72)
BUTTON_HOVER = (58, 92, 104)
BUTTON_DISABLED = (34, 40, 46)
BUTTON_SELECTED = (60, 120, 100)

_fonts = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _fonts:
        f = pygame.font.Font(None, size)
        f.set_bold(bold)
        _fonts[key] = f
    return _fonts[key]


def text(surf, s, pos, size=20, color=TEXT, bold=False, center=False, right=False):
    img = font(size, bold).render(str(s), True, color)
    r = img.get_rect()
    if center:
        r.center = pos
    elif right:
        r.topright = pos
    else:
        r.topleft = pos
    surf.blit(img, r)
    return r


def wrap(s, size, width):
    f = font(size)
    lines = []
    for para in str(s).split("\n"):
        words = para.split(" ")
        cur = ""
        for w in words:
            trial = (cur + " " + w).strip()
            if f.size(trial)[0] <= width or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def text_block(surf, s, rect, size=18, color=TEXT, line_gap=2):
    y = rect[1]
    lh = font(size).get_linesize() + line_gap
    for line in wrap(s, size, rect[2]):
        if y + lh > rect[1] + rect[3]:
            break
        text(surf, line, (rect[0], y), size, color)
        y += lh
    return y


def panel(surf, rect, color=PANEL, border=PANEL_BORDER, alpha=None, radius=6):
    rect = pygame.Rect(rect)
    if alpha is not None:
        s = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha), s.get_rect(), border_radius=radius)
        surf.blit(s, rect)
    else:
        pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surf, border, rect, 1, border_radius=radius)


def bar(surf, rect, frac, color, back=(40, 45, 50)):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, back, rect)
    w = int(rect.width * max(0.0, min(1.0, frac)))
    if w:
        pygame.draw.rect(surf, color, (rect.x, rect.y, w, rect.height))
    pygame.draw.rect(surf, (90, 100, 105), rect, 1)


def shade(color, amount):
    return tuple(max(0, min(255, int(c + amount))) for c in color)


def mix(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


RESOURCE_COLORS = {"nutrients": NUTRIENT, "minerals": MINERAL, "energy": ENERGY}


def resource_icon(surf, kind, center, size=7):
    """Small pictogram: a leaf for nutrients, a crystal for minerals, a bolt for energy."""
    cx, cy = center
    s = size
    if kind == "nutrients":
        r = pygame.Rect(cx - s, cy - s // 2 - 1, 2 * s, s + 2)
        pygame.draw.ellipse(surf, (70, 170, 60), r)
        pygame.draw.ellipse(surf, (190, 250, 170), r, 1)
        pygame.draw.line(surf, (30, 90, 30), (cx - s + 2, cy + 1), (cx + s - 2, cy - 1), 1)
    elif kind == "minerals":
        pts = [(cx, cy - s), (cx + s * 3 // 4, cy - s // 4), (cx + s // 2, cy + s), (cx - s // 2, cy + s),
               (cx - s * 3 // 4, cy - s // 4)]
        pygame.draw.polygon(surf, (130, 140, 190), pts)
        pygame.draw.polygon(surf, (225, 230, 255), pts, 1)
    else:
        pts = [(cx + s // 3, cy - s), (cx - s // 2, cy + 1), (cx, cy + 1), (cx - s // 3, cy + s),
               (cx + s // 2, cy - 1), (cx, cy - 1)]
        pygame.draw.polygon(surf, (250, 210, 60), pts)
        pygame.draw.polygon(surf, (255, 250, 200), pts, 1)


def yields(surf, pos, n, m, e, size=18, words=False, gap=10):
    """Draw 'leaf 2  crystal 1  bolt 0' (optionally with names). Returns list of (kind, rect)."""
    x, y = pos
    out = []
    h = font(size).get_linesize()
    for kind, val in (("nutrients", n), ("minerals", m), ("energy", e)):
        icon = max(4, size // 3)
        resource_icon(surf, kind, (x + icon, y + h // 2 - 1), icon)
        label = f"{val} {kind.title()}" if words else str(val)
        r = text(surf, label, (x + icon * 2 + 4, y), size, RESOURCE_COLORS[kind], bold=True)
        out.append((kind, pygame.Rect(x, y, r.right - x, h)))
        x = r.right + gap
    return out
