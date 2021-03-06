from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericRelation
from django.utils.text import slugify

from model_utils.models import TimeStampedModel

from quiz.models import Quiz
from discussions.models import Post

CONTENT_TYPES = (
    ('topic', 'Topics'),
    ('media', 'Consider This'),
    ('reading', 'More To Consider'),
    ('quiz', 'Test Yourself'), 
    ('apply', 'Apply'),    
)

class Project(models.Model):
    title = models.CharField(max_length=512)
    description = models.TextField(blank=True)
    slug = models.SlugField(blank=True)
    public = models.BooleanField(default=False)

    def get_lessons(self):
        lessons = []
        modules = self.project_modules.all().order_by('order')
        for mod in modules:
            for lsnmod in mod.lessons.all().order_by('order'):
                lessons.append((mod, lsnmod.lesson))
        return lessons 

    def get_absolute_url(self):
        return reverse('project', args=[str(self.slug)])

    def __unicode__(self):
        return self.title


class Module(models.Model):
    title = models.CharField(max_length=512)
    description = models.TextField(blank=True)
    slug = models.SlugField(blank=True)
    order = models.IntegerField(default=0)
    project = models.ForeignKey(Project, related_name='project_modules', on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        self.slug = slugify(unicode(self.title))
        super(Module, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        try:
            lessons = self.lessons.all()
            for i in lessons:
                i.delete()
            
        except Exception as e:
            pass  # proceed silently
            
        super(Module, self).delete(*args, **kwargs) # Call the "real" delete() 

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('module', args=[self.project.slug, self.id])

    class Meta:
        ordering = ['order']


class Lesson(TimeStampedModel):
    title = models.CharField(max_length=512)
    description = models.TextField(blank=True)
    slug = models.SlugField(blank=True)
    # module = models.ForeignKey(Module, related_name='lessons')
    active = models.BooleanField(default=True)
    # order = models.IntegerField(default=0)
    creator = models.ForeignKey(User, null=True, on_delete=models.CASCADE)

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('lesson_permlink', args=[str(self.id)])

    def save(self, *args, **kwargs):
        self.slug = slugify(unicode(self.title))
        self.slug = self.slug[:49]
        super(Lesson, self).save(*args, **kwargs)

        if not self.sections.all():
            section = LessonSection(content_type='topic', lesson=self)
            section.save()
            section = LessonSection(content_type='media', lesson=self)
            section.save()
            section = LessonSection(content_type='reading', lesson=self)
            section.save()
            section = LessonSection(content_type='apply', lesson=self)
            section.save()

        if not self.lesson_discussion.all():
            try:
                user = self.creator
            except:
                user = User.objects.filter(is_superuser=True)[0]
            try:
                thread = Post(text="Start a discussion!", creator=user, subject=self.title+' Talk', parent_post=None)
                thread.save()
                discussion = LessonDiscussion(thread=thread, lesson=self)
                discussion.save()
            except:
                pass  # Fail silently...

        if not self.lesson_quiz.all():
            
            try:
                title = '%s Quiz'% (self.title)
                quiz = Quiz(title=title, url=title, random_order=False, answers_at_end=True)
                quiz.save()
                lesson_quiz = LessonQuiz(quiz=quiz, lesson=self)
                lesson_quiz.save()
            except Exception as e:
                pass  # Fail silently...

    def delete(self, *args, **kwargs):
        try:
            q = self.lesson_quiz.all().get()
            q.quiz.delete()
            d = self.lesson_discussion.all().get()
            d.thread.delete()
        except Exception as e:
            pass  # proceed silently
            
        super(Lesson, self).delete(*args, **kwargs) # Call the "real" delete() 


class LessonModule(models.Model):
    module = models.ForeignKey(Module, related_name='lessons', on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, related_name='modules', on_delete=models.CASCADE)
    order = models.IntegerField(default=0)

    class Meta:
        unique_together = (('module', 'lesson'),)
        ordering = ['order']
    

class LessonSection(models.Model):
    text = models.TextField(default='Coming soon...')
    content_type = models.CharField(max_length=64, choices=CONTENT_TYPES, default='text')
    lesson = models.ForeignKey(Lesson, related_name='sections', on_delete=models.CASCADE)
    
    def __unicode__(self):
        return '%s' % (self.content_type)

    def get_absolute_url(self):
        return reverse('lesson_section_permlink', args=[str(self.lesson.id), str(self.content_type)])


class LessonQuiz(models.Model):
    quiz = models.ForeignKey(Quiz, related_name='lesson', on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, related_name='lesson_quiz', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Lesson / Quiz Pair'

    # def delete(self, *args, **kwargs):
    #     try:
    #         self.quiz.delete()
    #         self.lesson.delete()
    #     except:
    #         pass  # proceed silently

    #     super(LessonQuiz, self).delete(*args, **kwargs) # Call the "real" delete() 
    
    def __unicode__(self):
        return '%s --> %s' % (self.lesson, self.quiz)


class LessonDiscussion(models.Model):
    thread = models.ForeignKey(Post, related_name='lesson_post', on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, related_name='lesson_discussion', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Lesson / Discussion Pair'
        unique_together = (('thread', 'lesson'),)

    def __unicode__(self):
        return '%s --> %s' % (self.lesson, self.thread)


class PbllPage(models.Model):
    title = models.CharField(max_length=512)
    content = models.TextField(blank=True)
    slug = models.SlugField(blank=True)

    def save(self, *args, **kwargs):
        self.slug = slugify(unicode(self.title))
        super(PbllPage, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('pbllpage', args=[str(self.slug)])
