# mixins.py
from django.shortcuts import redirect
from django.urls import reverse
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.contrib.auth.views import redirect_to_login

from braces.views import LoginRequiredMixin

from lessons.models import Project
from .models import Whitelist


class WhitelistRequiredMixin(LoginRequiredMixin):
    """
    View mixin which verifies that the user is authenticated.
    NOTE:
        This should be the left-most mixin of a view, except when
        combined with CsrfExemptMixin - which in that case should
        be the left-most mixin.
    """
    def dispatch(self, request, *args, **kwargs):
        """Mixin that overrides braces LoginRequiredMixin to provide an
        optional login depending on visibility setting in project.
        """
        try:
            project = Project.objects.get(slug=kwargs.get('project_slug'))
        except ObjectDoesNotExist:
            project = Project.objects.get(slug=kwargs.get('slug'))

        #  Closed access - authentication required.
        if not project.public:
            if not request.user.is_authenticated():
                return redirect_to_login(request.get_full_path(),
                                            self.get_login_url(),
                                            self.get_redirect_field_name())
            else:  # Check project membership for user.
                if request.user.is_staff:
                    pass
                else:
                    whitelisting = request.user.whitelisting.get()
                    if not whitelisting.member_projects.filter(project=project):
                        return redirect(reverse('member_access_error'), permanent=True)  # return a membership access response

            return super(WhitelistRequiredMixin, self).dispatch(
                request, *args, **kwargs)

        # Authentication not required proceed with regular access.
        elif request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed
        return handler(request, *args, **kwargs)

class HonorCodeRequired(object):
    def dispatch(self, *args, **kwargs):
        activated = Whitelist.objects.get(email_addr=self.request.user.email).honor_agreement
        if not activated:
            return redirect('honor_agreement')
        return super(HonorCodeRequired, self).dispatch(*args, **kwargs)