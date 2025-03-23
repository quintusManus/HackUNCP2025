import os
import re
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI

# Load .env file
load_dotenv(dotenv_path=Path(".env"))

# Initialize OpenAI client with the API key from your .env file
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")


def strip_markdown_characters(text: str) -> str:
    """
    Removes common Markdown/code symbols that can appear as strange boxes
    or cause formatting issues.
    """
    text = text.replace("```", "")
    text = text.replace("**", "")
    text = text.replace("`", "")
    return text


def clean_questions(text: str) -> list:
    """
    Improved function to properly group questions with their answer choices.
    """
    lines = [line for line in text.split('\n') if line.strip() != '---']
    cleaned_text = '\n'.join(lines)
    questions = re.split(r'(?m)^\d+\.\s', cleaned_text)
    if questions and not questions[0].strip():
        questions = questions[1:]
    if len(questions) <= 1:
        return cleaned_text.split('\n\n')
    question_blocks = []
    question_number = 1
    for q in questions:
        q = q.strip()
        if q:
            block = f"{question_number}. {q}"
            question_blocks.append(block)
            question_number += 1
    return question_blocks


def call_chatgpt(prompt: str) -> str:
    """
    Calls the ChatGPT API and returns the cleaned text.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # or "gpt-4", "gpt-3.5-turbo", etc.
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        output = response.choices[0].message.content.strip()
        print("GPT Output (raw):\n", output)
        cleaned_output = strip_markdown_characters(output)
        print("GPT Output (cleaned):\n", cleaned_output)
        return cleaned_output
    except Exception as e:
        error_text = f"Error: {str(e)}"
        print("GPT Error:", error_text)
        return error_text


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        session["native_language"] = request.form["native_language"]
        session["target_language"] = request.form["target_language"]
        return redirect(url_for("prelim_test"))
    return render_template("index.html")


@app.route("/prelim_test", methods=["GET", "POST"])
def prelim_test():
    """
    Generate preliminary test questions entirely in the native language.
    """
    if request.method == "POST":
        session["prelim_answers"] = request.form.getlist("answer")
        prompt = f"""
You are a language teacher. The user's target language is {session['target_language']}, 
and their native language is {session['native_language']}.
Below are test questions (written in {session['native_language']}) and the user's answers. 
Assess their current language competency and write your analysis in {session['native_language']} only.

Questions:
{session['prelim_questions']}

Answers:
{session['prelim_answers']}
"""
        analysis = call_chatgpt(prompt)
        session["user_competency"] = analysis
        return redirect(url_for("next_lesson"))

    prompt = f"""
You are a language tutor. The user is a native speaker of {session['native_language']} 
learning {session['target_language']}. 
Create a short preliminary test entirely in {session['native_language']}.
It should have 3 to 5 multiple-choice questions about basic {session['target_language']} vocabulary and grammar.
IMPORTANT: Write all questions and answer choices in {session['native_language']}. 
For example, if the target language is English, the question might be:
"1. Was bedeutet 'cat' auf English?" 
with answer options in {session['native_language']}.
Return only the questions and answer choices in plain text.
"""
    prelim_questions = call_chatgpt(prompt)
    if not prelim_questions.strip() or "Error:" in prelim_questions:
        prelim_questions = f"""1. Wie sagt man 'hello' auf {session['target_language']}?
A) Option A
B) Option B
C) Option C"""
    session["prelim_questions"] = prelim_questions
    question_blocks = clean_questions(prelim_questions)
    return render_template("prelim_test.html", question_blocks=question_blocks)


@app.route("/vocab_lesson", methods=["GET", "POST"])
def vocab_lesson():
    """
    Generate a vocabulary lesson. Explanations are in the native language, but
    all vocabulary words and example sentences are in the target language.
    """
    if request.method == "POST":
        session["vocab_quiz_answers"] = request.form.getlist("answer")
        prompt = f"""
You are a language teacher. The user's target language is {session['target_language']} 
and their native language is {session['native_language']}.
Below is a vocabulary quiz (in {session['native_language']}) and the user's answers. 
Summarize their vocabulary strengths and weaknesses in {session['native_language']} only.

Questions:
{session.get('vocab_quiz_questions', '')}

Answers:
{session['vocab_quiz_answers']}
"""
        vocab_summary = call_chatgpt(prompt)
        session["vocab_summary"] = vocab_summary
        return redirect(url_for("grammar_lesson"))

    next_lesson_plan = session.get("next_lesson_plan", "")
    prompt_vocab = f"""
You are a language tutor. The user is a native {session['native_language']} speaker learning {session['target_language']}.
Their current competency is:
{session['user_competency']}

Next lesson plan (if any):
{next_lesson_plan}

Create a short vocabulary lesson in {session['native_language']} where the **instructions and explanations** are in {session['native_language']}, 
but all **vocabulary words and example sentences** are provided exclusively in {session['target_language']}.
Return only the vocabulary lesson text in plain text.
"""
    vocab_list = call_chatgpt(prompt_vocab)
    session["vocab_list"] = vocab_list

    prompt_quiz = f"""
Now create a vocabulary quiz in {session['native_language']}, based on the following vocabulary lesson.
IMPORTANT: Write all questions and answer choices in {session['native_language']}, but any vocabulary words or examples must be in {session['target_language']}.
Use the following format:
1. [Question text]
A) [Option A]
B) [Option B]
C) [Option C]
Limit to 10 questions maximum.

Vocabulary lesson:
{vocab_list}

Return only the questions and answer choices in plain text.
"""
    vocab_quiz_questions = call_chatgpt(prompt_quiz)
    session["vocab_quiz_questions"] = vocab_quiz_questions
    question_blocks = clean_questions(vocab_quiz_questions)
    return render_template("vocab_lesson.html", vocab_list=vocab_list, question_blocks=question_blocks)


@app.route("/grammar_lesson", methods=["GET", "POST"])
def grammar_lesson():
    """
    Generate a grammar lesson. Instructions are in the native language, but all examples and sample sentences are in the target language.
    """
    if request.method == "POST":
        session["grammar_quiz_answers"] = request.form.getlist("answer")
        prompt = f"""
You are a language teacher. The user's target language is {session['target_language']} 
and their native language is {session['native_language']}.
Below is a grammar quiz (in {session['native_language']}) and the user's answers. 
Summarize their strengths and weaknesses in {session['native_language']} only.

Questions:
{session.get('grammar_quiz_questions', '')}

Answers:
{session['grammar_quiz_answers']}
"""
        grammar_summary = call_chatgpt(prompt)
        session["grammar_summary"] = grammar_summary
        return redirect(url_for("overall_summary"))

    next_lesson_plan = session.get("next_lesson_plan", "")
    prompt_lesson = f"""
You are a language tutor. The user is a native {session['native_language']} speaker learning {session['target_language']}.
Current competency:
{session['user_competency']}

Next lesson plan:
{next_lesson_plan}

Write a short grammar lesson in {session['native_language']} with all general instructions and explanations in {session['native_language']}.
However, **all example sentences and grammatical examples must be in {session['target_language']} only.**
Return the grammar lesson text in plain text.
"""
    grammar_lesson_text = call_chatgpt(prompt_lesson)
    session["grammar_lesson"] = grammar_lesson_text

    prompt_quiz = f"""
Create a grammar quiz in {session['native_language']} based on the lesson below.

IMPORTANT FORMATTING INSTRUCTIONS:
1. Each question must include its answer choices immediately below it.
2. Format each question as: "1. [Question text]" followed by options on new lines.
3. Format answer choices as: "A) [Option A]", "B) [Option B]", etc.
4. Do NOT use dash separators (---).
5. Keep each question with its answers together as one unit.
6. Number questions sequentially (1, 2, 3...).
7. Limit to 5-7 questions maximum.
8. All content should be in {session['native_language']}, but any examples or sample sentences must be in {session['target_language']}.
    
Lesson:
{grammar_lesson_text}

Return only the questions and answer choices in plain text.
"""
    grammar_quiz_questions = call_chatgpt(prompt_quiz)
    session["grammar_quiz_questions"] = grammar_quiz_questions
    question_blocks = clean_questions(grammar_quiz_questions)
    return render_template("grammar_lesson.html", lesson=grammar_lesson_text, question_blocks=question_blocks)


@app.route("/overall_summary", methods=["GET"])
def overall_summary():
    """
    Summarize the user's overall competency in the native language,
    referencing the target language as needed.
    """
    prompt = f"""
You are a language teacher. Summarize the user's overall language competency in {session['native_language']} only, 
based on the following:

1. Preliminary competency:
{session['user_competency']}

2. Vocabulary summary:
{session.get('vocab_summary', '')}

3. Grammar summary:
{session.get('grammar_summary', '')}

Return the summary in plain text, in {session['native_language']} only.
"""
    overall = call_chatgpt(prompt)
    session["overall_summary"] = overall
    return render_template("overall_summary.html", overall=overall)


@app.route("/next_lesson", methods=["GET"])
def next_lesson():
    """
    Generate a next lesson plan in the native language,
    then redirect to the vocabulary lesson route.
    """
    overall_summary = session.get("overall_summary", "No summary available.")
    prompt = f"""
You are a language teacher. The user's native language is {session['native_language']}, 
and the target language is {session['target_language']}.
Here is their overall summary (in {session['native_language']}):
{overall_summary}

Generate a detailed next lesson plan in {session['native_language']} that specifically targets areas needing improvement. 
Use plain text only (no Markdown). 
Include lesson objectives, a brief review of weaknesses, and tailored exercises.
Return only the plan text in {session['native_language']}.
"""
    next_lesson_plan = call_chatgpt(prompt)
    session["next_lesson_plan"] = next_lesson_plan
    return redirect(url_for("vocab_lesson"))


if __name__ == "__main__":
    app.run(debug=True)