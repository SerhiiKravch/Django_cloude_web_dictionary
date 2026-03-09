mplemented a complete Django + SQLite dictionary site with the flow you requested.

What I built

Main page with:
Table of all words: English word, transcription, Ukrainian translation, context sentence
Django form input for unknown word
Logic:
If word exists in DB (case-insensitive), redirects to detail page
If not, calls OpenAI utility to generate translation/transcription/context/origin
If input is not a valid English word, shows notification
If generated successfully, saves to DB and opens detail page
Detail page with:
English word, transcription, translation, context sentence, origin
Back button to main page
SEO-friendly URL via slug: /word/<slug>/
Key files

Settings/URLs:
config/settings.py
config/urls.py
App logic:
dictionary/models.py
dictionary/forms.py
dictionary/utils.py
dictionary/views.py
dictionary/urls.py
dictionary/admin.py
dictionary/migrations/0001_initial.py
Templates:
templates/dictionary/base.html
templates/dictionary/word_list.html
templates/dictionary/word_detail.html
Dependencies:
requirements.txt
Validation

Ran migrations successfully (dictionary.0001_initial applied)
Ran Django checks: no issues
Run

pip install -r requirements.txt
Set OpenAI key: export OPENAI_API_KEY="your_key"
Optional model override: export OPENAI_MODEL="gpt-4.1-mini"
python3 manage.py runserver
