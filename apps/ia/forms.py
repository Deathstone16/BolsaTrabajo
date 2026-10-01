from django import forms


class PerfilCVForm(forms.Form):
    version = forms.IntegerField(widget=forms.HiddenInput)
    headline = forms.CharField(max_length=180, required=False, label='Título profesional')
    summary = forms.CharField(max_length=2000, required=False, widget=forms.Textarea(attrs={'rows': 5}), label='Resumen profesional')
    skills = forms.CharField(max_length=2000, required=False, label='Habilidades', help_text='Separalas con comas.')
    languages = forms.CharField(max_length=1000, required=False, label='Idiomas', help_text='Separalos con comas.')
    locations = forms.CharField(max_length=1000, required=False, label='Ubicaciones preferidas', help_text='Separalas con comas.')

    @classmethod
    def initial_from_profile(cls, profile):
        content = profile.contenido or {}
        return {
            'version': profile.version,
            'headline': content.get('headline') or '',
            'summary': content.get('summary') or '',
            'skills': ', '.join(item.get('name', '') for item in content.get('skills', [])),
            'languages': ', '.join(item.get('name', '') for item in content.get('languages', [])),
            'locations': ', '.join(content.get('preferences', {}).get('locations', [])),
        }

    def apply_to(self, content):
        result = dict(content)
        result['headline'] = self.cleaned_data['headline'] or None
        result['summary'] = self.cleaned_data['summary'] or None
        old_skills = {item.get('name', '').casefold(): item for item in result.get('skills', [])}
        result['skills'] = [old_skills.get(name.casefold(), {'name': name, 'level': 'unknown', 'evidence': []}) for name in self._csv('skills')]
        result['languages'] = [{'name': name, 'level': 'unknown'} for name in self._csv('languages')]
        preferences = dict(result.get('preferences') or {})
        preferences['locations'] = self._csv('locations')
        preferences.setdefault('work_modes', [])
        result['preferences'] = preferences
        return result

    def _csv(self, field):
        return list(dict.fromkeys(item.strip() for item in self.cleaned_data[field].split(',') if item.strip()))
