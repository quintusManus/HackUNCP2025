import os
import openai
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a secure key

# Make sure to set the OPENAI_API_KEY environment variable before running
openai.api_key = os.getenv("OPENAI_API_KEY")

def call_chatgpt(prompt):
    """
    Calls the ChatGPT API with the provided prompt and returns the generated text.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Landing page: collects the user’s native language, target language,
    and a sample of what they would like to say.
    """
    if request.method == 'POST':
        session['native_language'] = request.form['native_language']
        session['target_language'] = request.form['target_language']
        session['user_speech'] = request.form['user_speech']
        return redirect(url_for('prelim_test'))
    return render_template('index.html')

@app.route('/prelim_test', methods=['GET', 'POST'])
def prelim_test():
    """
    Preliminary test:
    - GET: Generate test questions using ChatGPT.
    - POST: Receive user answers and generate a competency analysis.
    """
    if request.method == 'POST':
        # Capture the user's answers from the preliminary test
        session['prelim_answers'] = request.form.getlist('answer')
        session['prelim_questions'] = session.get('prelim_questions', '')
        # Generate competency analysis based on the questions and answers
        prompt = f"""You are a language teacher. The user’s target language is {session['target_language']} and their native language is {session['native_language']}.
Based on the following questions and answers from a language test, provide a comprehensive analysis of their level of competency in the target language.

Questions:
{session['prelim_questions']}

Answers:
{session['prelim_answers']}

Return user_language_competency = [AI generated competency description]"""
        analysis = call_chatgpt(prompt)
        session['user_competency'] = analysis
        return redirect(url_for('vocab_quiz'))
    else:
        # Generate preliminary test questions based on the user's speech and target language.
        prompt = f"""Preliminary test method:
The user speaks: "{session.get('user_speech', '')}" and their target language is {session['target_language']}.
Generate a language comprehension test based on this. Only respond with the questions you’ve made.
Prelim_test_questions = [AI generated questions]"""
        prelim_questions = call_chatgpt(prompt)
        session['prelim_questions'] = prelim_questions
        return render_template('prelim_test.html', questions=prelim_questions)

@app.route('/vocab_quiz', methods=['GET', 'POST'])
def vocab_quiz():
    """
    Vocabulary section:
    - GET: Generate a vocabulary list (with translations) based on the user’s competency,
           then generate a quiz using that vocab.
    - POST: Receive the user's quiz answers and generate a vocab summary.
    """
    if request.method == 'POST':
        # Process the user's vocabulary quiz answers
        session['vocab_quiz_answers'] = request.form.getlist('answer')
        prompt = f"""You are a language teacher. The user’s target language is {session['target_language']} and their native language is {session['native_language']}.
Based on the following vocab quiz questions and user answers, generate a summary of what they need to work on and what they did well with vocabulary.

Questions:
{session.get('vocab_quiz_questions', '')}

Answers:
{session['vocab_quiz_answers']}

Vocab_summary = [AI summary of what the user did good and bad in the vocab section]"""
        vocab_summary = call_chatgpt(prompt)
        session['vocab_summary'] = vocab_summary
        return redirect(url_for('grammar_lesson'))
    else:
        # Generate the vocab list and then the vocabulary quiz questions
        prompt_vocab = f"""You are a language teacher. The user’s target language is {session['target_language']} and their native language is {session['native_language']}.
Based on the language learner’s level:
{session['user_competency']}

Generate vocabulary in the target language along with translations for learning purposes.
Vocab = [AI generated vocab list with translations in their target language]"""
        vocab_list = call_chatgpt(prompt_vocab)
        session['vocab_list'] = vocab_list

        prompt_quiz = f"""Based on the following vocabulary list, generate a quiz with only the vocab in {session['target_language']}. Say nothing else.
Vocab_quiz_questions = [AI generated questions]

Vocabulary list:
{vocab_list}"""
        vocab_quiz_questions = call_chatgpt(prompt_quiz)
        session['vocab_quiz_questions'] = vocab_quiz_questions
        return render_template('vocab_quiz.html', questions=vocab_quiz_questions)

@app.route('/grammar_lesson', methods=['GET', 'POST'])
def grammar_lesson():
    """
    Grammar section:
    - GET: Generate a short grammar lesson and corresponding quiz questions.
    - POST: Receive grammar quiz answers and generate a summary.
    """
    if request.method == 'POST':
        session['grammar_quiz_answers'] = request.form.getlist('answer')
        prompt = f"""You are a language teacher. The user’s target language is {session['target_language']} and their native language is {session['native_language']}.
Based on the following grammar quiz questions and user answers, generate a summary of what they need to work on and what they did well in grammar.

Questions:
{session.get('grammar_quiz_questions', '')}

Answers:
{session['grammar_quiz_answers']}

grammar_summary = [AI summary of what the user did good and bad in the grammar section]"""
        grammar_summary = call_chatgpt(prompt)
        session['grammar_summary'] = grammar_summary
        return redirect(url_for('overall_summary'))
    else:
        prompt_lesson = f"""You are a language teacher. The user’s target language is {session['target_language']} and their native language is {session['native_language']}.
Based on the language learner’s level:
{session['user_competency']}

Generate a short grammar lesson that the user can understand.
grammar_lesson = [AI generated grammar lesson]"""
        grammar_lesson_text = call_chatgpt(prompt_lesson)
        session['grammar_lesson'] = grammar_lesson_text

        prompt_quiz = f"""Based on the following grammar lesson, generate a grammar quiz for the user numbered for the questions. Only generate the questions.
lesson:
{grammar_lesson_text}

grammar_quiz_questions = [AI generated questions]"""
        grammar_quiz_questions = call_chatgpt(prompt_quiz)
        session['grammar_quiz_questions'] = grammar_quiz_questions
        return render_template('grammar_lesson.html', lesson=grammar_lesson_text, quiz_questions=grammar_quiz_questions)

@app.route('/overall_summary', methods=['GET'])
def overall_summary():
    """
    Overall summary:
    Generate an overall competency analysis using the preliminary test, vocabulary summary,
    and grammar summary.
    """
    prompt = f"""You are a language teacher. The user’s target language is {session['target_language']} and their native language is {session['native_language']}.
Based on the user’s previously recorded competency in the language, and summaries of their grammar and vocabulary, generate a new detailed analysis of their competency in the target language.

Previously recorded competency:
{session['user_competency']}

Vocabulary summary:
{session['vocab_summary']}

Grammar summary:
{session['grammar_summary']}

User_language_competency = [AI generated text based on the above summaries]"""
    overall = call_chatgpt(prompt)
    session['overall_summary'] = overall
    return render_template('overall_summary.html', overall=overall)

@app.route('/next_lesson', methods=['GET'])
def next_lesson():
    """
    Starts the next lesson.
    For subsequent lessons, skip the preliminary test and start with the vocabulary and grammar sections.
    """
    return redirect(url_for('vocab_quiz'))

if __name__ == '__main__':
    app.run(debug=True)
