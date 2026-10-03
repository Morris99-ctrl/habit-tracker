import pyttsx3

engine = pyttsx3.init()

voices = engine.getProperty("voices")

engine.setProperty("voice", voices[2].id)
engine.setProperty("rate", 100)

def speak(text):
    engine.say(text)
    engine.runAndWait()

speak("All systems are functional. It's nice to have here with you. I am Jarvis, your personal assistant. How can I help you today?")

print("Available voices:")
for index, voice in  enumerate(voices):
    print(f"{index}: {voice.name} - voice.id")
