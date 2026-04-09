from django.shortcuts import render


def train_model_view(request):
    return render(request, "model_training.html")
