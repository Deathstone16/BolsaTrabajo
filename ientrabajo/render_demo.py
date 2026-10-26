"""Render-only template context for the visual demo."""


def context(_request):
    return {'render_ui_demo': True}
