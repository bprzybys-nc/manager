from datetime import datetime

import openai


class Conversation:
    def __init__(self, dbclient, conversation_id=None):
        self.db = dbclient["conversations_db"]
        self.collection = self.db["conversations"]
        self.conversation_id = conversation_id or self._create_new_conversation()

    def _create_new_conversation(self):
        conversation = {"created_at": datetime.utcnow(), "messages": []}
        result = self.collection.insert_one(conversation)
        return result.inserted_id

    def add_message(self, role, content):
        message = {"role": role, "content": content, "timestamp": datetime.utcnow()}
        self.collection.update_one(
            {"_id": self.conversation_id}, {"$push": {"messages": message}}
        )

    def get_messages(self):
        conversation = self.collection.find_one({"_id": self.conversation_id})
        return conversation["messages"] if conversation else []


class OpenAIInterface:
    def __init__(self, api_key, dbclient):
        self.api_key = api_key
        openai.api_key = self.api_key
        self.dbclient = dbclient

    def send_message(self, message, model="gpt-3.5-turbo", conversation_id=None):
        conversation = Conversation(self.dbclient, conversation_id)
        conversation.add_message("user", message)

        response = openai.ChatCompletion.create(
            model=model, messages=conversation.get_messages()
        )

        reply = response.choices[0].message["content"]
        conversation.add_message("assistant", reply)

        return reply


class Config:
    def __init__(
        self,
        model="gpt-4o",
        endpoint="https://api.openai.com/v1/chat/completions",
    ):
        self.model = model
        self.endpoint = endpoint
