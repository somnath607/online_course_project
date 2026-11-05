import logging

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import generic

from .models import Choice, Course, Enrollment, Question, Submission

logger = logging.getLogger(__name__)


def registration_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("psw", "")
        first_name = request.POST.get("firstname", "").strip()
        last_name = request.POST.get("lastname", "").strip()

        if not username or not password:
            context["message"] = "Username and password are required."
        elif User.objects.filter(username=username).exists():
            context["message"] = "User already exists."
        else:
            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                last_name=last_name,
                password=password,
            )
            login(request, user)
            return redirect("onlinecourse:index")

    return render(request, "onlinecourse/user_registration_bootstrap.html", context)


def login_request(request):
    context = {"next": request.GET.get("next", "")}
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("psw", "")
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(request.POST.get("next") or "onlinecourse:index")
        context["message"] = "Invalid username or password."

    return render(request, "onlinecourse/user_login_bootstrap.html", context)


def logout_request(request):
    logout(request)
    return redirect("onlinecourse:index")


def check_if_enrolled(user, course):
    return bool(
        user.is_authenticated
        and Enrollment.objects.filter(user=user, course=course).exists()
    )


class CourseListView(generic.ListView):
    template_name = "onlinecourse/course_list_bootstrap.html"
    context_object_name = "course_list"

    def get_queryset(self):
        courses = Course.objects.order_by("-total_enrollment", "name")[:10]
        for course in courses:
            course.is_enrolled = check_if_enrolled(self.request.user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = "onlinecourse/course_details_bootstrap.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_enrolled"] = check_if_enrolled(self.request.user, self.object)
        return context


@login_required
def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    _enrollment, created = Enrollment.objects.get_or_create(
        user=request.user,
        course=course,
        defaults={"mode": Enrollment.HONOR},
    )
    if created:
        course.total_enrollment = Enrollment.objects.filter(course=course).count()
        course.save(update_fields=["total_enrollment"])
    return HttpResponseRedirect(
        reverse("onlinecourse:course_details", args=(course.id,))
    )


@login_required
def submit(request, course_id):
    if request.method != "POST":
        return HttpResponseBadRequest("Exam submissions must use POST.")

    course = get_object_or_404(Course, pk=course_id)
    enrollment = get_object_or_404(
        Enrollment,
        user=request.user,
        course=course,
    )
    submitted_answers = extract_answers(request, course)
    submission = Submission.objects.create(enrollment=enrollment)
    submission.choices.set(submitted_answers)

    return HttpResponseRedirect(
        reverse(
            "onlinecourse:show_exam_result",
            args=(course.id, submission.id),
        )
    )


def extract_answers(request, course=None):
    """Collect selected Choice objects from the submitted exam form."""
    choice_ids = []
    for key, values in request.POST.lists():
        if key.startswith("choice"):
            for value in values:
                if value.isdigit():
                    choice_ids.append(int(value))

    queryset = Choice.objects.filter(pk__in=choice_ids)
    if course is not None:
        queryset = queryset.filter(question__course=course)
    return list(queryset)


@login_required
def show_exam_result(request, course_id, submission_id):
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(
        Submission,
        pk=submission_id,
        enrollment__user=request.user,
        enrollment__course=course,
    )

    submitted_choices = list(submission.choices.select_related("question"))
    submitted_ids = {choice.id for choice in submitted_choices}
    questions = list(course.question_set.prefetch_related("choice_set"))

    total_points = sum(question.grade for question in questions)
    achieved_points = 0
    question_results = []

    for question in questions:
        selected_for_question = [
            choice for choice in submitted_choices if choice.question_id == question.id
        ]
        is_correct = question.is_get_score(selected_for_question)
        if is_correct:
            achieved_points += question.grade

        choices = []
        for choice in question.choice_set.all():
            choices.append(
                {
                    "choice": choice,
                    "selected": choice.id in submitted_ids,
                    "is_correct": choice.is_correct,
                }
            )
        question_results.append(
            {
                "question": question,
                "is_correct": is_correct,
                "choices": choices,
            }
        )

    grade = round((achieved_points / total_points) * 100) if total_points else 0
    context = {
        "course": course,
        "submission": submission,
        "submitted_choices": submitted_choices,
        "question_results": question_results,
        "achieved_points": achieved_points,
        "total_points": total_points,
        "grade": grade,
        "passed": grade >= 80,
    }
    return render(request, "onlinecourse/exam_result_bootstrap.html", context)
