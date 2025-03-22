import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import requests
import json
import traceback
import os  # Add missing import
import Model_Beta as mod
def recipy_recommend(_email,content_i,content_r):
    # Initialize Firebase
    def initialize_firebase():
        try:
            # Check if already initialized
            if not firebase_admin._apps:
                # For local development
                if os.path.exists("serviceAccountKey.json"):
                    cred = credentials.Certificate("serviceAccountKey.json")
                    firebase_admin.initialize_app(cred)
                    st.sidebar.success("Firebase connection successful (local)")
                # For Streamlit Cloud
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

    # API Configuration
    SPOONACULAR_API_KEY = 'a75d9c6a6488408eb84eebcda1ff3d55'
    SPOONACULAR_API_URL = "https://api.spoonacular.com/recipes/complexSearch"

    # Default ingredient ratings data - 10 ingredients from different categories
    DEFAULT_INGREDIENT_RATINGS = {}
    for i in content_i:
        DEFAULT_INGREDIENT_RATINGS[i] = 0

    # Common ingredients list
    COMMON_INGREDIENTS = content_i

    # Country to cuisine mapping
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

    # Function to search recipes based on ingredients and country
    def search_recipes(ingredients, country, recipe_name=""):
        # Get cuisine based on country
        cuisine = get_cuisine_from_country(country)
        
        # Join multiple ingredients with commas
        query = ','.join(ingredients)
        
        params = {
            "apiKey": SPOONACULAR_API_KEY,
            "number": 10,
            "addRecipeInformation": True,
            "fillIngredients": True,
            "instructionsRequired": True,
            "addRecipeNutrition": True,
        }
        
        # Add query parameter if ingredients are provided
        if ingredients:
            params["includeIngredients"] = query
        
        # Add title search if provided
        if recipe_name:
            params["query"] = recipe_name
        
        # Add cuisine parameter if available
        if cuisine:
            params["cuisine"] = cuisine
        
        try:
            response = requests.get(SPOONACULAR_API_URL, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"Error fetching recipes: {response.status_code}")
                st.write(f"Response: {response.text}")  # Added to debug API issues
                return None
        except Exception as e:
            st.error(f"API request failed: {str(e)}")
            return None

    # Save ratings to Firebase
    def save_ratings_to_firebase(db, email, ratings_data):
        if not db:
            st.error("Database connection not established. Cannot save ratings.")
            return False
            
        try:
            batch = db.batch()
            
            for recipe_id, data in ratings_data.items():
                if data['rating'] > 0:  # Only save if rating is provided
                    rating_ref = db.collection('recipe').document(f"{email}_{recipe_id}")
                    rating_data = {
                        'user_id': email,
                        'recipe_id': str(recipe_id),
                        'recipe_name': data['name'],
                        'rating': data['rating'],
                        'timestamp': firestore.SERVER_TIMESTAMP  # Using server timestamp
                    }
                    batch.set(rating_ref, rating_data)
            
            # Commit the batch
            batch.commit()
            
            # Generate CSV after successful commit
            generate_csv_from_firebase(db)
            
            st.success("All ratings saved successfully!")
            return True
        except Exception as e:
            st.error(f"Error saving ratings: {str(e)}")
            st.code(traceback.format_exc())
            return False

    # Save ingredient ratings to Firebase
    def save_ingredient_ratings_to_firebase(db, email, ingredient_ratings):
        if not db:
            st.error("Database connection not established. Cannot save ingredient ratings.")
            return False
            
        try:
            # Use the email as the document ID
            ingredient_ref = db.collection('incri_rating').document(email)
            
            # Get existing data if any
            doc = ingredient_ref.get()
            
            # Prepare the data to save
            ingredient_data = {
                'username': email,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'ratings': {}
            }
            
            # If document already exists, get the existing ingredients
            if doc.exists:
                existing_data = doc.to_dict()
                if 'ratings' in existing_data:
                    ingredient_data['ratings'] = existing_data['ratings']
            
            # Update with new ratings
            for ingredient, rating in ingredient_ratings.items():
                if rating > 0:  # Only save if rating is provided
                    ingredient_data['ratings'][ingredient] = rating
            
            # Save to Firestore
            ingredient_ref.set(ingredient_data, merge=True)
            
            st.success("All ingredient ratings saved successfully!")
            return True
        except Exception as e:
            st.error(f"Error saving ingredient ratings: {str(e)}")
            st.code(traceback.format_exc())
            return False

    # Generate CSV from Firebase data
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
            
            # Create DataFrame
            df = pd.DataFrame(ratings_data)
            
            # If the DataFrame is empty, create the column structure
            if df.empty:
                df = pd.DataFrame(columns=['user_id', 'recipe_id', 'recipe_name', 'rating', 'timestamp'])
            
            # Save to CSV
            csv_path = "recipe_ratings_database.csv"
            df.to_csv(csv_path, index=False)
            
            return csv_path
        except Exception as e:
            st.error(f"Error generating CSV: {str(e)}")
            st.code(traceback.format_exc())
            return None

    # Function to get user's rated recipes
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

    # Display recipe with rating
    def display_recipe(recipe, key_prefix, ratings_dict):
        with st.expander(f"{recipe['title']}"):
            col1, col2 = st.columns([1, 2])
            
            recipe_id = recipe['id']
            recipe_name = recipe['title']
            
            # Initialize this recipe in the ratings dictionary if not present
            if recipe_id not in ratings_dict:
                ratings_dict[recipe_id] = {'name': recipe_name, 'rating': 0}
            
            with col1:
                # Display recipe image
                if 'image' in recipe and recipe['image']:
                    st.image(recipe['image'], width=200)
                else:
                    st.write("No image available")
                
                # Rating system
                ratings_dict[recipe_id]['rating'] = st.slider(
                    "Rate this recipe", 
                    0, 5, 
                    ratings_dict[recipe_id]['rating'],  # Use current value
                    key=f"{key_prefix}_slider_{recipe_id}"
                )
            
            with col2:
                # Display recipe details
                # Health information
                health_info = []
                if 'healthScore' in recipe:
                    health_info.append(f"Health Score: {recipe['healthScore']}/100")
                
                if 'diets' in recipe and recipe['diets']:
                    health_info.append(f"Diets: {', '.join(recipe['diets'])}")
                
                if health_info:
                    st.markdown("### Health Information")
                    for info in health_info:
                        st.markdown(f"- {info}")
                
                # Nutrition info if available
                if 'nutrition' in recipe and 'nutrients' in recipe['nutrition']:
                    st.markdown("### Nutrition Facts")
                    nutrients = recipe['nutrition']['nutrients']
                    # Dictionary to store the specific nutrients we want
                    nutrient_values = {
                        'Calories': '0 kcal',
                        'Fat': '0 g',
                        'Protein': '0 g',
                        'Carbohydrates': '0 g'
                    }
                    
                    # Find the specific nutrients we want
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
                    
                    # Display the specific nutrients
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

    # Function to get recommended recipes
    def get_recommendations(db, user_id):
        if not db:
            return [], "Database connection not established. Cannot generate recommendations."
        
        try:
            # Check if user has any ratings
            user_ratings = get_user_ratings(db, user_id)
            
            if not user_ratings:
                return [], "You haven't rated any recipes yet. Rate some recipes to get personalized recommendations."
            
            # Simple recommendation stub (without Model_Alpha)
            return [], "Recommendation feature is currently under maintenance. Please check back later."
            
        except Exception as e:
            st.error(f"Recommendation processing error: {str(e)}")
            st.code(traceback.format_exc())
            return [], f"Error processing recommendations: {str(e)}"

    # Streamlit UI
    def main():
        st.title("Healthy Recipe Finder")
        
        # Initialize Firebase
        db = initialize_firebase()
        
        if not db:
            st.error("Failed to connect to Firebase. Please check your configuration.")
            st.stop()
        
        # Session state initialization
        if 'searched_recipes' not in st.session_state:
            st.session_state.searched_recipes = []
        
        if 'ratings' not in st.session_state:
            st.session_state.ratings = {}
        
        if 'ingredient_ratings' not in st.session_state:
            # Initialize with default ratings
            st.session_state.ingredient_ratings = DEFAULT_INGREDIENT_RATINGS.copy()
        
        if 'search_performed' not in st.session_state:
            st.session_state.search_performed = False
        
        # Fixed email ID instead of user input
        email = _email
        
        # App tabs - Swapped the order of My Ratings and Recommendations
        tab1, tab2, tab4, tab3 = st.tabs(["Find Recipes", "Rate Ingredients", "Recommendations", "My Ratings"])
        
        # Tab 1: Find Recipes
        with tab1:
            st.header("Find Healthy Recipes")
            
            with st.form("recipe_search_form"):
                # Country Selection
                countries = [
                    "Select Country", "United States", "United Kingdom", "Italy", "France", 
                    "China", "Japan", "India", "Mexico", "Thailand", "Spain", "Greece", 
                    "Germany", "Vietnam", "Korea", "Lebanon", "Morocco", "Turkey", 
                    "Brazil", "Argentina", "Ethiopia", "Nigeria", "Sweden", "Denmark"
                ]
                selected_country = st.selectbox("Select your country", countries)
                
                # Changed from multiselect to single select dropdown
                ingredients_list = ["Select Ingredient"] + COMMON_INGREDIENTS
                selected_ingredient = st.selectbox(
                    "Select an ingredient", 
                    options=ingredients_list
                )
                
                recipe_name_search = st.text_input("Search recipes by name", "")
                
                # Search button
                search_submitted = st.form_submit_button("Search Recipes")
                
                if search_submitted:
                    if selected_country == "Select Country":
                        st.warning("Please select a country")
                    elif selected_ingredient == "Select Ingredient" and not recipe_name_search:
                        st.warning("Please select an ingredient or enter a recipe name")
                    else:
                        # Create a list with the single selected ingredient (if not "Select Ingredient")
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
                                    # Clear previous ratings for new search
                                    st.session_state.ratings = {}
                                else:
                                    st.warning("No recipes found. Try different ingredients or search terms.")
                                    st.session_state.searched_recipes = []
            
            # Display recipes and collect ratings
            if st.session_state.search_performed and st.session_state.searched_recipes:
                st.header("Results")
                
                # Display each recipe with rating slider
                for recipe in st.session_state.searched_recipes:
                    display_recipe(recipe, "search", st.session_state.ratings)
                
                # Save all ratings button
                if st.button("Save All Ratings"):
                    if any(data['rating'] > 0 for data in st.session_state.ratings.values()):
                        save_ratings_to_firebase(db, email, st.session_state.ratings)
                        # Clear ratings after saving
                        st.session_state.ratings = {}
                    else:
                        st.warning("Please rate at least one recipe before saving.")
        
        # Tab 2: Rate Ingredients
        with tab2:
            st.header("Rate Your Favorite Ingredients")
            st.write("Rate ingredients based on your preference on a scale of 0 to 5. These ratings will help us provide better recommendations.")
            
            # Create a 2-column layout for ingredients
            col1, col2 = st.columns(2)
            
            # Get sorted default ingredients for display
            ingredients_to_rate = sorted(list(st.session_state.ingredient_ratings.keys()))
            
            # Display ingredients for rating
            for i, ingredient in enumerate(ingredients_to_rate):
                # Determine which column to place the ingredient in
                col = col1 if i % 2 == 0 else col2
                
                # Get existing rating or default to 0
                current_rating = st.session_state.ingredient_ratings.get(ingredient, 0)
                
                # Show rating slider
                with col:
                    st.session_state.ingredient_ratings[ingredient] = st.slider(
                        f"{ingredient}", 
                        0, 5, 
                        int(current_rating),
                        key=f"ing_rate_{i}"
                    )
            
            # Save ratings button
            if st.button("Save Ingredient Ratings"):
                if st.session_state.ingredient_ratings and any(rating > 0 for rating in st.session_state.ingredient_ratings.values()):
                    save_ingredient_ratings_to_firebase(db, email, st.session_state.ingredient_ratings)
                    st.success("Ingredient ratings saved successfully!")
                else:
                    st.warning("Please rate at least one ingredient before saving.")
        
        # Tab 4 (now in 3rd position): Recommendations
        with tab4:
            st.header("Personalized Recipe Recommendations")
            
            st.write("Based on your ratings, we think you might enjoy these recipes:")
            
            # Get recommendations
            with st.spinner("Generating recommendations..."):
                recommendations, error_msg = get_recommendations(db, email)
            
            if error_msg:
                st.info(error_msg)
            elif recommendations:
                # Display recommendations
                st.success(f"Found {len(recommendations)} recommendations for you!")
                
                # Create a filter sidebar within the tab
                available_cuisines = ["All Cuisines"] + list(set([r.get('cuisine', 'Unknown') for r in recommendations if 'cuisine' in r]))
                rec_cuisine_filter = st.selectbox(
                    "Filter by cuisine", 
                    available_cuisines
                )
                
                # Filter based on selection
                filtered_recs = recommendations
                if rec_cuisine_filter != "All Cuisines":
                    filtered_recs = [r for r in recommendations if r.get('cuisine', '') == rec_cuisine_filter]
                
                # Display each recommendation
                for i, rec in enumerate(filtered_recs):
                    with st.expander(f"{i+1}. {rec.get('recipe_name', 'Recipe')} - Score: {rec.get('score', 'N/A')}"):
                        # Display recipe details
                        st.write(f"**Recipe ID:** {rec.get('recipe_id', 'Unknown')}")
                        if 'cuisine' in rec:
                            st.write(f"**Cuisine:** {rec.get('cuisine', 'Unknown')}")
                        
                        # Add a button to search for this recipe
                        if st.button(f"Find this recipe", key=f"find_rec_{i}"):
                            # Store in session state to trigger a search in the Find Recipes tab
                            st.session_state.search_recipe_id = rec.get('recipe_id', '')
                            st.rerun()
            else:
                st.info("No recommendations available. Try rating more recipes first.")
        
        # Tab 3 (now in 4th position): My Ratings
        with tab3:
            st.header("Your Saved Ratings")
            
            # Add refresh button
            if st.button("Refresh Ratings"):
                st.rerun()
            
            # Show user ratings
            user_ratings = get_user_ratings(db, email)
            if user_ratings:
                st.success(f"You have rated {len(user_ratings)} recipes so far.")
                
                # Display ratings in a table
                ratings_df = pd.DataFrame(user_ratings)
                if not ratings_df.empty:
                    # Select only relevant columns and rename them
                    display_columns = ['recipe_name', 'rating']
                    if 'timestamp' in ratings_df.columns:
                        display_columns.append('timestamp')
                    
                    # Make sure all columns exist before filtering
                    available_columns = [col for col in display_columns if col in ratings_df.columns]
                    ratings_df = ratings_df[available_columns]
                    
                    column_rename = {
                        'recipe_name': 'Recipe Name',
                        'rating': 'Your Rating'
                    }
                    
                    if 'timestamp' in available_columns:
                        column_rename['timestamp'] = 'Rated On'
                    
                    ratings_df = ratings_df.rename(columns=column_rename)
                    
                    # Sort by rating (highest first)
                    if 'Your Rating' in ratings_df.columns:
                        ratings_df = ratings_df.sort_values(by='Your Rating', ascending=False)
                    
                    st.dataframe(ratings_df, use_container_width=True)
            else:
                st.info("You haven't saved any ratings yet. Start rating recipes to see them here!")
                
            # Show ingredient ratings
            st.subheader("Your Ingredient Preferences")
            
            # Convert ingredient ratings to DataFrame for display
            ing_df = pd.DataFrame(list(st.session_state.ingredient_ratings.items()), columns=['Ingredient', 'Your Rating'])
            ing_df = ing_df.sort_values(by='Your Rating', ascending=False)
            st.dataframe(ing_df, use_container_width=True)

    if __name__ == "__main__":
        main()
#print(mod.recommend('bbb@gmail.com'))