from django.shortcuts import render


def model_statistics_view(request):
    return render(request, "model_statistics.html")
