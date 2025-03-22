import streamlit as st
import firebase_admin
from firebase_admin import credentials, db,firestore
import uuid
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import traceback
import os
import json
from dietchar import (
    generate_diet_plan, 
    calculate_calories, 
    calculate_protein, 
    calculate_carbs, 
    calculate_fats, 
    create_food_database, 
    generate_nutrition_tips, 
    display_diet_chart
)

# Set page config
st.set_page_config(
    page_title="Diet Recommendation App",
    page_icon="🥗",
    layout="wide"
)

# Initialize Firebase with Realtime Database (only do this once)
@st.cache_resource
# Initialize Firebase
def initialize_firebase():
    if not firebase_admin._apps:
        # Use direct file path for simplicity during development
        cred = credentials.Certificate('service.json')
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://diet-webapp-default-rtdb.firebaseio.com'
        })
    return db.reference()

# Get database reference
ref = initialize_firebase()

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 'survey'  # Default page
if 'user_data' not in st.session_state:
    st.session_state.user_data = None
if 'survey_id' not in st.session_state:
    st.session_state.survey_id = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Function to calculate BMI
def calculate_bmi(weight, height):
    # Height in meters (convert from cm)
    height_m = height / 100
    # BMI formula: weight (kg) / height^2 (m)
    bmi = weight / (height_m ** 2)
    return round(bmi, 2)

# Function to determine BMI category
def get_bmi_category(bmi):
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal weight"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obese"

# Function to save data to Firebase Realtime Database
def save_to_firebase(data):
    try:
        # Generate a unique ID for this submission
        doc_id = str(uuid.uuid4())
        # Add timestamp as string (Realtime DB doesn't handle datetime objects)
        data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Save to Realtime Database
        ref.child('diet_survey2').child(doc_id).set(data)
        return True, doc_id
    except Exception as e:
        return False, str(e)

# Authentication function for admin section
def authenticate():
    if not st.session_state.authenticated:
        st.title("Admin Dashboard")
        st.subheader("Login Required")
        password = st.text_input("Enter admin password", type="password")
        if st.button("Login"):
            # Replace with a proper authentication system in production
            if password == "admin123":  # Simple password for demo
                st.session_state.authenticated = True
                st.experimental_rerun()
            else:
                st.error("Incorrect password")
        return False
    return True

# Survey form function
def show_survey_form():
    st.title("🥗 Personalized Diet Recommendation Survey")
    st.write("Complete this survey to get a customized diet plan tailored to your needs and preferences.")
    
    # Create a form
    with st.form("diet_survey_form"):
        st.subheader("Personal Information")
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Full Name")
            age = st.number_input("Age", min_value=12, max_value=100, value=30)
            gender = st.selectbox("Gender", ["Male", "Female", "Non-binary", "Prefer not to say"])
            
        with col2:
            height = st.number_input("Height (cm)", min_value=100, max_value=250, value=170)
            weight = st.number_input("Weight (kg)", min_value=30, max_value=250, value=70)
            email = st.text_input("Email Address")
        
        # Calculate BMI immediately and show it
        if height and weight:
            bmi = calculate_bmi(weight, height)
            bmi_category = get_bmi_category(bmi)
            
            st.info(f"Your BMI: **{bmi}** - Category: **{bmi_category}**")
        
        st.subheader("Diet & Lifestyle")
        
        # Diet preferences
        diet_pref = st.radio("Diet Preference", 
                            ["Vegetarian", "Non-vegetarian", "Vegan", "Pescatarian", "Flexitarian"])
        
        # Food allergies or restrictions
        food_allergies = st.multiselect("Food Allergies or Restrictions (if any)",
                                       ["Nuts", "Dairy", "Gluten", "Seafood", "Eggs", "Soy", 
                                        "Lactose Intolerant", "None"])
        
        # Activity level
        activity_level = st.select_slider("Activity Level", 
                                         options=["Sedentary (office job, little exercise)", 
                                                 "Lightly active (light exercise 1-3 days/week)", 
                                                 "Moderately active (moderate exercise 3-5 days/week)", 
                                                 "Very active (hard exercise 6-7 days/week)", 
                                                 "Extremely active (physical job & hard exercise)"])
        
        # Fitness goals
        fitness_goal = st.selectbox("Fitness Goal", 
                                  ["Weight loss", "Muscle gain", "Maintenance", 
                                   "Improve overall health", "Athletic performance"])
        
        # Sleep pattern
        sleep_hours = st.slider("Average Sleep Duration (hours per day)", 4, 12, 7)
        
        # Work-life balance
        work_life = st.select_slider("How would you describe your work-life balance?",
                                   options=["Very stressful", "Somewhat stressful", 
                                           "Balanced", "Good balance", "Excellent balance"])
        
        # Lifestyle
        lifestyle = st.multiselect("Select aspects that describe your lifestyle",
                                 ["Long work hours", "Regular exercise", "Frequent travel", 
                                  "Work from home", "Student", "Parent/Caregiver", 
                                  "Social events with food/drink"])
        
        st.subheader("Meal Patterns & Budget")
        
        # Meals per day
        meals_per_day = st.slider("How many meals do you typically eat per day?", 1, 6, 3)
        
        # Snacking habits
        snacking = st.radio("Snacking habits", 
                          ["Rarely snack", "Occasional snacks", "Regular snacks between meals", 
                           "Frequent snacking throughout the day"])
        
        # Eating out frequency
        eating_out = st.select_slider("How often do you eat at restaurants or order takeout?",
                                    options=["Rarely (few times a month)", 
                                            "Occasionally (1-2 times a week)", 
                                            "Regularly (3-5 times a week)", 
                                            "Very frequently (almost daily)"])
        
        # Budget constraints
        budget_constraint = st.slider("What's your monthly budget for food? ($ per month)", 
                                    100, 1000, 300, step=50)
        
        # Cooking skills and time
        cooking_skill = st.select_slider("Cooking skills",
                                       options=["Beginner", "Can follow basic recipes", 
                                               "Intermediate", "Advanced"])
        
        cooking_time = st.slider("How much time can you spend cooking per day (minutes)?", 
                                15, 120, 30, step=15)
        
        # Additional information
        st.subheader("Additional Information")
        
        health_conditions = st.multiselect("Do you have any health conditions?",
                                         ["Diabetes", "Hypertension", "Heart disease", 
                                          "Digestive issues", "Food intolerances",
                                          "None"])
        
        additional_info = st.text_area("Any additional information you'd like to share")
        
        # Submit button
        submitted = st.form_submit_button("Submit Survey")
        
        if submitted:
            if not name or not email:
                st.error("Please provide your name and email to continue.")
            else:
                # Calculate nutritional needs
                calories = calculate_calories({
                    'weight': weight,
                    'height': height,
                    'age': age,
                    'gender': gender,
                    'activity_level': activity_level,
                    'fitness_goal': fitness_goal
                })
                
                protein = calculate_protein({
                    'weight': weight,
                    'fitness_goal': fitness_goal
                })
                
                carbs = calculate_carbs({
                    'calories': calories,
                    'fitness_goal': fitness_goal
                })
                
                fats = calculate_fats({
                    'calories': calories
                })
                
                # Generate food database based on diet preference and allergies
                food_db = create_food_database(diet_pref, food_allergies)
                
                # Create user_data dictionary for nutritional calculations
                user_data = {
                    'weight': weight,
                    'height': height,
                    'age': age,
                    'gender': gender,
                    'health_conditions': health_conditions,
                    'activity_level': activity_level,
                    'fitness_goal': fitness_goal,
                    'food_allergies': food_allergies,
                    'meals_per_day': meals_per_day,
                    'calories': calories,
                    'protein': protein,
                    'carbs': carbs,
                    'fats': fats,
                    'food_db': food_db,
                    'bmi_category': bmi_category
                }
                
                # Prepare data for Firebase
                survey_data = {
                    "name": name,
                    "email": email,
                    "age": age,
                    "gender": gender,
                    "height": height,
                    "weight": weight,
                    "bmi": bmi,
                    "bmi_category": bmi_category,
                    "diet_preference": diet_pref,
                    "food_allergies": food_allergies,
                    "activity_level": activity_level,
                    "fitness_goal": fitness_goal,
                    "sleep_hours": sleep_hours,
                    "work_life_balance": work_life,
                    "lifestyle": lifestyle,
                    "meals_per_day": meals_per_day,
                    "snacking_habits": snacking,
                    "eating_out_frequency": eating_out,
                    "budget_constraint": budget_constraint,
                    "cooking_skill": cooking_skill,
                    "cooking_time": cooking_time,
                    "health_conditions": health_conditions,
                    "additional_info": additional_info,
                    "calculated_calories": calories,
                    "calculated_protein": protein,
                    "calculated_carbs": carbs,
                    "calculated_fats": fats
                }
                
                # Save to Firebase
                success, result = save_to_firebase(survey_data)
                
                if success:
                    # Store user data in session state
                    st.session_state.user_data = user_data
                    st.session_state.survey_data = survey_data
                    st.session_state.survey_id = result
                    
                    # Generate the diet plan immediately after form submission
                    with st.spinner("Generating your personalized diet plan..."):
                        try:
                            diet_plan = generate_diet_plan(user_data)
                            nutrition_tips = generate_nutrition_tips(user_data)
                            
                            # Store diet plan in session state
                            st.session_state.diet_plan = diet_plan
                            st.session_state.nutrition_tips = nutrition_tips
                            
                            # Change page to diet plan - FIXED: Use experimental_rerun instead of rerun
                            st.session_state.page = 'diet_plan'
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error generating diet plan: {str(e)}")
                            st.code(traceback.format_exc())
                    
                else:
                    st.error(f"There was an error saving your data: {result}")

# Diet plan page function

def show_diet_plan():
    if st.session_state.user_data is None:
        st.error("No survey data found. Please complete the survey first.")
        if st.button("Go Back to Survey"):
            st.session_state.page = 'survey'
            st.experimental_rerun()
        return
    
    st.title("🍽️ Your Personalized Diet Plan")
    st.write(f"Welcome {st.session_state.survey_data.get('name', 'there')}! Here's your customized diet plan based on your survey responses.")
    
    # Display user stats
    st.subheader("Your Details")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("BMI", f"{st.session_state.survey_data.get('bmi', 'N/A')}", 
                 f"{st.session_state.survey_data.get('bmi_category', 'N/A')}")
    with col2:
        st.metric("Goal", f"{st.session_state.survey_data.get('fitness_goal', 'N/A')}")
    with col3:
        st.metric("Diet Preference", f"{st.session_state.survey_data.get('diet_preference', 'N/A')}")
    
    # Display nutritional needs
    st.subheader("Your Nutritional Needs")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Daily Calories", f"{st.session_state.survey_data.get('calculated_calories', 'N/A')} kcal")
    with col2:
        st.metric("Protein", f"{st.session_state.survey_data.get('calculated_protein', 'N/A')} g")
    with col3:
        st.metric("Carbohydrates", f"{st.session_state.survey_data.get('calculated_carbs', 'N/A')} g")
    with col4:
        st.metric("Fats", f"{st.session_state.survey_data.get('calculated_fats', 'N/A')} g")
    
    # Use pre-generated diet plan if available, otherwise generate it
    if hasattr(st.session_state, 'diet_plan') and st.session_state.diet_plan is not None:
        diet_plan = st.session_state.diet_plan
        nutrition_tips = st.session_state.nutrition_tips
    else:
        # Fallback in case diet plan isn't in session state
        with st.spinner("Generating your personalized diet plan..."):
            try:
                diet_plan = generate_diet_plan(st.session_state.user_data)
                nutrition_tips = generate_nutrition_tips(st.session_state.user_data)
            except Exception as e:
                st.error(f"Error generating diet plan: {str(e)}")
                diet_plan = None
                nutrition_tips = []
    
    # Display Diet Plan
    st.subheader("Your 7-Day Diet Plan")
    try:
        if diet_plan is not None:
            display_diet_chart(st.session_state.survey_data, diet_plan)
        else:
            st.warning("Unable to generate diet plan. Please try again.")
    except Exception as e:
        st.error(f"Error displaying diet chart: {str(e)}")
    
    # Display Nutrition Tips
    st.subheader("Nutrition Tips for You")
    for i, tip in enumerate(nutrition_tips, 1):
        st.markdown(f"**{i}.** {tip}")
    
    # Additional sections
    st.subheader("Shopping List")
    # Generate a shopping list based on the diet plan
    # This would be implemented in the dietchar module
    st.info("A shopping list feature is coming soon!")
    
    # Meal preparation tips
    st.subheader("Meal Prep Tips")
    if st.session_state.survey_data.get('cooking_time', 0) < 30:
        st.write("Since you have limited time for cooking, here are some time-saving meal prep tips:")
        st.markdown("""
        - Prep ingredients for multiple meals at once
        - Use a slow cooker or pressure cooker for hands-off cooking
        - Cook in batches and freeze extra portions
        - Keep pre-cut vegetables on hand for quick meals
        """)
    
    # Download options
    st.subheader("Download Your Plan")
    if st.button("Download Diet Plan as PDF"):
        st.info("PDF download feature is coming soon!")
    
    # Get email confirmation
    st.subheader("Email Your Plan")
    email = st.session_state.survey_data.get('email', '')
    if st.button(f"Email Diet Plan to {email}"):
        st.success(f"Your diet plan has been sent to {email}!")
    
    # Navigation buttons
    st.subheader("Want to make changes?")
    if st.button("Retake the Survey"):
        st.session_state.page = 'survey'
        st.experimental_rerun()

# Admin dashboard function
def show_admin_dashboard():
    st.title("📊 Diet Survey Admin Dashboard")
    
    # Sidebar for filtering
    st.sidebar.title("Filters")
    
    # Date range filter
    st.sidebar.subheader("Date Range")
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    date_range = st.sidebar.date_input(
        "Select date range",
        value=(start_date.date(), end_date.date())
    )
    
    # BMI category filter
    st.sidebar.subheader("BMI Category")
    bmi_categories = ["All", "Underweight", "Normal weight", "Overweight", "Obese"]
    selected_bmi = st.sidebar.multiselect("Select BMI categories", bmi_categories, default=["All"])
    
    # Diet preference filter
    st.sidebar.subheader("Diet Preference")
    diet_prefs = ["All", "Vegetarian", "Non-vegetarian", "Vegan", "Pescatarian", "Flexitarian"]
    selected_diet = st.sidebar.multiselect("Select diet preferences", diet_prefs, default=["All"])
    
    # Fitness goal filter
    st.sidebar.subheader("Fitness Goal")
    fitness_goals = ["All", "Weight loss", "Muscle gain", "Maintenance", "Improve overall health", "Athletic performance"]
    selected_goals = st.sidebar.multiselect("Select fitness goals", fitness_goals, default=["All"])
    
    # Fetch data from Firebase Realtime Database
    survey_data = []
    try:
        survey_ref = ref.child('diet_survey2').get()
        
        if survey_ref:
            for survey_id, data in survey_ref.items():
                # Convert timestamp string to datetime if it exists
                if 'timestamp' in data and isinstance(data['timestamp'], str):
                    data['date'] = datetime.strptime(data['timestamp'], "%Y-%m-%d %H:%M:%S").date()
                survey_data.append(data)
    except Exception as e:
        st.error(f"Error fetching data from Firebase: {str(e)}")
    
    if not survey_data:
        st.warning("No survey responses found in the database.")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(survey_data)
    
    # Apply filters
    if len(date_range) == 2 and 'date' in df.columns:
        start_date, end_date = date_range
        df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    
    if "All" not in selected_bmi and 'bmi_category' in df.columns:
        df = df[df['bmi_category'].isin(selected_bmi)]
    
    if "All" not in selected_diet and 'diet_preference' in df.columns:
        df = df[df['diet_preference'].isin(selected_diet)]
    
    if "All" not in selected_goals and 'fitness_goal' in df.columns:
        df = df[df['fitness_goal'].isin(selected_goals)]
    
    # Dashboard stats
    st.header("Survey Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Responses", len(df))
    with col2:
        avg_bmi = round(df['bmi'].mean(), 2) if 'bmi' in df.columns else "N/A"
        st.metric("Average BMI", avg_bmi)
    with col3:
        avg_age = round(df['age'].mean(), 1) if 'age' in df.columns else "N/A"
        st.metric("Average Age", avg_age)
    with col4:
        veg_percent = (df['diet_preference'] == 'Vegetarian').mean() * 100 if 'diet_preference' in df.columns else "N/A"
        st.metric("Vegetarian %", f"{round(veg_percent, 1)}%")
    
    # Data visualizations
    st.header("Data Visualizations")
    
    # BMI distribution
    if 'bmi_category' in df.columns:
        st.subheader("BMI Category Distribution")
        bmi_counts = df['bmi_category'].value_counts().reset_index()
        bmi_counts.columns = ['BMI Category', 'Count']
        fig = px.pie(bmi_counts, values='Count', names='BMI Category', 
                    title='Distribution of BMI Categories')
        st.plotly_chart(fig)
    
    # Diet preferences
    if 'diet_preference' in df.columns:
        st.subheader("Diet Preferences")
        diet_counts = df['diet_preference'].value_counts().reset_index()
        diet_counts.columns = ['Diet Preference', 'Count']
        fig = px.bar(diet_counts, x='Diet Preference', y='Count',
                    title='Distribution of Diet Preferences')
        st.plotly_chart(fig)
    
    # Fitness goals
    if 'fitness_goal' in df.columns:
        st.subheader("Fitness Goals")
        goal_counts = df['fitness_goal'].value_counts().reset_index()
        goal_counts.columns = ['Fitness Goal', 'Count']
        fig = px.bar(goal_counts, x='Fitness Goal', y='Count',
                    title='Distribution of Fitness Goals')
        st.plotly_chart(fig)
    
    # Age vs BMI scatter plot
    if 'age' in df.columns and 'bmi' in df.columns:
        st.subheader("Age vs BMI")
        fig = px.scatter(df, x='age', y='bmi', color='gender' if 'gender' in df.columns else None,
                        title='Age vs BMI', labels={'age': 'Age', 'bmi': 'BMI'})
        st.plotly_chart(fig)
    
    # Survey responses table
    st.header("Survey Responses")
    if st.checkbox("Show raw data"):
        st.dataframe(df)

# Main function to control the app flow
def main():
    # Add a navigation option in the sidebar
    st.sidebar.title("Navigation")
    app_mode = st.sidebar.radio("Go to", ["Survey Form", "Diet Plan", "Admin Dashboard"])
    
    # Update page based on sidebar selection
    if app_mode == "Survey Form":
        st.session_state.page = 'survey'
    elif app_mode == "Diet Plan" and st.session_state.user_data is not None:
        st.session_state.page = 'diet_plan'
    elif app_mode == "Admin Dashboard":
        st.session_state.page = 'admin'
    
    # Display the appropriate page
    if st.session_state.page == 'survey':
        show_survey_form()
    elif st.session_state.page == 'diet_plan':
        show_diet_plan()
    elif st.session_state.page == 'admin':
        if authenticate():
            show_admin_dashboard()

# Run the app
if __name__ == "__main__":
    main()