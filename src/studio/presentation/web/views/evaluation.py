from django.shortcuts import render


def model_statistics_view(request):
    return render(request, "web/pages/evaluation/model_statistics.html")
