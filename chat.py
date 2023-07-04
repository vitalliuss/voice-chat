import os
import openai

class ChatApp:
    def __init__(self, system_message, openai_model, openai_api_key):
        openai.api_key = openai_api_key
        self.openai_model = openai_model
        self.system_message = system_message
        self.messages = [
            {"role": "system", "content": self.system_message},
        ]

    def chat(self, message):
        self.messages.append({"role": "user", "content": message})
        response = openai.ChatCompletion.create(
            model=self.openai_model,
            messages=self.messages
        )
        self.messages.append({"role": "assistant", "content": response["choices"][0]["message"].content})
        return response["choices"][0]["message"]