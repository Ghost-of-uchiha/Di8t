import streamlit as st
import pandas as pd
import plotly.express as px
import random

def generate_diet_plan(user_data):
    """
    Generate a personalized weekly diet plan based on user survey data
    
    Parameters:
    user_data (dict): User survey responses containing preferences and metrics
    
    Returns:
    dict: Weekly diet plan with meals and nutrition recommendations
    """
    # Extract key information from user data
    bmi_category = user_data.get('bmi_category', 'Normal weight')
    diet_preference = user_data.get('diet_preference', 'Non-vegetarian')
    food_allergies = user_data.get('food_allergies', [])
    activity_level = user_data.get('activity_level', 'Moderately active')
    fitness_goal = user_data.get('fitness_goal', 'Maintenance')
    meals_per_day = user_data.get('meals_per_day', 3)
    cooking_time = user_data.get('cooking_time', 30)
    cooking_skill = user_data.get('cooking_skill', 'Intermediate')
    health_conditions = user_data.get('health_conditions', [])
    
    # Initialize diet plan dictionary
    diet_plan = {
        'breakfast': [],
        'morning_snack': [],
        'lunch': [],
        'afternoon_snack': [],
        'dinner': [],
        'evening_snack': [],
        'nutrition_tips': [],
        'hydration': "Drink 8-10 glasses of water daily. Increase by 2-3 glasses on workout days.",
        'metrics': {
            'calories': calculate_calories(user_data),
            'protein': calculate_protein(user_data),
            'carbs': calculate_carbs(user_data),
            'fats': calculate_fats(user_data)
        }
    }
    
    # ===== FOOD DATABASE BY DIET PREFERENCE =====
    food_db = create_food_database(diet_preference, food_allergies)
    
    # ===== GENERATE WEEKLY MEAL PLAN =====
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekly_plan = {day: {} for day in days}
    
    for day in days:
        # Core meals (always included)
        weekly_plan[day]['breakfast'] = random.choice(food_db['breakfast'])
        weekly_plan[day]['lunch'] = random.choice(food_db['lunch'])
        weekly_plan[day]['dinner'] = random.choice(food_db['dinner'])
        
        # Add snacks based on meals_per_day
        if meals_per_day >= 4:
            weekly_plan[day]['morning_snack'] = random.choice(food_db['snacks'])
        if meals_per_day >= 5:
            weekly_plan[day]['afternoon_snack'] = random.choice(food_db['snacks'])
        if meals_per_day >= 6:
            weekly_plan[day]['evening_snack'] = random.choice(food_db['snacks'])
    
    # ===== NUTRITION TIPS =====
    nutrition_tips = generate_nutrition_tips(user_data)
    
    # Complete the diet plan
    diet_plan['weekly_meals'] = weekly_plan
    diet_plan['nutrition_tips'] = nutrition_tips
    
    return diet_plan

def calculate_calories(user_data):
    """Calculate recommended daily calorie intake"""
    weight = user_data.get('weight', 70)
    height = user_data.get('height', 170)
    age = user_data.get('age', 30)
    gender = user_data.get('gender', 'Male')
    activity_level = user_data.get('activity_level', 'Moderately active')
    fitness_goal = user_data.get('fitness_goal', 'Maintenance')
    
    # Calculate BMR (Basal Metabolic Rate) using Mifflin-St Jeor equation
    if gender == 'Male':
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161
    
    # Activity multiplier
    activity_multipliers = {
        'Sedentary (office job, little exercise)': 1.2,
        'Lightly active (light exercise 1-3 days/week)': 1.375,
        'Moderately active (moderate exercise 3-5 days/week)': 1.55,
        'Very active (hard exercise 6-7 days/week)': 1.725,
        'Extremely active (physical job & hard exercise)': 1.9
    }
    
    # Fitness goal adjustment
    goal_adjustments = {
        'Weight loss': 0.8,
        'Muscle gain': 1.1,
        'Maintenance': 1.0,
        'Improve overall health': 1.0,
        'Athletic performance': 1.15
    }
    
    # Calculate TDEE (Total Daily Energy Expenditure)
    activity_multiplier = activity_multipliers.get(activity_level, 1.55)
    goal_adjustment = goal_adjustments.get(fitness_goal, 1.0)
    
    calories = int(bmr * activity_multiplier * goal_adjustment)
    
    # Ensure minimum healthy calorie intake
    min_calories = 1200 if gender != 'Male' else 1500
    if calories < min_calories:
        calories = min_calories
    
    return calories

def calculate_protein(user_data):
    """Calculate recommended daily protein intake in grams"""
    weight = user_data.get('weight', 70)  # in kg
    fitness_goal = user_data.get('fitness_goal', 'Maintenance')
    
    # Protein factors based on fitness goal (g per kg of body weight)
    protein_factors = {
        'Weight loss': 1.6,
        'Muscle gain': 2.0,
        'Maintenance': 1.2,
        'Improve overall health': 1.2,
        'Athletic performance': 1.8
    }
    
    factor = protein_factors.get(fitness_goal, 1.2)
    protein_grams = int(weight * factor)
    
    return protein_grams

def calculate_carbs(user_data):
    """Calculate recommended daily carbohydrate intake in grams"""
    calories = calculate_calories(user_data)
    fitness_goal = user_data.get('fitness_goal', 'Maintenance')
    
    # Carb percentages based on fitness goal
    carb_percentages = {
        'Weight loss': 0.4,
        'Muscle gain': 0.5,
        'Maintenance': 0.5,
        'Improve overall health': 0.45,
        'Athletic performance': 0.55
    }
    
    percentage = carb_percentages.get(fitness_goal, 0.5)
    carb_calories = calories * percentage
    carb_grams = int(carb_calories / 4)  # 4 calories per gram of carbs
    
    return carb_grams

def calculate_fats(user_data):
    """Calculate recommended daily fat intake in grams"""
    calories = calculate_calories(user_data)
    protein_grams = calculate_protein(user_data)
    carb_grams = calculate_carbs(user_data)
    
    # Calculate remaining calories after protein and carbs
    protein_calories = protein_grams * 4  # 4 calories per gram of protein
    carb_calories = carb_grams * 4  # 4 calories per gram of carbs
    fat_calories = calories - protein_calories - carb_calories
    
    # Convert to grams (9 calories per gram of fat)
    fat_grams = int(fat_calories / 9)
    
    # Ensure minimum healthy fat intake (at least 20% of calories)
    min_fat_grams = int((calories * 0.2) / 9)
    if fat_grams < min_fat_grams:
        fat_grams = min_fat_grams
    
    return fat_grams

def create_food_database(diet_preference, food_allergies):
    """Create a food database filtered by diet preference and allergies"""
    # Initialize the food database
    food_db = {
        'breakfast': [],
        'lunch': [],
        'dinner': [],
        'snacks': []
    }
    
    # ===== BREAKFAST OPTIONS =====
    vegetarian_breakfast = [
        "Greek yogurt with berries and honey",
        "Oatmeal with sliced banana and cinnamon",
        "Whole grain toast with avocado and eggs",
        "Spinach and mushroom omelette with whole grain toast",
        "Breakfast smoothie (banana, berries, yogurt, spinach)",
        "Overnight chia pudding with mixed berries",
        "Whole grain pancakes with fresh fruit",
        "Vegetable frittata with side of fruit"
    ]
    
    vegan_breakfast = [
        "Overnight oats with almond milk and berries",
        "Tofu scramble with vegetables",
        "Whole grain toast with avocado and tomato",
        "Chia seed pudding with coconut milk and fruit",
        "Smoothie bowl with granola and fresh fruit",
        "Vegan breakfast wrap with vegetables and hummus",
        "Whole grain cereal with plant-based milk and banana",
        "Avocado toast with nutritional yeast"
    ]
    
    non_veg_breakfast = vegetarian_breakfast + [
        "Scrambled eggs with turkey bacon",
        "Smoked salmon on whole grain toast with cream cheese",
        "Turkey and vegetable breakfast wrap",
        "Chicken and vegetable breakfast burrito",
        "Lean ham omelette with vegetables"
    ]
    
    # ===== LUNCH OPTIONS =====
    vegetarian_lunch = [
        "Mediterranean salad with feta cheese and olive oil dressing",
        "Quinoa bowl with roasted vegetables and chickpeas",
        "Veggie wrap with hummus and mixed greens",
        "Lentil soup with whole grain bread",
        "Caprese sandwich with tomato and mozzarella",
        "Spinach and feta quesadilla with side salad",
        "Vegetable stir-fry with tofu and brown rice",
        "Bean and cheese burrito with salsa"
    ]
    
    vegan_lunch = [
        "Buddha bowl with quinoa, roasted vegetables, and tahini dressing",
        "Black bean and vegetable soup",
        "Chickpea salad sandwich on whole grain bread",
        "Lentil and vegetable curry with brown rice",
        "Vegan wrap with hummus and mixed vegetables",
        "Quinoa salad with mixed vegetables and lemon dressing",
        "Vegan burrito bowl with beans, rice, and guacamole",
        "Roasted vegetable and hummus sandwich"
    ]
    
    non_veg_lunch = [
        "Grilled chicken salad with olive oil dressing",
        "Turkey and avocado wrap with mixed greens",
        "Tuna salad sandwich on whole grain bread",
        "Chicken and vegetable stir-fry with brown rice",
        "Salmon with quinoa and steamed vegetables",
        "Lean beef and vegetable soup with whole grain bread",
        "Chicken and vegetable curry with brown rice",
        "Grilled fish tacos with cabbage slaw"
    ]
    
    # ===== DINNER OPTIONS =====
    vegetarian_dinner = [
        "Eggplant parmesan with side salad",
        "Vegetable lasagna with ricotta cheese",
        "Black bean burgers with sweet potato fries",
        "Mushroom risotto with parmesan cheese",
        "Stuffed bell peppers with quinoa and cheese",
        "Spinach and ricotta stuffed shells",
        "Vegetable curry with brown rice",
        "Lentil and vegetable soup with whole grain bread"
    ]
    
    vegan_dinner = [
        "Lentil and vegetable curry with brown rice",
        "Roasted vegetable and quinoa bowl",
        "Black bean and sweet potato chili",
        "Vegan pasta with tomato sauce and vegetables",
        "Chickpea and vegetable stew",
        "Stir-fried tofu with vegetables and brown rice",
        "Stuffed bell peppers with quinoa and beans",
        "Vegan shepherd's pie with lentils"
    ]
    
    non_veg_dinner = [
        "Grilled salmon with roasted vegetables",
        "Baked chicken with quinoa and steamed broccoli",
        "Turkey meatballs with whole wheat pasta and marinara",
        "Lean beef stir-fry with vegetables and brown rice",
        "Shrimp and vegetable skewers with quinoa",
        "Baked cod with roasted sweet potatoes and vegetables",
        "Grilled chicken with mushroom sauce and steamed vegetables",
        "Turkey chili with vegetables and beans"
    ]
    
    # ===== SNACK OPTIONS =====
    vegetarian_snacks = [
        "Greek yogurt with honey",
        "Apple slices with nut butter",
        "Hummus with vegetable sticks",
        "Trail mix with nuts and dried fruit",
        "Cheese and whole grain crackers",
        "Cottage cheese with pineapple",
        "Hard-boiled eggs",
        "Smoothie with yogurt and berries"
    ]
    
    vegan_snacks = [
        "Apple slices with almond butter",
        "Hummus with vegetable sticks",
        "Trail mix with nuts and dried fruit",
        "Roasted chickpeas",
        "Rice cakes with avocado",
        "Fruit and nut bars",
        "Edamame",
        "Smoothie with plant-based milk"
    ]
    
    non_veg_snacks = vegetarian_snacks + [
        "Turkey and cheese roll-ups",
        "Tuna on whole grain crackers",
        "Beef jerky (low sodium)",
        "Chicken and vegetable skewers"
    ]
    
    # Assign appropriate food lists based on diet preference
    if diet_preference == 'Vegan':
        food_db['breakfast'] = vegan_breakfast
        food_db['lunch'] = vegan_lunch
        food_db['dinner'] = vegan_dinner
        food_db['snacks'] = vegan_snacks
    elif diet_preference == 'Vegetarian':
        food_db['breakfast'] = vegetarian_breakfast
        food_db['lunch'] = vegetarian_lunch
        food_db['dinner'] = vegetarian_dinner
        food_db['snacks'] = vegetarian_snacks
    elif diet_preference == 'Pescatarian':
        # For pescatarian, filter out meat options but keep fish
        food_db['breakfast'] = vegetarian_breakfast + [item for item in non_veg_breakfast if 'salmon' in item.lower() or 'fish' in item.lower()]
        food_db['lunch'] = vegetarian_lunch + [item for item in non_veg_lunch if 'tuna' in item.lower() or 'salmon' in item.lower() or 'fish' in item.lower()]
        food_db['dinner'] = vegetarian_dinner + [item for item in non_veg_dinner if 'salmon' in item.lower() or 'shrimp' in item.lower() or 'cod' in item.lower() or 'fish' in item.lower()]
        food_db['snacks'] = vegetarian_snacks + [item for item in non_veg_snacks if 'tuna' in item.lower()]
    else:  # Non-vegetarian or Flexitarian
        food_db['breakfast'] = non_veg_breakfast
        food_db['lunch'] = non_veg_lunch
        food_db['dinner'] = non_veg_dinner
        food_db['snacks'] = non_veg_snacks
    
    # Filter out allergies
    if food_allergies and 'None' not in food_allergies:
        for meal_type in food_db:
            filtered_meals = []
            for meal in food_db[meal_type]:
                if not any(allergen.lower() in meal.lower() for allergen in food_allergies):
                    filtered_meals.append(meal)
            food_db[meal_type] = filtered_meals
    
    return food_db

def generate_nutrition_tips(user_data):
    """Generate personalized nutrition tips based on user data"""
    bmi_category = user_data.get('bmi_category', 'Normal weight')
    fitness_goal = user_data.get('fitness_goal', 'Maintenance')
    health_conditions = user_data.get('health_conditions', [])
    
    general_tips = [
        "Aim to eat a rainbow of fruits and vegetables daily for a wide range of nutrients.",
        "Stay hydrated by drinking water throughout the day, especially before meals.",
        "Limit processed foods and focus on whole, unprocessed foods.",
        "Include protein with each meal to help maintain muscle and feel satisfied.",
        "Don't skip meals, especially breakfast, to maintain energy levels.",
        "Practice mindful eating by eating slowly and without distractions.",
        "Prepare meals at home when possible to control ingredients and portion sizes.",
        "Read food labels to understand what you're consuming."
    ]
    
    # Goal-specific tips
    weight_loss_tips = [
        "Focus on creating a small calorie deficit through diet and exercise.",
        "Fill half your plate with non-starchy vegetables to stay full with fewer calories.",
        "Use smaller plates to help with portion control.",
        "Keep a food journal to increase awareness of eating habits.",
        "Plan meals ahead to avoid impulsive, less healthy choices."
    ]
    
    muscle_gain_tips = [
        "Ensure you're eating enough calories to support muscle growth.",
        "Consume protein within 30 minutes after strength training.",
        "Include quality carbohydrates to fuel workouts and support recovery.",
        "Focus on progressive overload in your strength training.",
        "Ensure adequate recovery between workouts targeting the same muscle groups."
    ]
    
    health_condition_tips = {
        "Diabetes": [
            "Monitor carbohydrate intake and focus on complex carbs with fiber.",
            "Maintain consistent meal timing to help regulate blood sugar.",
            "Include protein with each meal to slow glucose absorption.",
            "Limit added sugars and refined carbohydrates."
        ],
        "Hypertension": [
            "Limit sodium intake by reducing processed foods.",
            "Increase potassium-rich foods like bananas, potatoes, and leafy greens.",
            "Consider the DASH diet approach, which is designed to lower blood pressure.",
            "Limit alcohol consumption."
        ],
        "Heart disease": [
            "Focus on heart-healthy fats like those in olive oil, avocados, and fatty fish.",
            "Limit saturated and trans fats found in fried foods and baked goods.",
            "Include soluble fiber from oats, beans, and fruits to help lower cholesterol.",
            "Consider a Mediterranean-style eating pattern."
        ],
        "Digestive issues": [
            "Identify and limit foods that trigger symptoms.",
            "Eat smaller, more frequent meals if large meals cause discomfort.",
            "Stay well-hydrated to support digestive function.",
            "Consider incorporating probiotics from yogurt or fermented foods."
        ]
    }
    
    # Compile tips based on user profile
    tips = general_tips.copy()
    
    if fitness_goal == 'Weight loss':
        tips.extend(weight_loss_tips)
    elif fitness_goal == 'Muscle gain':
        tips.extend(muscle_gain_tips)
    
    # Add health condition specific tips
    for condition in health_conditions:
        if condition in health_condition_tips and condition != 'None':
            tips.extend(health_condition_tips[condition])
    
    # Select a subset of tips to avoid overwhelming the user
    if len(tips) > 10:
        tips = random.sample(tips, 10)
    
    return tips

def display_diet_chart(user_data, diet_plan):
    """Display the personalized diet chart in Streamlit"""
    st.title("🥗 Your Personalized Weekly Diet Plan")
    
    # Display user info at the top
    st.subheader("📊 Your Health Profile")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("BMI", f"{user_data.get('bmi', 'N/A')}", 
                 f"{user_data.get('bmi_category', 'N/A')}")
    with col2:
        st.metric("Goal", f"{user_data.get('fitness_goal', 'N/A')}")
    with col3:
        st.metric("Activity Level", f"{user_data.get('activity_level', 'N/A').split(' ')[0]}")
    
    # Display daily nutrition targets
    st.subheader("🎯 Daily Nutrition Targets")
    metrics = diet_plan.get('metrics', {})
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Calories", f"{metrics.get('calories', 'N/A')} kcal")
    with col2:
        st.metric("Protein", f"{metrics.get('protein', 'N/A')}g")
    with col3:
        st.metric("Carbs", f"{metrics.get('carbs', 'N/A')}g")
    with col4:
        st.metric("Fats", f"{metrics.get('fats', 'N/A')}g")
    
    # Macronutrient distribution chart
    macros_data = {
        'Nutrient': ['Protein', 'Carbs', 'Fats'],
        'Grams': [metrics.get('protein', 0), 
                 metrics.get('carbs', 0), 
                 metrics.get('fats', 0)],
        'Calories': [metrics.get('protein', 0) * 4, 
                    metrics.get('carbs', 0) * 4, 
                    metrics.get('fats', 0) * 9]
    }
    
    fig = px.pie(
        names=macros_data['Nutrient'],
        values=macros_data['Calories'],
        title='Calorie Distribution by Macronutrient'
    )
    st.plotly_chart(fig)
    
    # Weekly meal plan in tabs
    st.subheader("📅 Weekly Meal Plan")
    
    # Create tabs for each day
    days = list(diet_plan.get('weekly_meals', {}).keys())
    tabs = st.tabs(days)
    
    for i, day in enumerate(days):
        with tabs[i]:
            day_meals = diet_plan.get('weekly_meals', {}).get(day, {})
            
            # Morning
            st.markdown("#### 🌅 Morning")
            st.markdown(f"**Breakfast:** {day_meals.get('breakfast', 'Not specified')}")
            if 'morning_snack' in day_meals:
                st.markdown(f"**Morning Snack:** {day_meals.get('morning_snack', 'Not specified')}")
            
            # Afternoon
            st.markdown("#### ☀️ Afternoon")
            st.markdown(f"**Lunch:** {day_meals.get('lunch', 'Not specified')}")
            if 'afternoon_snack' in day_meals:
                st.markdown(f"**Afternoon Snack:** {day_meals.get('afternoon_snack', 'Not specified')}")
            
            # Evening
            st.markdown("#### 🌙 Evening")
            st.markdown(f"**Dinner:** {day_meals.get('dinner', 'Not specified')}")
            if 'evening_snack' in day_meals:
                st.markdown(f"**Evening Snack:** {day_meals.get('evening_snack', 'Not specified')}")
    
    # Nutrition tips
    st.subheader("💡 Nutrition Tips")
    tips = diet_plan.get('nutrition_tips', [])
    for i, tip in enumerate(tips, 1):
        st.markdown(f"{i}. {tip}")