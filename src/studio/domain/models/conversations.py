"""Domain model for chat conversation history."""

from django.db import models


class Conversation(models.Model):
    session_id = models.CharField(max_length=255)
    message = models.TextField()
    is_user = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lmforge_core_conversation"

    def __str__(self) -> str:
        role = "User" if self.is_user else "Chatbot"
        return f"Session {self.session_id} - {role}: {self.message}"
