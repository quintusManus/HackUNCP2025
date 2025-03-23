import os
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI

# Load .env file
load_dotenv(dotenv_path=Path(".env"))

# Initialize the OpenAI client with the API key from your .env file.
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")


def call_chatgpt(prompt):
    """
    Calls the ChatGPT API with the provided prompt using the correct interface,
    and returns the generated text.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        output = response.choices[0].message.content.strip()
        print("GPT Output:\n", output)  # Debug output
        return output
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
    if request.method == "POST":
        session["prelim_answers"] = request.form.getlist("answer")
        # Assess the user's performance on the preliminary test.
        prompt = f"""You are a language teacher. The user's target language is {session['target_language']} and their native language is {session['native_language']}.
Based on the following questions and the user's answers, please assess their current language competency.

Questions:
{session['prelim_questions']}

Answers:
{session['prelim_answers']}"""
        analysis = call_chatgpt(prompt)
        session["user_competency"] = analysis
        return redirect(url_for("next_lesson"))

    # Generate preliminary test questions (GET request)
    prompt = f"""
You are a language tutor. Please generate a preliminary test for a beginner learning {session['target_language']} whose native language is {session['native_language']}.
The test should include 3 to 5 multiple choice questions covering basic vocabulary, reading comprehension, and grammar.
Each question should be formatted as a separate block (separated by a blank line) in the following format:

1. [Question text]
a) [Option A]
b) [Option B]
c) [Option C]

Return only the questions and answer choices.
"""
    prelim_questions = call_chatgpt(prompt)
    print("Prelim Questions Raw:\n", prelim_questions)
    if not prelim_questions.strip() or "Error:" in prelim_questions:
        prelim_questions = """1. What does 'hello' mean in your target language?
a) Option A
b) Option B
c) Option C"""
    session["prelim_questions"] = prelim_questions
    question_blocks = prelim_questions.split("\n\n")
    return render_template("prelim_test.html", question_blocks=question_blocks)


@app.route("/vocab_lesson", methods=["GET", "POST"])
def vocab_lesson():
    if request.method == "POST":
        session["vocab_quiz_answers"] = request.form.getlist("answer")
        # Assess vocabulary performance.
        prompt = f"""You are a language teacher. The user's target language is {session['target_language']} and their native language is {session['native_language']}.
Based on the following vocabulary quiz questions and the user's answers, summarize their vocabulary strengths and weaknesses.

Questions:
{session.get('vocab_quiz_questions', '')}

Answers:
{session['vocab_quiz_answers']}"""
        vocab_summary = call_chatgpt(prompt)
        session["vocab_summary"] = vocab_summary
        return redirect(url_for("grammar_lesson"))

    # Incorporate the next lesson plan into the vocab lesson prompt if available.
    next_lesson_plan = session.get("next_lesson_plan", "")
    prompt_vocab = f"""Based on this language competency level in {session['target_language']}:
{session['user_competency']}

And considering the following next lesson plan:
{next_lesson_plan}

Generate a vocabulary list with translations that the student should study to improve their skills."""
    vocab_list = call_chatgpt(prompt_vocab)
    session["vocab_list"] = vocab_list

    prompt_quiz = f"""Create a vocabulary quiz in {session['target_language']} using the following vocabulary list.
Only output the questions and answer choices.

{vocab_list}"""
    vocab_quiz_questions = call_chatgpt(prompt_quiz)
    session["vocab_quiz_questions"] = vocab_quiz_questions

    question_blocks = vocab_quiz_questions.split("\n\n")
    return render_template("vocab_lesson.html", vocab_list=vocab_list, question_blocks=question_blocks)


@app.route("/grammar_lesson", methods=["GET", "POST"])
def grammar_lesson():
    if request.method == "POST":
        session["grammar_quiz_answers"] = request.form.getlist("answer")
        prompt = f"""You are a language teacher. The user's target language is {session['target_language']} and their native language is {session['native_language']}.
Review the following grammar quiz questions and the user's answers, and summarize their strengths and areas for improvement.

Questions:
{session.get('grammar_quiz_questions', '')}

Answers:
{session['grammar_quiz_answers']}"""
        grammar_summary = call_chatgpt(prompt)
        session["grammar_summary"] = grammar_summary
        return redirect(url_for("overall_summary"))

    # Incorporate the next lesson plan into the grammar lesson prompt if available.
    next_lesson_plan = session.get("next_lesson_plan", "")
    prompt_lesson = f"""Based on the user's language competency in {session['target_language']}:
{session['user_competency']}

And considering the following next lesson plan:
{next_lesson_plan}

Generate a short, easy-to-understand grammar lesson."""
    grammar_lesson_text = call_chatgpt(prompt_lesson)
    session["grammar_lesson"] = grammar_lesson_text

    prompt_quiz = f"""Create a grammar quiz (with numbered questions only) based on the following lesson.
Only output the questions and answer choices.

{grammar_lesson_text}"""
    grammar_quiz_questions = call_chatgpt(prompt_quiz)
    session["grammar_quiz_questions"] = grammar_quiz_questions

    question_blocks = grammar_quiz_questions.split("\n\n")
    return render_template("grammar_lesson.html", lesson=grammar_lesson_text, question_blocks=question_blocks)


@app.route("/overall_summary", methods=["GET"])
def overall_summary():
    prompt = f"""Summarize the user's overall language competency in {session['target_language']} based on the following:

1. Initial competency assessment:
{session['user_competency']}

2. Vocabulary summary:
{session['vocab_summary']}

3. Grammar summary:
{session['grammar_summary']}"""
    overall = call_chatgpt(prompt)
    session["overall_summary"] = overall
    return render_template("overall_summary.html", overall=overall)


# Next Lesson route: Generate a next lesson plan based on the overall summary,
# but do not display it. Instead, store it and then redirect to the vocab lesson.
@app.route("/next_lesson", methods=["GET"])
def next_lesson():
    overall_summary = session.get("overall_summary", "No summary available.")
    prompt = f"""
You are a language teacher. Based on the following overall competency summary for the student:
{overall_summary}

Generate a detailed next lesson plan that specifically targets the areas needing improvement.
The lesson plan should include:
- Lesson objectives
- A brief review of the areas of weakness
- Tailored exercises (e.g., grammar, vocabulary, or comprehension tasks)
Return only the lesson plan text.
"""
    next_lesson_plan = call_chatgpt(prompt)
    session["next_lesson_plan"] = next_lesson_plan
    # Instead of showing the lesson plan, redirect to the vocabulary lesson for the next cycle.
    return redirect(url_for("vocab_lesson"))


if __name__ == "__main__":
    app.run(debug=True)