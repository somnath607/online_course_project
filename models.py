from django.conf import settings
from django.db import models
from django.utils.timezone import now


class Instructor(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    full_time = models.BooleanField(default=True)
    total_learners = models.IntegerField(default=0)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Learner(models.Model):
    STUDENT = "student"
    DEVELOPER = "developer"
    DATA_SCIENTIST = "data_scientist"
    DATABASE_ADMIN = "dba"

    OCCUPATION_CHOICES = [
        (STUDENT, "Student"),
        (DEVELOPER, "Developer"),
        (DATA_SCIENTIST, "Data Scientist"),
        (DATABASE_ADMIN, "Database Admin"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    occupation = models.CharField(
        max_length=20,
        choices=OCCUPATION_CHOICES,
        default=STUDENT,
    )
    social_link = models.URLField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.user.username}, {self.get_occupation_display()}"


class Course(models.Model):
    name = models.CharField(max_length=120, default="Online Course")
    image = models.ImageField(upload_to="course_images/", blank=True)
    description = models.CharField(max_length=1000)
    pub_date = models.DateField(null=True, blank=True)
    instructors = models.ManyToManyField(Instructor, blank=True)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, through="Enrollment")
    total_enrollment = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class Lesson(models.Model):
    title = models.CharField(max_length=200, default="Lesson")
    order = models.PositiveIntegerField(default=0)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    content = models.TextField()

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.course.name}: {self.title}"


class Enrollment(models.Model):
    AUDIT = "audit"
    HONOR = "honor"
    BETA = "BETA"

    COURSE_MODES = [
        (AUDIT, "Audit"),
        (HONOR, "Honor"),
        (BETA, "BETA"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date_enrolled = models.DateField(default=now)
    mode = models.CharField(max_length=5, choices=COURSE_MODES, default=AUDIT)
    rating = models.FloatField(default=5.0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "course"],
                name="unique_user_course_enrollment",
            )
        ]

    def __str__(self):
        return f"{self.user.username} enrolled in {self.course.name}"


class Question(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    text = models.CharField(max_length=200, default="Question")
    grade = models.FloatField(default=0)

    def __str__(self):
        return self.text

    def is_get_score(self, selected):
        """Return True only when the exact set of correct choices was selected."""
        selected_ids = {
            item.pk if isinstance(item, Choice) else int(item)
            for item in selected
            if item is not None
        }
        correct_ids = set(
            self.choice_set.filter(is_correct=True).values_list("id", flat=True)
        )
        return bool(correct_ids) and selected_ids == correct_ids


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text = models.CharField(max_length=200, default="Choice")
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class Submission(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    choices = models.ManyToManyField(Choice)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Submission #{self.pk} by {self.enrollment.user.username}"
