import os
import subprocess
import sounddevice
import pyaudio
import time
import wave
import numpy as np
from gpiozero import Button
from pathlib import Path
from openai import OpenAI

# OpenAI API Key
client = OpenAI( api_key = 'sk-...................' )

# Sound record settings
CHUNK = 256
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
GAIN = 5

ai_speech_file   = Path(__file__).parent / "ai_speech.mp3"
user_speech_file = Path(__file__).parent / "user_speech.wav"

# GPIO Button settings
button = Button(4, bounce_time=0.2)

# Global variables
audio_available = False


# Generate a text response from an AI model based on the input message
def ai_text_to_text( message ):
   if message:
      messages = [
         {"role":'system','content':'Respond concisely, in a maximum of three sentences!'},
         {"role": "user", "content": message},
      ]
      chat = client.chat.completions.create(
         model="gpt-4o", messages=messages
      )
   return chat.choices[0].message.content


# Convert text to speech using an AI model and save the result to a file
def ai_text_to_voice( text ):
    with client.audio.speech.with_streaming_response.create(
      model="tts-1",
      voice="onyx",
      input=text,
    ) as response:
      response.stream_to_file(ai_speech_file)
    return True


# Transcribe speech from an audio file to text using an AI model
def ai_voice_to_text():
    audio_file = open(user_speech_file, "rb")
    transcription = client.audio.transcriptions.create(
      model="whisper-1", 
      file=audio_file
    )
    return transcription.text


# Record audio from the microphone and save it to a file
def audio_recording():
    global audio_available

    # Create audio file
    audio = pyaudio.PyAudio()
    on_recording = True
    frames = []
    stream = audio.open(
        format=pyaudio.paInt16,  input=True,
        channels=CHANNELS, rate=RATE, frames_per_buffer=CHUNK)

    print ("Recording started...")

    while True:
        # Recording loop
        if ( button.is_pressed ):
            data = stream.read(CHUNK)
            audio_data = np.frombuffer(data, dtype=np.int16)
            audio_data = audio_data * GAIN
            audio_data = np.clip(audio_data, -32768, 32767)
            frames.append(audio_data.astype(np.int16).tobytes())

        else:
            # Audio file close
            if (on_recording == True):
                stream.stop_stream()
                stream.close()
                audio.terminate()
                waveFile = wave.open(str(user_speech_file), 'wb')
                waveFile.setnchannels(CHANNELS)
                waveFile.setsampwidth(audio.get_sample_size(FORMAT))
                waveFile.setframerate(RATE)
                waveFile.writeframes(b''.join(frames))
                waveFile.close()

                on_recording = False
                audio_available = True

                print ("Recording ended.")
                break


# Function to process an audio question by transcribing, generating a text response, and converting it to speech
def process_audio_questation( silent = False ):
    global audio_available
    audio_available = False

    print ("Processing...\n")
    
    if ( not silent ):
        message = ai_voice_to_text()
        print(f"User: {message}")

        answer = ai_text_to_text( message )
        print(f"ChatGPT: {answer} \n")

        print ("ChatGPT speaking...\n")
        ai_text_to_voice( answer )
        os.system(f"mpg321 -o alsa -a plughw:1,0 -q {ai_speech_file}")

    print ("\nWaiting for new input. Press the button for recording!\n")
    

# Main function
def main():
    try:
        print("Program started. Press the button for recording!")
        
        while True:
            button.when_pressed = audio_recording

            if ( audio_available == True):
                process_audio_questation( silent = False)

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nProgram interrupted with Ctrl+C")
    finally:
        print("\nCleaning up... Program is exiting.")


if __name__ == "__main__":
    main()
