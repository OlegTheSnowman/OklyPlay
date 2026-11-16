"""OklyPlay's look: accent colour, the logo, and small list markers.

Everything is drawn with wx at runtime, so there are no image files to ship
or keep in sync. tools/make_icon.py uses draw_logo to write the exe icon."""

import math

import wx

# Deep indigo; white text on it has a contrast ratio of about 8:1.
ACCENT = wx.Colour(0x3B, 0x2F, 0xA8)
ACCENT_TEXT = wx.Colour(255, 255, 255)
ACCENT_SUBTLE = wx.Colour(0xD8, 0xD4, 0xF5)  # secondary text on the accent strip

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


def _paint_logo(gc, s):
    # Rounded indigo square
    gc.SetPen(wx.TRANSPARENT_PEN)
    gc.SetBrush(wx.Brush(ACCENT))
    gc.DrawRoundedRectangle(0, 0, s, s, s * 0.22)
    # White speaker: a box and a cone
    gc.SetBrush(wx.Brush(ACCENT_TEXT))
    path = gc.CreatePath()
    path.MoveToPoint(s * 0.18, s * 0.40)
    path.AddLineToPoint(s * 0.32, s * 0.40)
    path.AddLineToPoint(s * 0.50, s * 0.24)
    path.AddLineToPoint(s * 0.50, s * 0.76)
    path.AddLineToPoint(s * 0.32, s * 0.60)
    path.AddLineToPoint(s * 0.18, s * 0.60)
    path.CloseSubpath()
    gc.FillPath(path)
    # Two sound waves
    gc.SetBrush(wx.TRANSPARENT_BRUSH)
    gc.SetPen(gc.CreatePen(wx.GraphicsPenInfo(ACCENT_TEXT, max(1.0, s * 0.07)).Cap(wx.CAP_ROUND)))
    for r in (0.16, 0.29):
        arc = gc.CreatePath()
        arc.AddArc(s * 0.50, s * 0.50, s * r, -math.pi / 4, math.pi / 4, True)
        gc.StrokePath(arc)


def draw_logo(size):
    return _bitmap(size, _paint_logo)


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
