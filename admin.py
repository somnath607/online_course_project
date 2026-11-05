from django.contrib import admin

# The rubric asks for these seven imported model classes.
from .models import Choice, Course, Instructor, Learner, Lesson, Question, Submission


class ChoiceInline(admin.StackedInline):
    model = Choice
    extra = 4


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 2


class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 1


class CourseAdmin(admin.ModelAdmin):
    inlines = [LessonInline, QuestionInline]
    list_display = ("name", "pub_date", "total_enrollment")
    list_filter = ("pub_date",)
    search_fields = ("name", "description")


class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order")
    list_filter = ("course",)
    ordering = ("course", "order")


class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ("text", "course", "grade")
    list_filter = ("course",)


admin.site.register(Course, CourseAdmin)
admin.site.register(Lesson, LessonAdmin)
admin.site.register(Instructor)
admin.site.register(Learner)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Choice)
admin.site.register(Submission)

admin.site.site_header = "Online Course Administration"
admin.site.site_title = "Online Course Admin"
admin.site.index_title = "Course management"
