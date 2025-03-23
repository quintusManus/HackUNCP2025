# Language Learning App

## Project Overview
This is a language learning web application designed to help users improve their language skills through various lessons and quizzes. The application is built using Flask and includes templates for different types of lessons and quizzes.

## Project Structure
```
.env
app.py
requirements.txt
static/
    style.css
templates/
    grammar_lesson.html
    index.html
    layout.html
    next_lesson.html
    overall_summary.html
    prelim_test.html
    vocab_lesson.html
    vocab_quiz.html
```

### Files and Directories
- **.env**: Contains environment variables such as API keys and secret keys.
- **app.py**: The main Flask application file.
- **requirements.txt**: Lists the dependencies required for the project.
- **static/**: Contains static files like CSS.
- **templates/**: Contains HTML templates for different pages of the application.

## How to Run the Project
1. Clone the repository to your local machine.
2. Create a virtual environment and activate it:
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
3. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```
4. Set up environment variables by creating a `.env` file with the necessary keys.
5. Run the Flask application:
    ```sh
    flask run
    ```
6. Open your web browser and navigate to `http://127.0.0.1:5000` to access the application.

## Templates
- **index.html**: The home page where users can start the preliminary test.
- **layout.html**: The base layout template extended by other templates.
- **grammar_lesson.html**: Template for grammar lessons and quizzes.
- **vocab_lesson.html**: Template for vocabulary lessons and quizzes.
- **vocab_quiz.html**: Template for vocabulary quizzes.
- **overall_summary.html**: Displays the overall competency summary.
- **next_lesson.html**: Shows the next lesson plan.
- **prelim_test.html**: Template for the preliminary test.

## Static Files
- **style.css**: Contains the CSS styles for the application.

## Environment Variables
- **OPENAI_API_KEY**: API key for OpenAI.
- **FLASK_SECRET_KEY**: Secret key for Flask.
