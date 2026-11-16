"""OklyPlay's look: accent colour, the logo, and small list markers.

Everything is drawn with wx at runtime, so there are no image files to ship
or keep in sync. tools/make_icon.py uses draw_logo to write the exe icon."""

import math

import wx

# Deep indigo; white text on it has a contrast ratio of about 8:1.
ACCENT = wx.Colour(0x3B, 0x2F, 0xA8)
ACCENT_TEXT = wx.Colour(255, 255, 255)
PAD_LIT = wx.Colour(0xFF, 0xB0, 0x00)  # amber: the pad "being pressed" in the logo

# Okabe-Ito palette: stays distinguishable with the common colour vision deficiencies.
BUS_COLOURS = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00", "#F0E442", "#555555"]


def _bitmap(size, paint):
    img = wx.Image(size, size)
    img.SetAlpha(bytearray(size * size))  # start fully transparent
    bmp = wx.Bitmap(img)
    dc = wx.MemoryDC(bmp)
    gc = wx.GraphicsContext.Create(dc)
    gc.SetAntialiasMode(wx.ANTIALIAS_DEFAULT)
    paint(gc, size)
    del gc
    dc.SelectObject(wx.NullBitmap)
    return bmp


def _paint_logo(gc, s, tile=True):
    """A soundboard: a 2 by 2 grid of pads on an indigo tile, one pad lit amber."""
    gc.SetPen(wx.TRANSPARENT_PEN)
    if tile:
        gc.SetBrush(wx.Brush(ACCENT))
        gc.DrawRoundedRectangle(0, 0, s, s, s * 0.22)
    margin, gap = s * 0.2, s * 0.08
    pad = (s - 2 * margin - gap) / 2
    for row in range(2):
        for col in range(2):
            lit = (row, col) == (0, 1)
            gc.SetBrush(wx.Brush(PAD_LIT if lit else ACCENT_TEXT))
            x = margin + col * (pad + gap)
            y = margin + row * (pad + gap)
            gc.DrawRoundedRectangle(x, y, pad, pad, pad * 0.25)


def draw_logo(size, tile=True):
    """The logo; tile=False draws just the pads, for use on the indigo header."""
    return _bitmap(size, lambda gc, s: _paint_logo(gc, s, tile))


def icon_bundle():
    bundle = wx.IconBundle()
    for size in (16, 20, 24, 32, 40, 48, 64, 256):
        icon = wx.Icon()
        icon.CopyFromBitmap(draw_logo(size))
        bundle.AddIcon(icon)
    return bundle


def dot(colour, size):
    """A filled circle, used as a colour marker in lists."""
    def paint(gc, s):
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(wx.Colour(colour)))
        d = s * 0.6
        gc.DrawEllipse((s - d) / 2, (s - d) / 2, d, d)
    return _bitmap(size, paint)


def blank(size):
    return _bitmap(size, lambda gc, s: None)


def speaker(colour, size):
    """A small speaker with one wave, marking a sound that is playing."""
    def paint(gc, s):
        gc.SetPen(wx.TRANSPARENT_PEN)
        gc.SetBrush(wx.Brush(colour))
        path = gc.CreatePath()
        path.MoveToPoint(s * 0.12, s * 0.38)
        path.AddLineToPoint(s * 0.30, s * 0.38)
        path.AddLineToPoint(s * 0.52, s * 0.18)
        path.AddLineToPoint(s * 0.52, s * 0.82)
        path.AddLineToPoint(s * 0.30, s * 0.62)
        path.AddLineToPoint(s * 0.12, s * 0.62)
        path.CloseSubpath()
        gc.FillPath(path)
        gc.SetBrush(wx.TRANSPARENT_BRUSH)
        gc.SetPen(gc.CreatePen(wx.GraphicsPenInfo(colour, max(1.0, s * 0.1)).Cap(wx.CAP_ROUND)))
        arc = gc.CreatePath()
        arc.AddArc(s * 0.52, s * 0.50, s * 0.26, -math.pi / 3, math.pi / 3, True)
        gc.StrokePath(arc)
    return _bitmap(size, paint)
