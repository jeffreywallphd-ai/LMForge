from django.shortcuts import render


def chatbot_view(request):
    return render(request, "web/pages/chat/chatbot.html")
