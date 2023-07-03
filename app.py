import datetime
from time import sleep
from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import openai
import json
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech
from google.oauth2 import service_account
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.environ['OPENAI_API_KEY']
google_cloud_account_file = os.environ['GOOGLE_APPLICATION_CREDENTIALS']

openai_model = "gpt-3.5-turbo-0613"

app = Flask(__name__, static_folder="static")

@app.route('/')
def index():
    with open('job.log', 'w') as f:
        f.write('')
    add_to_log("Starting new job. This log file will be overwritten every time the application is restarted.")
    return render_template('index.html')

@app.route('/listen', methods=['POST'])
def listen():
    try:
        add_to_log('Receiving audio from client...')
        audio_file = request.files.get('audio_data')
        audio_file.save(os.path.join('audio', 'user_audio.webm'))      

        with open('audio/user_audio.webm', 'rb') as audio: #line below is for debugging
            audio_content = audio.read()
            add_to_log('Saved audio to file.')
            dummy_text = "ru-RU"
            add_to_log('language_code: {}'.format(dummy_text))

        # client = speech.SpeechClient()
        credentials = service_account.Credentials.from_service_account_file(google_cloud_account_file)
        client = speech.SpeechClient(credentials=credentials)
        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=24000,
            language_code="en-US"
            #,alternative_language_codes=["ru-RU"] - usually treats russian accent as russian language, not reliable
        )

        add_to_log('Sending audio to Google Cloud Speech-to-Text API...')
        
        response = client.recognize(config=config, audio=audio)
        transcript = response.results[0].alternatives[0].transcript
        language_code = response.results[0].language_code
        add_to_log('Regognized transcript: {}'.format(transcript))
        add_to_log('Language detected: {}'.format(language_code))


        # # Get response from GPT
        answer = generateAnswer(transcript)
        add_to_log(answer)
        audio_content = text_to_speech(answer, language_code)
        
        with open('audio/response.mp3', 'wb') as out:
            out.write(audio_content)
            
        return jsonify({'response_audio': 'response.mp3'})
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)})


def text_to_speech(text, language_code):
    client = texttospeech.TextToSpeechClient()

    # Set the text input to be synthesized
    synthesis_input = texttospeech.SynthesisInput(text=text)

    # Build the voice request
    voice = texttospeech.VoiceSelectionParams(
        language_code=language_code,
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL)

    # Select the type of audio file you want returned
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3)

    # Perform the text-to-speech request
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config)

    return response.audio_content

def generateAnswer(question):
    return request_gpt(question)

def request_gpt(conversation):
    system_message = "Provide the shortest answer possible" # make debug cheaper
    return openai_call(system_message, conversation)

def openai_call(system_message, input):
    response = openai.ChatCompletion.create(
        model=openai_model,
        messages=[
            {"role": "system", "content": "" + system_message + ""},
            {"role": "user", "content": "" + input + ""}
        ]
    )
    add_to_log(json.dumps(response))
    result = response['choices'][0]['message']['content']
    return result

def add_to_log(message):
    with open('job.log', 'a') as f:
        message_with_timestamp = '{}: {}\n'.format(datetime.datetime.now(), message)
        f.write(message_with_timestamp)      
        print(message_with_timestamp)


@app.route('/stream')
def stream():
    def generate():
        with open('job.log') as f:
            while True:
                yield f.read()
                sleep(1)
    return app.response_class(generate(), mimetype='text/plain')

@app.route('/audio/<path:path>')
def send_audio(path):
    return send_from_directory('audio', path)

if __name__ == "__main__":
    if not os.path.exists('audio'):
        os.makedirs('audio')
    app.run(debug=True)