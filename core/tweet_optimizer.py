def optimize(text):
    if "؟" not in text:
        text += "\n\nما رأيك؟ 🤔"
    return text.strip()
