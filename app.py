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


def clean_questions(text):
    """
    Improved function to properly group questions with their answer choices.
    Ensures each question block contains both the question and all its answer options.
    """
    # Remove lines that only contain dashes
    lines = [line for line in text.split('\n') if line.strip() != '---']
    
    # Clean text and prepare for processing
    cleaned_text = '\n'.join(lines)
    
    # Use regex to find question patterns (number followed by text)
    import re
    
    # Look for numbered questions (1., 2., etc.) or questions with asterisks (**1.**)
    questions = re.split(r'\n\s*(?:\d+\.|\*\*\d+\.\*\*|\*\*\d+\*\*|\(\d+\))', cleaned_text)
    
    # Remove the first empty element if it exists
    if questions and not questions[0].strip():
        questions = questions[1:]
    
    # If we couldn't split by question numbers, try splitting by double newlines
    if len(questions) <= 1:
        return cleaned_text.split('\n\n')
    
    # Rebuild properly formatted question blocks
    question_blocks = []
    question_number = 1
    
    for q in questions:
        if q.strip():
            # Clean up any asterisks from markdown formatting
            q = re.sub(r'\*\*', '', q)
            # Ensure the question has its number
            formatted_q = f"{question_number}. {q.strip()}"
            question_blocks.append(formatted_q)
            question_number += 1
    
    return question_blocks


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

IMPORTANT FORMATTING INSTRUCTIONS:
1. Each question must include its answer choices immediately below it
2. Format each question as: "1. [Question text]" followed by options on new lines
3. Format answer choices as: "A) [Option A]", "B) [Option B]", etc.
4. Do NOT use dash separators (---) between questions
5. Keep each question with its answers together as one unit
6. Number questions sequentially (1, 2, 3...)

Example format:
1. What is the word for "hello"?
A) Word1
B) Word2
C) Word3

2. Which sentence is correct?
A) Sentence 1
B) Sentence 2
C) Sentence 3

Return only the questions and answer choices following this exact format.
"""
    prelim_questions = call_chatgpt(prompt)
    print("Prelim Questions Raw:\n", prelim_questions)
    if not prelim_questions.strip() or "Error:" in prelim_questions:
        prelim_questions = """1. What does 'hello' mean in your target language?
a) Option A
b) Option B
c) Option C"""
    
    session["prelim_questions"] = prelim_questions
    question_blocks = clean_questions(prelim_questions)
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

IMPORTANT FORMATTING INSTRUCTIONS:
1. Each question must include its answer choices immediately below it
2. Format each question as: "1. [Question text]" followed by options on new lines
3. Format answer choices as: "A) [Option A]", "B) [Option B]", etc.
4. Do NOT use dash separators (---) between questions
5. Keep each question with its answers together as one unit
6. Number questions sequentially (1, 2, 3...)
7. Limit to 10 questions maximum

Example format:
1. What is the word for "hello"?
A) Word1
B) Word2
C) Word3

2. Which sentence is correct?
A) Sentence 1
B) Sentence 2
C) Sentence 3

Vocabulary list:
{vocab_list}

Return only the questions and answer choices following this exact format.
"""
    vocab_quiz_questions = call_chatgpt(prompt_quiz)
    session["vocab_quiz_questions"] = vocab_quiz_questions

    question_blocks = clean_questions(vocab_quiz_questions)
    return render_template("vocab_lesson.html", vocab_list=vocab_list, question_blocks=question_blocks)


def format_grammar_lesson(text):
    """
    Formats a grammar lesson text with proper HTML structure and styling classes.
    """
    import re
    
    # Add basic HTML structure
    formatted_text = text
    
    # Clean up the text first to remove any problematic patterns
    formatted_text = formatted_text.replace('###', '').replace('####', '')
    
    # Create a proper lesson title
    title_match = re.search(r'^(.+?)(?:\n|$)', formatted_text)
    if title_match:
        title = title_match.group(1).strip()
        formatted_text = re.sub(r'^.+?(?:\n|$)', f'<h3>{title}</h3>\n', formatted_text)
    
    # Format section headers (numbered sections like "1. Sentence Structure:")
    formatted_text = re.sub(r'(\d+\.\s+)([^:\n]+):', r'<h3>\1\2</h3>', formatted_text)
    
    # Format lesson objective
    objective_match = re.search(r'Lesson Objective:(.*?)(?=\d+\.|$)', formatted_text, re.DOTALL)
    if objective_match:
        objective = objective_match.group(1).strip()
        formatted_text = re.sub(r'Lesson Objective:.*?(?=\d+\.|$)', 
                              f'<div class="grammar-rule">Lesson Objective: {objective}</div>\n', 
                              formatted_text, 
                              flags=re.DOTALL)
    
    # Format examples
    formatted_text = re.sub(r'Example[s]?:(.*?)(?=\d+\.|Practice|Exercise|Conclusion|$)', 
                           r'<div class="example"><strong>Examples:</strong>\1</div>', 
                           formatted_text, 
                           flags=re.DOTALL)
    
    # Format practice sentences
    practice_pattern = r'Practice Sentences:(.*?)(?=\d+\.|Exercise|Conclusion|$)'
    practice_match = re.search(practice_pattern, formatted_text, re.DOTALL)
    if practice_match:
        practice_content = practice_match.group(1).strip()
        formatted_text = re.sub(practice_pattern, 
                             f'<div class="practice-exercises"><h3>Practice Sentences</h3>{practice_content}</div>\n', 
                             formatted_text, 
                             flags=re.DOTALL)
    
    # Format exercises
    exercise_pattern = r'Exercise:(.*?)(?=\d+\.|Conclusion|$)'
    exercise_match = re.search(exercise_pattern, formatted_text, re.DOTALL)
    if exercise_match:
        exercise_content = exercise_match.group(1).strip()
        formatted_text = re.sub(exercise_pattern, 
                             f'<div class="practice-exercises"><h3>Exercises</h3>{exercise_content}</div>\n', 
                             formatted_text, 
                             flags=re.DOTALL)
    
    # Format conclusion
    conclusion_pattern = r'Conclusion:(.*?)$'
    conclusion_match = re.search(conclusion_pattern, formatted_text, re.DOTALL)
    if conclusion_match:
        conclusion_content = conclusion_match.group(1).strip()
        formatted_text = re.sub(conclusion_pattern, 
                             f'<div class="grammar-note"><strong>Conclusion:</strong>{conclusion_content}</div>', 
                             formatted_text, 
                             flags=re.DOTALL)
    
    # Format breakdown sections
    formatted_text = re.sub(r'Breakdown:(.*?)(?=\d+\.|Practice|Exercise|Conclusion|$)', 
                          r'<div class="grammar-section"><strong>Breakdown:</strong>\1</div>', 
                          formatted_text, 
                          flags=re.DOTALL)
    
    # Format vocabulary sections
    vocab_pattern = r'Common Vocabulary:(.*?)(?=\d+\.|Practice|Exercise|Conclusion|$)'
    vocab_match = re.search(vocab_pattern, formatted_text, re.DOTALL)
    if vocab_match:
        vocab_content = vocab_match.group(1).strip()
        formatted_text = re.sub(vocab_pattern, 
                             f'<div class="grammar-section"><h3>Common Vocabulary</h3>{vocab_content}</div>\n', 
                             formatted_text, 
                             flags=re.DOTALL)
    
    # Format Arabic terms with highlighting
    formatted_text = re.sub(r'\*\*([\u0600-\u06FF\s\(\)\'\.]+)\*\*', r'<span class="grammar-highlight">\1</span>', formatted_text)
    
    # Handle bullet points
    formatted_text = re.sub(r'^\s*-\s+(.*?)$', r'<li>\1</li>', formatted_text, flags=re.MULTILINE)
    formatted_text = re.sub(r'(?:<li>.*?</li>\s*)+', r'<ul>\g<0></ul>', formatted_text)
    
    # Clean up any remaining Markdown formatting
    formatted_text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', formatted_text)
    
    # Final cleanup
    formatted_text = formatted_text.replace('\n\n', '<br>')
    formatted_text = formatted_text.replace('\n', ' ')
    
    # Remove any <br> tags that appear right before a closing div
    formatted_text = re.sub(r'<br>\s*</div>', '</div>', formatted_text)
    
    # Final cleanup
    formatted_text = re.sub(r'<br>\s*<h3>', '<h3>', formatted_text)
    formatted_text = re.sub(r'</h3>\s*<br>', '</h3>', formatted_text)
    
    return formatted_text

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

Generate a short, easy-to-understand grammar lesson. Format the lesson with the following structure:
- A clear lesson title (prefixed with "###")
- Lesson objective (prefixed with "#### Lesson Objective:")
- 2-4 numbered sections (prefixed with "#### 1.", "#### 2.", etc.)
- Examples with Arabic text and English translations
- Practice sentences
- A brief exercise
- A conclusion

Use Markdown formatting: "**bold**" for important terms and Arabic words.
"""
    grammar_lesson_text = call_chatgpt(prompt_lesson)
    
    # Format the grammar lesson with HTML and CSS classes
    formatted_lesson = format_grammar_lesson(grammar_lesson_text)
    
    session["grammar_lesson"] = grammar_lesson_text  # Store original text
    
    prompt_quiz = f"""Create a grammar quiz based on the following lesson.

IMPORTANT FORMATTING INSTRUCTIONS:
1. Each question must include its answer choices immediately below it
2. Format each question as: "1. [Question text]" followed by options on new lines
3. Format answer choices as: "A) [Option A]", "B) [Option B]", etc.
4. Do NOT use dash separators (---) between questions
5. Keep each question with its answers together as one unit
6. Number questions sequentially (1, 2, 3...)
7. Limit to 5-7 questions maximum

Example format:
1. What is the correct verb form?
A) Option1
B) Option2
C) Option3

2. Which sentence uses the grammar rule correctly?
A) Sentence 1
B) Sentence 2
C) Sentence 3

Grammar lesson:
{grammar_lesson_text}

Return only the questions and answer choices following this exact format.
"""
    grammar_quiz_questions = call_chatgpt(prompt_quiz)
    session["grammar_quiz_questions"] = grammar_quiz_questions

    question_blocks = clean_questions(grammar_quiz_questions)
    return render_template("grammar_lesson.html", lesson=formatted_lesson, question_blocks=question_blocks)


@app.route('/overall_summary')
def overall_summary():
    # Fix for KeyError: 'vocab_summary'
    vocab_summary = session.get('vocab_summary', 'No vocabulary summary available yet.')
    grammar_summary = session.get('grammar_summary', 'No grammar summary available yet.')
    quiz_results = session.get('quiz_results', 'No quiz results available yet.')
    
    return render_template('overall_summary.html', 
                          vocab_summary=vocab_summary,
                          grammar_summary=grammar_summary,
                          quiz_results=quiz_results)


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