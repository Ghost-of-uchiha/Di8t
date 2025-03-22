import streamlit as st
st.set_page_config(
    page_title="Diet Recommendation App",
    page_icon="🥗",
    layout="wide"
)

import pyrebase
import time
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
import pandas as pd
from datetime import datetime, timedelta
import os
import json
import requests
import traceback
import threading

# Import custom modules: dietchart, recipe, Model_Beta and incri_budget
import dietchar
import recipe
import Model_Beta as mod
import incri_budget

# ===== Monkey-patch st.plotly_chart to assign a unique key automatically =====
original_plotly_chart = st.plotly_chart
def unique_plotly_chart(fig, **kwargs):
    if 'key' not in kwargs:
        kwargs['key'] = "plotly_chart_" + str(uuid.uuid4())
    return original_plotly_chart(fig, **kwargs)
st.plotly_chart = unique_plotly_chart
# ===========================================================================

# Firebase configuration for authentication
firebase_config = {
    'apiKey': st.secrets["firebase"]["apiKey"],
    'authDomain': st.secrets["firebase"]["authDomain"],
    'projectId': st.secrets["firebase"]["projectId"],
    'storageBucket': st.secrets["firebase"]["storageBucket"],
    'messagingSenderId': st.secrets["firebase"]["messagingSenderId"],
    'appId': st.secrets["firebase"]["appId"],
    'databaseURL': st.secrets["firebase"]["databaseURL"],
}

# ------------------------------------ Recipe Recommendation Functions ------------------------------------
def recipy_recommend(_email, content_i, content_r):
    # Initialize Firebase Admin (if needed)
    def initialize_firebase():
        try:
            if not firebase_admin._apps:
                if os.path.exists("serviceAccountKey.json"):
                    cred = credentials.Certificate("serviceAccountKey.json")
                    firebase_admin.initialize_app(cred)
                    st.sidebar.success("Firebase connection successful (local)")
                else:
                    try:
                        key_dict = json.loads(st.secrets["FIREBASE_SERVICE_ACCOUNT_KEY"])
                        cred = credentials.Certificate(key_dict)
                        firebase_admin.initialize_app(cred)
                        st.sidebar.success("Firebase connection successful (cloud)")
                    except Exception as e:
                        st.sidebar.error(f"Error accessing Firebase secrets: {e}")
                        st.stop()
            return firestore.client()
        except Exception as e:
            st.error(f"Firestore initialization failed: {str(e)}")
            st.code(traceback.format_exc())
            return None

    SPOONACULAR_API_KEY = 'a75d9c6a6488408eb84eebcda1ff3d55'
    SPOONACULAR_API_URL = "https://api.spoonacular.com/recipes/complexSearch"

    DEFAULT_INGREDIENT_RATINGS = {i: 0 for i in content_i}
    COMMON_INGREDIENTS = content_i

    def get_cuisine_from_country(country):
        cuisine_mapping = {
            'Italy': 'Italian',
            'France': 'French',
            'China': 'Chinese',
            'Japan': 'Japanese',
            'India': 'Indian',
            'Mexico': 'Mexican',
            'Thailand': 'Thai',
            'Spain': 'Spanish',
            'Greece': 'Greek',
            'United States': 'American',
            'United Kingdom': 'British',
            'Germany': 'German',
            'Vietnam': 'Vietnamese',
            'Korea': 'Korean',
            'Lebanon': 'Lebanese',
            'Morocco': 'Mediterranean',
            'Turkey': 'Mediterranean',
            'Brazil': 'Latin American',
            'Argentina': 'Latin American',
            'Ethiopia': 'African',
            'Nigeria': 'African',
            'Sweden': 'Nordic',
            'Denmark': 'Nordic'
        }
        return cuisine_mapping.get(country, '')

    def search_recipes(ingredients, country, recipe_name=""):
        cuisine = get_cuisine_from_country(country)
        query = ','.join(ingredients)
        params = {
            "apiKey": SPOONACULAR_API_KEY,
            "number": 10,
            "addRecipeInformation": True,
            "fillIngredients": True,
            "instructionsRequired": True,
            "addRecipeNutrition": True,
        }
        if ingredients:
            params["includeIngredients"] = query
        if recipe_name:
            params["query"] = recipe_name
        if cuisine:
            params["cuisine"] = cuisine
        try:
            response = requests.get(SPOONACULAR_API_URL, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Error fetching recipes: {response.status_code}")
                st.write(f"Response: {response.text}")
                return None
        except Exception as e:
            st.error(f"API request failed: {str(e)}")
            return None

    def save_ratings_to_firebase(db, email, ratings_data):
        if not db:
            st.error("Database connection not established. Cannot save ratings.")
            return False
        try:
            batch = db.batch()
            for recipe_id, data in ratings_data.items():
                if data['rating'] > 0:
                    rating_ref = db.collection('recipe').document(f"{email}_{recipe_id}")
                    rating_data = {
                        'user_id': email,
                        'recipe_id': str(recipe_id),
                        'recipe_name': data['name'],
                        'rating': data['rating'],
                        'timestamp': firestore.SERVER_TIMESTAMP
                    }
                    batch.set(rating_ref, rating_data)
            batch.commit()
            generate_csv_from_firebase(db)
            st.success("All ratings saved successfully!")
            return True
        except Exception as e:
            st.error(f"Error saving ratings: {str(e)}")
            st.code(traceback.format_exc())
            return False

    def save_ingredient_ratings_to_firebase(db, email, ingredient_ratings):
        if not db:
            st.error("Database connection not established. Cannot save ingredient ratings.")
            return False
        try:
            ingredient_ref = db.collection('incri_rating').document(email)
            doc = ingredient_ref.get()
            ingredient_data = {
                'username': email,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'ratings': {}
            }
            if doc.exists:
                existing_data = doc.to_dict()
                if 'ratings' in existing_data:
                    ingredient_data['ratings'] = existing_data['ratings']
            for ingredient, rating in ingredient_ratings.items():
                if rating > 0:
                    ingredient_data['ratings'][ingredient] = rating
            ingredient_ref.set(ingredient_data, merge=True)
            st.success("All ingredient ratings saved successfully!")
            return True
        except Exception as e:
            st.error(f"Error saving ingredient ratings: {str(e)}")
            st.code(traceback.format_exc())
            return False

    def generate_csv_from_firebase(db):
        if not db:
            st.error("Database connection not established. Cannot generate CSV.")
            return None
        try:
            ratings_ref = db.collection('recipe').get()
            ratings_data = []
            for rating in ratings_ref:
                rating_data = rating.to_dict()
                ratings_data.append({
                    'user_id': rating_data.get('user_id', ''),
                    'recipe_id': rating_data.get('recipe_id', ''),
                    'recipe_name': rating_data.get('recipe_name', ''),
                    'rating': rating_data.get('rating', 0),
                    'timestamp': rating_data.get('timestamp', '')
                })
            df = pd.DataFrame(ratings_data)
            if df.empty:
                df = pd.DataFrame(columns=['user_id', 'recipe_id', 'recipe_name', 'rating', 'timestamp'])
            csv_path = "recipe_ratings_database.csv"
            df.to_csv(csv_path, index=False)
            return csv_path
        except Exception as e:
            st.error(f"Error generating CSV: {str(e)}")
            st.code(traceback.format_exc())
            return None

    def get_user_ratings(db, user_id):
        if not db:
            st.error("Database connection not established. Cannot fetch ratings.")
            return []
        try:
            ratings = db.collection('recipe').where('user_id', '==', user_id).get()
            return [rating.to_dict() for rating in ratings]
        except Exception as e:
            st.error(f"Error fetching user ratings: {str(e)}")
            st.code(traceback.format_exc())
            return []

    def display_recipe(recipe, key_prefix, ratings_dict):
        with st.expander(f"{recipe['title']}"):
            col1, col2 = st.columns([1, 2])
            recipe_id = recipe['id']
            recipe_name = recipe['title']
            if recipe_id not in ratings_dict:
                ratings_dict[recipe_id] = {'name': recipe_name, 'rating': 0}
            with col1:
                if 'image' in recipe and recipe['image']:
                    st.image(recipe['image'], width=200)
                else:
                    st.write("No image available")
                ratings_dict[recipe_id]['rating'] = st.slider(
                    "Rate this recipe", 
                    0, 5, 
                    ratings_dict[recipe_id]['rating'],
                    key=f"{key_prefix}_slider_{recipe_id}"
                )
            with col2:
                health_info = []
                if 'healthScore' in recipe:
                    health_info.append(f"Health Score: {recipe['healthScore']}/100")
                if 'diets' in recipe and recipe['diets']:
                    health_info.append(f"Diets: {', '.join(recipe['diets'])}")
                if health_info:
                    st.markdown("### Health Information")
                    for info in health_info:
                        st.markdown(f"- {info}")
                if 'nutrition' in recipe and 'nutrients' in recipe['nutrition']:
                    st.markdown("### Nutrition Facts")
                    nutrients = recipe['nutrition']['nutrients']
                    nutrient_values = {
                        'Calories': '0 kcal',
                        'Fat': '0 g',
                        'Protein': '0 g',
                        'Carbohydrates': '0 g'
                    }
                    for nutrient in nutrients:
                        name = nutrient['name']
                        value = f"{nutrient['amount']}{nutrient['unit']}"
                        if name == 'Calories':
                            nutrient_values['Calories'] = value
                        elif name == 'Fat':
                            nutrient_values['Fat'] = value
                        elif name == 'Protein':
                            nutrient_values['Protein'] = value
                        elif name == 'Carbohydrates':
                            nutrient_values['Carbohydrates'] = value
                    for name, value in nutrient_values.items():
                        st.markdown(f"- {name}: {value}")
                st.markdown("### Ingredients")
                if 'extendedIngredients' in recipe:
                    for ingredient in recipe['extendedIngredients']:
                        st.markdown(f"- {ingredient['original']}")
                else:
                    st.write("No ingredient information available")
                st.markdown("### Instructions")
                instructions = recipe.get('instructions', 'No instructions available for this recipe.')
                st.write(instructions.replace('\n', '\n\n') if instructions else "No instructions available for this recipe.")
                source_url = recipe.get('sourceUrl', '#')
                if source_url and source_url != '#':
                    st.markdown(f"[View Full Recipe]({source_url})")

    def get_recommendations(db, user_id):
        if not db:
            return [], "Database connection not established. Cannot generate recommendations."
        try:
            user_ratings = get_user_ratings(db, user_id)
            if not user_ratings:
                return [], "You haven't rated any recipes yet. Rate some recipes to get personalized recommendations."
            return [], "Recommendation feature is currently under maintenance. Please check back later."
        except Exception as e:
            st.error(f"Recommendation processing error: {str(e)}")
            st.code(traceback.format_exc())
            return [], f"Error processing recommendations: {str(e)}"

    def main():
        st.title("Healthy Recipe Finder")
        db = initialize_firebase()
        if not db:
            st.error("Failed to connect to Firebase. Please check your configuration.")
            st.stop()
        if 'searched_recipes' not in st.session_state:
            st.session_state.searched_recipes = []
        if 'ratings' not in st.session_state:
            st.session_state.ratings = {}
        if 'ingredient_ratings' not in st.session_state:
            st.session_state.ingredient_ratings = DEFAULT_INGREDIENT_RATINGS.copy()
        if 'search_performed' not in st.session_state:
            st.session_state.search_performed = False
        email = _email
        tab1, tab2, tab4, tab3 = st.tabs(["Find Recipes", "Rate Ingredients", "Recommendations", "My Ratings"])
        with tab1:
            st.header("Find Healthy Recipes")
            with st.form("recipe_search_form"):
                countries = [
                    "Select Country", "United States", "United Kingdom", "Italy", "France", 
                    "China", "Japan", "India", "Mexico", "Thailand", "Spain", "Greece", 
                    "Germany", "Vietnam", "Korea", "Lebanon", "Morocco", "Turkey", 
                    "Brazil", "Argentina", "Ethiopia", "Nigeria", "Sweden", "Denmark"
                ]
                selected_country = st.selectbox("Select your country", countries)
                ingredients_list = ["Select Ingredient"] + COMMON_INGREDIENTS
                selected_ingredient = st.selectbox("Select an ingredient", options=ingredients_list)
                recipe_name_search = st.text_input("Search recipes by name", "")
                search_submitted = st.form_submit_button("Search Recipes")
                if search_submitted:
                    if selected_country == "Select Country":
                        st.warning("Please select a country")
                    elif selected_ingredient == "Select Ingredient" and not recipe_name_search:
                        st.warning("Please select an ingredient or enter a recipe name")
                    else:
                        selected_ingredients = []
                        if selected_ingredient != "Select Ingredient":
                            selected_ingredients = [selected_ingredient]
                        st.session_state.search_performed = True
                        with st.spinner("Searching for recipes..."):
                            results = search_recipes(selected_ingredients, selected_country, recipe_name_search)
                            if results and 'results' in results:
                                recipes = results['results']
                                if recipes:
                                    st.session_state.searched_recipes = recipes
                                    st.success(f"Found {len(recipes)} recipes!")
                                    st.session_state.ratings = {}
                                else:
                                    st.warning("No recipes found. Try different ingredients or search terms.")
                                    st.session_state.searched_recipes = []
            if st.session_state.search_performed and st.session_state.searched_recipes:
                st.header("Results")
                for recipe in st.session_state.searched_recipes:
                    display_recipe(recipe, "search", st.session_state.ratings)
                if st.button("Save All Ratings"):
                    if any(data['rating'] > 0 for data in st.session_state.ratings.values()):
                        save_ratings_to_firebase(db, email, st.session_state.ratings)
                        st.session_state.ratings = {}
                    else:
                        st.warning("Please rate at least one recipe before saving.")
        with tab2:
            st.header("Rate Your Favorite Ingredients")
            st.write("Rate ingredients based on your preference on a scale of 0 to 5. These ratings will help us provide better recommendations.")
            col1, col2 = st.columns(2)
            ingredients_to_rate = sorted(list(st.session_state.ingredient_ratings.keys()))
            for i, ingredient in enumerate(ingredients_to_rate):
                col = col1 if i % 2 == 0 else col2
                current_rating = st.session_state.ingredient_ratings.get(ingredient, 0)
                with col:
                    st.session_state.ingredient_ratings[ingredient] = st.slider(
                        f"{ingredient}", 
                        0, 5, 
                        int(current_rating),
                        key=f"ing_rate_{i}"
                    )
            if st.button("Save Ingredient Ratings"):
                if st.session_state.ingredient_ratings and any(rating > 0 for rating in st.session_state.ingredient_ratings.values()):
                    save_ingredient_ratings_to_firebase(db, email, st.session_state.ingredient_ratings)
                    st.success("Ingredient ratings saved successfully!")
                else:
                    st.warning("Please rate at least one ingredient before saving.")
        with tab4:
            st.header("Personalized Recipe Recommendations")
            st.write("Based on your ratings, we think you might enjoy these recipes:")
            with st.spinner("Generating recommendations..."):
                recommendations, error_msg = get_recommendations(db, email)
            if error_msg:
                st.info(error_msg)
            elif recommendations:
                st.success(f"Found {len(recommendations)} recommendations for you!")
                available_cuisines = ["All Cuisines"] + list(set([r.get('cuisine', 'Unknown') for r in recommendations if 'cuisine' in r]))
                rec_cuisine_filter = st.selectbox("Filter by cuisine", available_cuisines)
                filtered_recs = recommendations
                if rec_cuisine_filter != "All Cuisines":
                    filtered_recs = [r for r in recommendations if r.get('cuisine', '') == rec_cuisine_filter]
                for i, rec in enumerate(filtered_recs):
                    with st.expander(f"{i+1}. {rec.get('recipe_name', 'Recipe')} - Score: {rec.get('score', 'N/A')}"):
                        st.write(f"**Recipe ID:** {rec.get('recipe_id', 'Unknown')}")
                        if 'cuisine' in rec:
                            st.write(f"**Cuisine:** {rec.get('cuisine', 'Unknown')}")
                        if st.button(f"Find this recipe", key=f"find_rec_{i}"):
                            st.session_state.search_recipe_id = rec.get('recipe_id', '')
                            st.rerun()
            else:
                st.info("No recommendations available. Try rating more recipes first.")
        with tab3:
            st.header("Your Saved Ratings")
            if st.button("Refresh Ratings"):
                st.rerun()
            user_ratings = get_user_ratings(db, email)
            if user_ratings:
                st.success(f"You have rated {len(user_ratings)} recipes so far.")
                ratings_df = pd.DataFrame(user_ratings)
                if not ratings_df.empty:
                    display_columns = ['recipe_name', 'rating']
                    if 'timestamp' in ratings_df.columns:
                        display_columns.append('timestamp')
                    available_columns = [col for col in display_columns if col in ratings_df.columns]
                    ratings_df = ratings_df[available_columns]
                    column_rename = {
                        'recipe_name': 'Recipe Name',
                        'rating': 'Your Rating'
                    }
                    if 'timestamp' in available_columns:
                        column_rename['timestamp'] = 'Rated On'
                    ratings_df = ratings_df.rename(columns=column_rename)
                    if 'Your Rating' in ratings_df.columns:
                        ratings_df = ratings_df.sort_values(by='Your Rating', ascending=False)
                    st.dataframe(ratings_df, use_container_width=True)
            else:
                st.info("You haven't saved any ratings yet. Start rating recipes to see them here!")
            st.subheader("Your Ingredient Preferences")
            ing_df = pd.DataFrame(list(st.session_state.ingredient_ratings.items()), columns=['Ingredient', 'Your Rating'])
            ing_df = ing_df.sort_values(by='Your Rating', ascending=False)
            st.dataframe(ing_df, use_container_width=True)
    if __name__ == "__main__":
        main()

# ------------------------------------ Utility Functions ------------------------------------
def save_to_csv(data):
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/survey_data_{timestamp}.csv"
        df = pd.DataFrame([data])
        main_csv = "data/all_survey_responses.csv"
        if os.path.exists(main_csv):
            existing_df = pd.read_csv(main_csv)
            combined_df = pd.concat([existing_df, df], ignore_index=True)
            combined_df.to_csv(main_csv, index=False)
        else:
            df.to_csv(main_csv, index=False)
        df.to_csv(filename, index=False)
        return True, filename
    except Exception as e:
        return False, str(e)

def calculate_bmi(weight, height):
    height_m = height / 100
    bmi = weight / (height_m ** 2)
    return round(bmi, 2)

def get_bmi_category(bmi):
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal weight"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obese"

def save_to_firebase(data):
    try:
        if db is None:
            return False, "Database not initialized"
        doc_id = str(uuid.uuid4())
        data['timestamp'] = datetime.now()
        db.collection('survey_responses').document(doc_id).set(data)
        return True, doc_id
    except Exception as e:
        return False, str(e)

def update_survey_response(email, updated_data):
    try:
        query = db.collection('survey_responses').where('email', '==', email).limit(1).get()
        if query:
            doc_id = query[0].id
            updated_data['timestamp'] = datetime.now()
            db.collection('survey_responses').document(doc_id).update(updated_data)
            return True, doc_id
        else:
            doc_id = str(uuid.uuid4())
            updated_data['timestamp'] = datetime.now()
            db.collection('survey_responses').document(doc_id).set(updated_data)
            return True, doc_id
    except Exception as e:
        return False, str(e)

def has_completed_survey(email):
    try:
        if db is None:
            return False
        query = db.collection('survey_responses').where('email', '==', email).limit(1).get()
        return len(query) > 0
    except Exception as e:
        st.error(f"Error checking survey status: {e}")
        return False

def get_user_survey_data(email):
    try:
        if db is None:
            return None
        query = db.collection('survey_responses').where('email', '==', email).limit(1).get()
        if len(query) > 0:
            return query[0].to_dict()
        return None
    except Exception as e:
        st.error(f"Error retrieving survey data: {e}")
        return None

def store_current_diet_chart(user_email, diet_plan):
    try:
        doc_id = str(uuid.uuid4())
        data = {
            "user_email": user_email,
            "diet_plan": diet_plan,
            "timestamp": datetime.now()
        }
        db.collection("save_diet_chart").document(doc_id).set(data)
        return True, doc_id
    except Exception as e:
        return False, str(e)

def get_saved_diet_charts(user_email):
    try:
        docs = db.collection("save_diet_chart")\
                 .where("user_email", "==", user_email)\
                 .order_by("timestamp", direction=firestore.Query.DESCENDING)\
                 .stream()
        results = []
        for doc in docs:
            results.append(doc.to_dict())
        return results
    except Exception as e:
        st.error("Error retrieving saved diet charts: " + str(e))
        return []

def show_previous_diet_charts(user_email, user_data):
    previous_charts = get_saved_diet_charts(user_email)
    if previous_charts:
        with st.expander("Previous Diet Charts"):
            options = {}
            for chart in previous_charts:
                ts = chart.get("timestamp")
                key = f"Chart saved on: {ts.strftime('%Y-%m-%d %H:%M:%S')}" if isinstance(ts, datetime) else f"Chart saved on: {ts}"
                options[key] = chart.get("diet_plan")
            selected_key = st.selectbox("Select a previous diet chart to view details", list(options.keys()))
            if selected_key:
                selected_plan = options[selected_key]
                st.write("**Full Diet Chart Details:**")
                dietchar.display_diet_chart(user_data, selected_plan)
    else:
        st.info("No previous diet charts found.")

# ------------------------------------ Firebase Initialization ------------------------------------
firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

@st.cache_resource
def initialize_firebase_admin():
    try:
        if not firebase_admin._apps:
            if os.path.exists("serviceAccountKey.json"):
                cred = credentials.Certificate("serviceAccountKey.json")
                firebase_admin.initialize_app(cred)
                st.sidebar.success("Firebase connection successful (local)")
            else:
                try:
                    key_dict = json.loads(st.secrets["FIREBASE_SERVICE_ACCOUNT_KEY"])
                    cred = credentials.Certificate(key_dict)
                    firebase_admin.initialize_app(cred)
                    st.sidebar.success("Firebase connection successful (cloud)")
                except Exception as e:
                    st.sidebar.error(f"Error accessing Firebase secrets: {e}")
                    st.stop()
        return firestore.client()
    except Exception as e:
        st.error(f"Firestore initialization failed: {str(e)}")
        st.code(traceback.format_exc())
        return None

try:
    db = initialize_firebase_admin()
except Exception as e:
    st.warning("Firestore initialization failed. Some features may not work properly.")
    db = None

if not os.path.exists('data'):
    os.makedirs('data')

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_info' not in st.session_state:
    st.session_state.user_info = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = "dashboard"
if 'first_login' not in st.session_state:
    st.session_state.first_login = False
if 'survey_completed' not in st.session_state:
    st.session_state.survey_completed = False

# ------------------------------------ Authentication ------------------------------------
if not st.session_state.logged_in:
    st.title("🥗 Diet Recommendation App")
    st.write("Log in or sign up to get personalized diet recommendations")
    tab1, tab2 = st.tabs(["Login", "Signup"])
    with tab1:
        st.header("Login")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")
        login_button = st.button("Login")
        if login_button:
            if not login_email or not login_password:
                st.error("Please enter both email and password")
            else:
                try:
                    user = auth.sign_in_with_email_and_password(login_email, login_password)
                    st.success("Login successful!")
                    st.session_state.logged_in = True
                    st.session_state.user_info = user
                    completed = has_completed_survey(user['email'])
                    st.session_state.survey_completed = completed
                    if not completed:
                        st.session_state.first_login = True
                        st.session_state.current_page = "survey"
                    else:
                        st.session_state.current_page = "dashboard"
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Login failed: {e}")
    with tab2:
        st.header("Create an Account")
        signup_email = st.text_input("Email", key="signup_email")
        signup_password = st.text_input("Password", type="password", key="signup_password")
        signup_confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm_password")
        signup_button = st.button("Sign Up")
        if signup_button:
            if not signup_email or not signup_password or not signup_confirm_password:
                st.error("Please fill in all fields")
            elif signup_password != signup_confirm_password:
                st.error("Passwords do not match")
            else:
                try:
                    user = auth.create_user_with_email_and_password(signup_email, signup_password)
                    st.success("Account created successfully!")
                    st.session_state.logged_in = True
                    st.session_state.user_info = user
                    st.session_state.first_login = True
                    st.session_state.current_page = "survey"
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Signup failed: {e}")
else:
    if st.session_state.first_login and not st.session_state.survey_completed:
        st.session_state.current_page = "survey"
    col1, col2 = st.columns([1, 4])
    with col1:
        st.sidebar.title("Diet Dashboard")
        st.sidebar.write(f"Welcome, {st.session_state.user_info['email']}")
        st.sidebar.markdown("### Menu")
        if st.sidebar.button("My Profile", use_container_width=True):
            st.session_state.current_page = "profile"
            st.rerun()
        if st.sidebar.button("My Diet Chart", use_container_width=True):
            st.session_state.current_page = "dashboard"
            st.rerun()
        if st.sidebar.button("Get My Recipes", use_container_width=True):
            st.session_state.current_page = "recipes"
            st.rerun()
        if st.sidebar.button("Ingredients Cost", use_container_width=True):
            st.session_state.current_page = "ingredients_cost"
            st.rerun()
        st.sidebar.markdown("---")
        if st.sidebar.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_info = None
            st.session_state.first_login = False
            st.session_state.survey_completed = False
            st.success("Logged out successfully!")
            time.sleep(1)
            st.rerun()

    with col2:
        # --------------------- Survey Page ---------------------
        if st.session_state.current_page == "survey":
            if st.session_state.survey_completed:
                st.session_state.current_page = "dashboard"
                st.info("You have already completed the survey. Redirecting to dashboard...")
                time.sleep(2)
                st.rerun()
            else:
                st.title("🥗 Personalized Diet Recommendation Survey")
                st.write("Complete this survey to help us tailor your experience.")
                with st.form("diet_survey_form"):
                    st.subheader("Personal Information")
                    col1_s, col2_s = st.columns(2)
                    with col1_s:
                        name = st.text_input("Full Name")
                        age = st.number_input("Age", min_value=12, max_value=100, value=30)
                        gender = st.selectbox("Gender", ["Male", "Female"])
                    with col2_s:
                        height = st.number_input("Height (cm)", min_value=100, max_value=250, value=170)
                        weight = st.number_input("Weight (kg)", min_value=30, max_value=250, value=70)
                        email = st.text_input("Email Address", value=st.session_state.user_info['email'], disabled=True)
                        country = st.text_input("Country")
                    if height and weight:
                        bmi = calculate_bmi(weight, height)
                        bmi_category = get_bmi_category(bmi)
                        st.info(f"Your BMI: **{bmi}** - Category: **{bmi_category}**")
                    st.subheader("Diet & Lifestyle")
                    diet_pref = st.radio("Diet Preference", ["Vegetarian", "Non-vegetarian", "Vegan", "Pescatarian", "Flexitarian"])
                    food_allergies = st.multiselect("Food Allergies or Restrictions (if any)",
                                                    ["Nuts", "Dairy", "Gluten", "Seafood", "Eggs", "Soy", 
                                                     "Lactose Intolerant", "None"])
                    activity_level = st.select_slider("Activity Level", 
                                                      options=["Sedentary (office job, little exercise)", 
                                                               "Lightly active (light exercise 1-3 days/week)", 
                                                               "Moderately active (moderate exercise 3-5 days/week)", 
                                                               "Very active (hard exercise 6-7 days/week)", 
                                                               "Extremely active (physical job & hard exercise)"])
                    fitness_goal = st.selectbox("Fitness Goal", 
                                                ["Weight loss", "Muscle gain", "Maintenance", "Improve overall health", "Athletic performance"])
                    sleep_hours = st.slider("Average Sleep Duration (hours per day)", 4, 12, 7)
                    work_life = st.select_slider("How would you describe your work-life balance?",
                                                 options=["Very stressful", "Somewhat stressful", "Balanced", "Good balance", "Excellent balance"])
                    lifestyle = st.multiselect("Select aspects that describe your lifestyle",
                                               ["Long work hours", "Regular exercise", "Frequent travel", 
                                                "Work from home", "Student", "Parent/Caregiver", "Social events with food/drink"])
                    st.subheader("Meal Patterns & Budget")
                    meals_per_day = st.slider("How many meals do you typically eat per day?", 1, 6, 3)
                    snacking = st.radio("Snacking habits", 
                                        ["Rarely snack", "Occasional snacks", "Regular snacks between meals", "Frequent snacking throughout the day"])
                    eating_out = st.select_slider("How often do you eat at restaurants or order takeout?",
                                                  options=["Rarely (few times a month)", "Occasionally (1-2 times a week)", "Regularly (3-5 times a week)", "Very frequently (almost daily)"])
                    budget_constraint = st.slider("What's your monthly budget for food? (₹ per month)", 1000, 6000, 3000, step=500)
                    cooking_skill = st.select_slider("Cooking skills",
                                                     options=["Beginner", "Can follow basic recipes", "Intermediate", "Advanced"])
                    cooking_time = st.slider("How much time can you spend cooking per day (minutes)?", 15, 120, 30, step=15)
                    st.subheader("Additional Information")
                    health_conditions = st.multiselect("Do you have any health conditions?",
                                                       ["Diabetes", "Hypertension", "Heart disease", "Digestive issues", "Food intolerances", "None"])
                    additional_info = st.text_area("Any additional information you'd like to share")
                    submitted = st.form_submit_button("Submit Survey")
                    if submitted:
                        survey_data = {
                            "name": name,
                            "age": age,
                            "gender": gender,
                            "height": height,
                            "weight": weight,
                            "email": st.session_state.user_info['email'],
                            "country": country,
                            "bmi": calculate_bmi(weight, height),
                            "bmi_category": get_bmi_category(calculate_bmi(weight, height)),
                            "diet_pref": diet_pref,
                            "food_allergies": food_allergies,
                            "activity_level": activity_level,
                            "fitness_goal": fitness_goal,
                            "sleep_hours": sleep_hours,
                            "work_life": work_life,
                            "lifestyle": lifestyle,
                            "meals_per_day": meals_per_day,
                            "snacking": snacking,
                            "eating_out": eating_out,
                            "budget_constraint": budget_constraint,
                            "cooking_skill": cooking_skill,
                            "cooking_time": cooking_time,
                            "health_conditions": health_conditions,
                            "additional_info": additional_info
                        }
                        success_csv, csv_result = save_to_csv(survey_data)
                        success_fb, doc_id = save_to_firebase(survey_data)
                        if success_csv and success_fb:
                            st.success("Survey submitted successfully!")
                            st.session_state.survey_completed = True
                            st.session_state.current_page = "dashboard"
                            st.rerun()
                        else:
                            st.error("Failed to save survey data: " + str(csv_result) + " " + str(doc_id))
        # --------------------- Recipes Page ---------------------
        elif st.session_state.current_page == "recipes":
            st.title("Get My Recipes")
            user_email = st.session_state.user_info['email']
            result = mod.recommend(user_email)
            print("mod.recommend returned:", result)
            _it = []
            re = []
            if result is None:
                re = ['palak paneer']
                st.error("No recommendation data available. Please check your input or the recommendation logic.")
            else:
                _it = result[0]
                re = result[1]

            _it = _it[:25] if len(_it) >= 25 else _it
            recipy_recommend(user_email, _it, re)
        # --------------------- Dashboard Page ---------------------
        elif st.session_state.current_page == "dashboard":
            st.title("Your Diet Dashboard")
            user_data = get_user_survey_data(st.session_state.user_info['email'])
            if user_data:
                st.header("Your Health Profile")
                col1_d, col2_d, col3_d = st.columns(3)
                with col1_d:
                    st.metric("BMI", f"{user_data.get('bmi', 'N/A')}", help="Body Mass Index based on your height and weight")
                with col2_d:
                    st.metric("Weight", f"{user_data.get('weight', 'N/A')} kg")
                with col3_d:
                    st.metric("Goal", user_data.get('fitness_goal', 'N/A'))
                current_tab, previous_tab = st.tabs(["Current Diet Chart", "Previous Diet Charts"])
                with current_tab:
                    current_diet_plan = dietchar.generate_diet_plan(user_data)
                    dietchar.display_diet_chart(user_data, current_diet_plan)
                    if st.button("Save Current Diet Chart"):
                        success, doc_id = store_current_diet_chart(user_data.get("email"), current_diet_plan)
                        if success:
                            st.success("Current diet chart saved!")
                        else:
                            st.error("Failed to save current diet chart: " + doc_id)
                with previous_tab:
                    show_previous_diet_charts(user_data.get("email"), user_data)
            else:
                st.warning("We couldn't find your survey data. Please complete the diet survey to continue.")
                if st.button("Take Diet Survey Now"):
                    st.session_state.current_page = "survey"
                    st.rerun()
        # --------------------- Profile Page ---------------------
        elif st.session_state.current_page == "profile":
            st.title("Your Health Profile")
            user_data = get_user_survey_data(st.session_state.user_info['email'])
            with st.form("profile_form"):
                full_name = st.text_input("Full Name", value=user_data.get("name", "") if user_data else "")
                email = st.text_input("Email", value=st.session_state.user_info['email'], disabled=True)
                col1_p, col2_p = st.columns(2)
                with col1_p:
                    age = st.number_input("Age", min_value=12, max_value=100, value=user_data.get("age", 30) if user_data else 30)
                    height = st.number_input("Height (cm)", min_value=100, max_value=250, value=user_data.get("height", 170) if user_data else 170)
                    weight = st.number_input("Weight (kg)", min_value=30, max_value=250, value=user_data.get("weight", 70) if user_data else 70)
                with col2_p:
                    gender = st.selectbox("Gender", ["Male", "Female", "Non-binary", "Prefer not to say"],
                                            index=["Male", "Female", "Non-binary", "Prefer not to say"].index(user_data.get("gender", "Male"))
                                            if user_data and user_data.get("gender") in ["Male", "Female", "Non-binary", "Prefer not to say"] else 0)
                    country = st.text_input("Country", value=user_data.get("country", "") if user_data else "")
                    diet_pref = st.selectbox("Diet Preference", ["Vegetarian", "Non-vegetarian", "Vegan", "Pescatarian", "Flexitarian"],
                                             index=["Vegetarian", "Non-vegetarian", "Vegan", "Pescatarian", "Flexitarian"].index(user_data.get("diet_pref", "Non-vegetarian"))
                                             if user_data and user_data.get("diet_pref") in ["Vegetarian", "Non-vegetarian", "Vegan", "Pescatarian", "Flexitarian"] else 1)
                exercise_freq = st.selectbox("Exercise Frequency", ["None", "1-2 times a week", "3-4 times a week", "5+ times a week"],
                                             index=1 if user_data is None else 0)
                water_intake = st.slider("Daily Water Intake (glasses)", 0, 20, 8)
                sleep_quality = st.selectbox("Sleep Quality", ["Poor", "Average", "Good"], index=1)
                if height and weight:
                    bmi = calculate_bmi(weight, height)
                    bmi_category = get_bmi_category(bmi)
                    st.info(f"Your BMI: **{bmi}** - Category: **{bmi_category}**")
                st.subheader("Health Goals")
                fitness_goal = st.selectbox("Fitness Goal", 
                              ["Weight loss", "Muscle gain", "Maintenance", "Improve overall health", "Athletic performance"],
                              index=["Weight loss", "Muscle gain", "Maintenance", "Improve overall health", "Athletic performance"].index(user_data.get("fitness_goal", "Improve overall health"))
                              if user_data and user_data.get("fitness_goal") in ["Weight loss", "Muscle gain", "Maintenance", "Improve overall health", "Athletic performance"] else 0)
                activity_level = st.select_slider("Activity Level", 
                                                options=["Sedentary (office job, little exercise)", "Lightly active (light exercise 1-3 days/week)", "Moderately active (moderate exercise 3-5 days/week)", "Very active (hard exercise 6-7 days/week)", "Extremely active (physical job & hard exercise)"],
                                                value=user_data.get("activity_level", "Moderately active (moderate exercise 3-5 days/week)") if user_data else "Moderately active (moderate exercise 3-5 days/week)")
                submitted_profile = st.form_submit_button("Update Profile and Generate New Diet Chart")
                if submitted_profile:
                    updated_data = {
                        "name": full_name,
                        "age": age,
                        "gender": gender,
                        "height": height,
                        "weight": weight,
                        "country": country,
                        "diet_pref": diet_pref,
                        "exercise_freq": exercise_freq,
                        "water_intake": water_intake,
                        "sleep_quality": sleep_quality,
                        "fitness_goal": fitness_goal,
                        "activity_level": activity_level
                    }
                    success, res = update_survey_response(st.session_state.user_info['email'], updated_data)
                    if success:
                        st.success("Profile updated successfully!")
                        # Generate and display new diet chart
                        new_diet_plan = dietchar.generate_diet_plan(updated_data)
                        st.subheader("New Diet Chart")
                        dietchar.display_diet_chart(updated_data, new_diet_plan)
                        if st.button("Save This Diet Chart"):
                            s_success, doc_id = store_current_diet_chart(updated_data.get("email", st.session_state.user_info['email']), new_diet_plan)
                            if s_success:
                                st.success("Diet chart saved!")
                            else:
                                st.error("Failed to save diet chart: " + doc_id)
                    else:
                        st.error("Profile update failed: " + res)
        # --------------------- Ingredients Cost Page ---------------------
        elif st.session_state.current_page == "ingredients_cost":
            # Temporarily override st.set_page_config to prevent duplicate call
            original_set_page_config = st.set_page_config
            st.set_page_config = lambda *args, **kwargs: None
            incri_budget.main()
            st.set_page_config = original_set_page_config
