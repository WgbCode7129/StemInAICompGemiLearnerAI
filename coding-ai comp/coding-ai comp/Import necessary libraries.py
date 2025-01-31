# Import necessary libraries
from flask import Flask, render_template, request, send_file, session
import google.generativeai as genai  # Google AI API
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import cv2
import pytesseract
import numpy as np
import textwrap
from IPython.display import Markdown

# Initialize Flask App
app = Flask(__name__)

# Set Google API Key
GOOGLE_API_KEY = "AIzaSyA3w-QUK96H-pN0Cd4vw3iG-qnFkkrJYWM"  # Replace with your actual Google AI API key
genai.configure(api_key=GOOGLE_API_KEY)

# Supported curriculums and age groups
CURRICULUMS = ["IGCSE", "CBSE", "IBDP"]
AGE_GROUPS = {"5-10": "Kids", "11-14": "Teens", "15-18": "Young Adults"}

### ---- Helper Functions ---- ###

def generate_learning_material(curriculum, topic, age_group):
    """
    Generate learning material using Google's AI API based on curriculum, topic, and age group.
    """
    prompt = f"""
    You are an expert teacher. Create a learning guide for the {curriculum} curriculum on the topic "{topic}" 
    for {AGE_GROUPS[age_group]} (age {age_group}). Provide:
    1. A short explanation of the topic.
    2. Examples to clarify concepts.
    3. Five questions for practice.
    """
    
    model = genai.GenerativeModel("tunedModels/copy-of-gemini2teacher-45xd061gda24")  # Use Google's generative model
    response = model.generate_content(prompt)
    return response.text  # Extract text response from Google AI API

def chat_with_bot(chat):
    model = genai.GenerativeModel("tunedModels/copy-of-gemini2teacher-45xd061gda24")  # Use Google's generative model
    response2 = model.generate_content(chat)
    formatted_text = response2.text.replace("**", " ")
    return formatted_text

def create_worksheet(content, topic):
    """
    Generate a printable worksheet as an image (can be saved as a PDF).
    """
    width, height = 1000, 1400
    image = Image.new('RGB', (width, height), "white")
    draw = ImageDraw.Draw(image)

    # Add title and instructions
    font = ImageFont.load_default()
    draw.text((50, 50), f"Worksheet: {topic}", fill="black", font=font)
    draw.text((50, 100), "Solve the questions below:", fill="black", font=font)

    # Add the content to the worksheet
    y_position = 150
    for line in content.split('\n'):
        draw.text((50, y_position), line, fill="black", font=font)
        y_position += 30

    # Save the worksheet as a file-like object
    buffer = BytesIO()
    image.save(buffer, format="PDF")
    buffer.seek(0)
    return buffer

def check_answers(image_file, correct_answers):
    """
    Use OCR to extract answers from the worksheet image and compare with correct answers.
    """
    img = cv2.imdecode(np.frombuffer(image_file.read(), np.uint8), cv2.IMREAD_COLOR)
    extracted_text = pytesseract.image_to_string(img)

    # Compare extracted answers with the correct ones
    extracted_answers = extracted_text.split('\n')
    feedback = []
    for i, (user_ans, correct_ans) in enumerate(zip(extracted_answers, correct_answers)):
        if user_ans.strip().lower() == correct_ans.strip().lower():
            feedback.append(f"Question {i+1}: Correct")
        else:
            feedback.append(f"Question {i+1}: Incorrect. Correct answer is: {correct_ans}")
    return feedback

def reteach_material(topic, mistakes):
    """
    Generate reteaching material tailored to mistakes using Google AI API.
    """
    prompt = f"""
    A student made the following mistakes in the topic "{topic}": {', '.join(mistakes)}.
    Create a short explanation to help them understand these mistakes better.
    """
    
    model = genai.GenerativeModel("gemini-pro")  # Google's AI model
    response = model.generate_content(prompt)
    return response.text  # Extract response text

### ---- Flask Routes ---- ###

@app.route('/')
def home():
    """
    Render the homepage with curriculum, age group, and topic selection.
    """
    return render_template("index.html", curriculums=CURRICULUMS, age_groups=AGE_GROUPS)

@app.route('/generate', methods=["POST"])
def generate():
    """
    Generate learning material and worksheet based on user input.
    """
    curriculum = request.form.get("curriculum")
    #chat = request.form.get("chat")
    topic = request.form.get("topic")
    age_group = request.form.get("age_group")
    
    #ai_response = request.form.get("ai_response")

    learning_material = generate_learning_material(curriculum, topic, age_group)
    worksheet = create_worksheet(learning_material, topic)

    # Store learning material in session for use in other routes (like feedback)
    session['learning_material'] = learning_material
    session['topic'] = topic
    #session['ai_response'] = ai_response


    #ai_response = chat_with_bot(chat)

    return send_file(worksheet, as_attachment=True, download_name=f"{topic}_worksheet.pdf")

@app.route('/response', methods=["POST"])
def generateresponse():
    """
    Generate learning material and worksheet based on user input.
    """
    chat = request.form.get("chat")
    ai_response = request.form.get("ai_response")
    session['ai_response'] = ai_response
    ai_response = chat_with_bot(chat)
    return render_template("index.html", curriculums=CURRICULUMS, age_groups=AGE_GROUPS, ai_response=ai_response)  # Pass AI response to the template

@app.route('/upload', methods=["POST"])
def upload():
    """
    Upload scanned worksheet and provide feedback.
    """
    file = request.files['worksheet']
    correct_answers = session.get('correct_answers', [])

    feedback = check_answers(file, correct_answers)

    mistakes = [fb for fb in feedback if "Incorrect" in fb]
    reteaching_material = reteach_material(session['topic'], mistakes)

    return render_template("feedback.html", feedback=feedback, reteaching_material=reteaching_material)

### ---- Run the App ---- ###

if __name__ == '__main__':
    app.secret_key = 'your_secret_key_here'  # Add a secret key for session management
    app.run(debug=True)
    
  