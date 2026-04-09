from django.shortcuts import render


def train_model_view(request):
    return render(request, "web/pages/training/model_training.html")
