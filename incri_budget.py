import streamlit as st
import pandas as pd
import random

# Sample ingredient data with categories
default_ingredients = {
    'Vegetables': ['Tomatoes', 'Onions', 'Potatoes', 'Carrots', 'Broccoli', 'Spinach', 'Bell Peppers'],
    'Fruits': ['Apples', 'Bananas', 'Oranges', 'Grapes', 'Strawberries'],
    'Protein': ['Chicken', 'Beef', 'Fish', 'Eggs', 'Tofu'],
    'Grains': ['Rice', 'Pasta', 'Bread', 'Oats', 'Quinoa'],
    'Dairy': ['Milk', 'Cheese', 'Yogurt', 'Butter'],
    'Others': ['Olive Oil', 'Sugar', 'Salt', 'Black Pepper', 'Flour']
}

# More realistic base costs for ingredients (in USD per kg or equivalent standard unit)
# These are standard reference prices before regional adjustments
base_ingredient_costs = {
    # Vegetables - price per kg in USD
    'Tomatoes': 2.0, 'Onions': 1.2, 'Potatoes': 1.0, 'Carrots': 1.3, 
    'Broccoli': 2.5, 'Spinach': 3.0, 'Bell Peppers': 3.5,
    # Fruits - price per kg in USD
    'Apples': 2.5, 'Bananas': 1.2, 'Oranges': 2.0, 'Grapes': 4.0, 'Strawberries': 5.0,
    # Protein - price per kg in USD
    'Chicken': 6.0, 'Beef': 10.0, 'Fish': 8.0, 'Eggs': 3.0, 'Tofu': 4.0,
    # Grains - price per kg in USD
    'Rice': 1.5, 'Pasta': 2.0, 'Bread': 3.0, 'Oats': 2.5, 'Quinoa': 5.0,
    # Dairy - price per kg/liter in USD
    'Milk': 1.2, 'Cheese': 8.0, 'Yogurt': 2.0, 'Butter': 8.0,
    # Others - price per standard unit in USD
    'Olive Oil': 10.0, 'Sugar': 1.0, 'Salt': 0.8, 'Black Pepper': 15.0, 'Flour': 1.2
}

# Direct regional price overrides - this is the key improvement
# These are actual market prices in local currency per local unit
regional_prices = {
    'India': {
        # Prices in INR per kg
        'Tomatoes': 30.0,  # ₹30 per kg as mentioned
        'Onions': 25.0,
        'Potatoes': 20.0,
        'Carrots': 40.0,
        'Spinach': 30.0,
        'Bell Peppers': 60.0,
        'Apples': 120.0,
        'Bananas': 40.0,
        'Oranges': 80.0,
        'Grapes': 100.0,
        'Rice': 50.0,
        'Chicken': 200.0,
        'Eggs': 7.0,  # per egg
        'Milk': 50.0,  # per liter
        # Other ingredients will use conversion from base
    },
    'United States': {
        # Prices in USD per pound for many items
        'Tomatoes': 2.5,  # per lb
        'Onions': 1.0,  # per lb
        'Potatoes': 0.8,  # per lb
        'Chicken': 3.5,  # per lb
        'Beef': 5.5,  # per lb
        'Milk': 3.5,  # per gallon
        # Other ingredients will use base prices with regional modifier
    },
    'United Kingdom': {
        # Prices in GBP per kg
        'Tomatoes': 2.0,
        'Onions': 1.0,
        'Potatoes': 1.1,
        'Milk': 1.2,  # per liter
        # Other ingredients will use conversion from base
    }
    # Other countries can be added with their local prices
}

# Cost modifiers based on regions (for prices not directly specified)
region_cost_modifiers = {
    'United States': {
        'California': 1.4,
        'New York': 1.5,
        'Texas': 1.1,
        'Florida': 1.2,
        'DEFAULT': 1.2  # Default for other states
    },
    'India': {
        'Maharashtra': 1.2,
        'Delhi': 1.3,
        'Karnataka': 1.1,
        'DEFAULT': 1.0
    },
    'United Kingdom': {'DEFAULT': 1.3},
    'DEFAULT': 1.0  # Default for countries not specifically listed
}

# Units by country and ingredient category
units_by_country = {
    'United States': {
        'Vegetables': 'lb',
        'Fruits': 'lb',
        'Protein': 'lb',
        'Grains': 'lb',
        'Dairy': {
            'Milk': 'gallon',
            'Cheese': 'lb',
            'Yogurt': 'oz',
            'Butter': 'lb'
        },
        'Others': {
            'Olive Oil': 'fl oz',
            'Sugar': 'lb',
            'Salt': 'oz',
            'Black Pepper': 'oz',
            'Flour': 'lb'
        }
    },
    'India': {
        'Vegetables': 'kg',
        'Fruits': 'kg',
        'Protein': 'kg',
        'Grains': 'kg',
        'Dairy': {
            'Milk': 'liter',
            'Cheese': 'kg',
            'Yogurt': 'kg',
            'Butter': 'kg'
        },
        'Others': {
            'Olive Oil': 'ml',
            'Sugar': 'kg',
            'Salt': 'kg',
            'Black Pepper': 'g',
            'Flour': 'kg'
        }
    },
    'United Kingdom': {
        'Vegetables': 'kg',
        'Fruits': 'kg',
        'Protein': 'kg',
        'Grains': 'kg',
        'Dairy': {
            'Milk': 'liter',
            'Cheese': 'kg',
            'Yogurt': 'kg',
            'Butter': 'kg'
        },
        'Others': {
            'Olive Oil': 'ml',
            'Sugar': 'kg',
            'Salt': 'kg',
            'Black Pepper': 'g',
            'Flour': 'kg'
        }
    },
    'DEFAULT': {
        'Vegetables': 'kg',
        'Fruits': 'kg',
        'Protein': 'kg',
        'Grains': 'kg',
        'Dairy': {
            'Milk': 'liter',
            'Cheese': 'kg',
            'Yogurt': 'kg',
            'Butter': 'kg'
        },
        'Others': {
            'Olive Oil': 'ml',
            'Sugar': 'kg',
            'Salt': 'kg',
            'Black Pepper': 'g',
            'Flour': 'kg'
        }
    }
}

# Conversion factors to standardize pricing 
conversion_factors = {
    'lb_to_kg': 2.20462,  # 1 kg = 2.20462 lb
    'oz_to_g': 28.3495,   # 1 oz = 28.3495 g
    'fl_oz_to_ml': 29.5735,  # 1 fl oz = 29.5735 ml
    'gallon_to_liter': 3.78541  # 1 gallon = 3.78541 liters
}

# Currency conversion rates (approximate)
currency_conversion = {
    'United States': {'symbol': '$', 'rate': 1.0},
    'India': {'symbol': '₹', 'rate': 75.0},  # 1 USD = ~75 INR
    'United Kingdom': {'symbol': '£', 'rate': 0.75},  # 1 USD = ~0.75 GBP
    'DEFAULT': {'symbol': '$', 'rate': 1.0}  # Default to USD
}

# Standard units for reference (for displaying universal pricing)
standard_units = {
    'Vegetables': 'kg',
    'Fruits': 'kg',
    'Protein': 'kg',
    'Grains': 'kg',
    'Dairy': {
        'Milk': 'liter',
        'Cheese': 'kg',
        'Yogurt': 'kg',
        'Butter': 'kg'
    },
    'Others': {
        'Olive Oil': 'liter',
        'Sugar': 'kg',
        'Salt': 'kg',
        'Black Pepper': 'kg',
        'Flour': 'kg'
    }
}

def get_all_default_ingredients():
    """Get all ingredients from default ingredients dictionary"""
    all_ingredients = []
    for category, items in default_ingredients.items():
        all_ingredients.extend(items)
    return all_ingredients

def get_ingredient_category(ingredient):
    """Find which category an ingredient belongs to"""
    for category, items in default_ingredients.items():
        if ingredient in items:
            return category
    return None

def get_unit_for_ingredient(ingredient, country):
    """Get the appropriate unit for an ingredient based on country"""
    category = get_ingredient_category(ingredient)
    if not category:
        return "unit"  # Default unit if category not found
    
    country_units = units_by_country.get(country, units_by_country['DEFAULT'])
    category_unit = country_units.get(category, "unit")
    
    # Handle nested dictionaries for specific ingredients
    if isinstance(category_unit, dict):
        return category_unit.get(ingredient, "unit")
    
    return category_unit

def get_standard_unit_for_ingredient(ingredient):
    """Get the standard unit for an ingredient for universal pricing"""
    category = get_ingredient_category(ingredient)
    if not category:
        return "unit"  # Default unit if category not found
    
    category_unit = standard_units.get(category, "unit")
    
    # Handle nested dictionaries for specific ingredients
    if isinstance(category_unit, dict):
        return category_unit.get(ingredient, "unit")
    
    return category_unit

def get_region_modifier(country, state=None):
    """Get cost modifier based on location"""
    if country in region_cost_modifiers:
        country_data = region_cost_modifiers[country]
        if state and state in country_data:
            return country_data[state]
        return country_data.get('DEFAULT', 1.0)
    return region_cost_modifiers.get('DEFAULT', 1.0)

def adjust_cost_for_unit(base_cost, from_unit, to_unit):
    """Adjust cost based on unit differences"""
    # If units are the same, no conversion needed
    if from_unit == to_unit:
        return base_cost
    
    # Apply conversion factors for different units
    if (from_unit == 'lb' and to_unit == 'kg'):
        return base_cost * conversion_factors['lb_to_kg']
    elif (from_unit == 'kg' and to_unit == 'lb'):
        return base_cost / conversion_factors['lb_to_kg']
    elif (from_unit == 'oz' and to_unit == 'g'):
        return base_cost * (conversion_factors['oz_to_g'] / 1000)  # convert to kg
    elif (from_unit == 'g' and to_unit == 'oz'):
        return base_cost / (conversion_factors['oz_to_g'] / 1000)
    elif (from_unit == 'fl oz' and to_unit == 'ml'):
        return base_cost * (conversion_factors['fl_oz_to_ml'] / 1000)  # convert to liter
    elif (from_unit == 'ml' and to_unit == 'fl oz'):
        return base_cost / (conversion_factors['fl_oz_to_ml'] / 1000)
    elif (from_unit == 'gallon' and to_unit == 'liter'):
        return base_cost / conversion_factors['gallon_to_liter']
    elif (from_unit == 'liter' and to_unit == 'gallon'):
        return base_cost * conversion_factors['gallon_to_liter']
    
    # Default case - no conversion
    return base_cost

def calculate_ingredient_costs(ingredients, country, state=None):
    """Calculate costs for selected ingredients based on location with unit consideration"""
    costs = {}
    local_units = {}
    standard_units_dict = {}
    standard_costs = {}
    
    for ingredient in ingredients:
        # Get local unit for this ingredient
        local_unit = get_unit_for_ingredient(ingredient, country)
        local_units[ingredient] = local_unit
        
        # Get standard unit for universal comparison
        std_unit = get_standard_unit_for_ingredient(ingredient)
        standard_units_dict[ingredient] = std_unit
        
        # Check if we have a direct regional price
        if country in regional_prices and ingredient in regional_prices[country]:
            # Use the direct regional price (already in local currency and unit)
            direct_price = regional_prices[country][ingredient]
            # Add some randomness (+/- 10%)
            variation = random.uniform(0.9, 1.1)
            costs[ingredient] = round(direct_price * variation, 2)
            
            # Convert to standard unit if needed for comparison
            if local_unit != std_unit:
                # Convert price from local unit to standard unit
                standard_price = adjust_cost_for_unit(costs[ingredient], local_unit, std_unit)
                standard_costs[ingredient] = standard_price
            else:
                standard_costs[ingredient] = costs[ingredient]
            
        else:
            # Use base price with region modifier
            base_cost = base_ingredient_costs.get(ingredient, 3.0)  # Default to $3 if missing
            modifier = get_region_modifier(country, state)
            
            # Adjust for local currency (convert from USD)
            currency_info = currency_conversion.get(country, currency_conversion['DEFAULT'])
            currency_rate = currency_info['rate']
            
            # Adjust for units based on standard units (kg) to local units
            if local_unit != std_unit:
                base_cost = adjust_cost_for_unit(base_cost, std_unit, local_unit)
            
            # Calculate final price with regional modifier and currency conversion
            price = base_cost * modifier * currency_rate
            
            # Add randomness
            variation = random.uniform(0.9, 1.1)
            costs[ingredient] = round(price * variation, 2)
            
            # Calculate standard unit cost for comparison
            if local_unit != std_unit:
                standard_price = adjust_cost_for_unit(costs[ingredient], local_unit, std_unit)
                standard_costs[ingredient] = standard_price
            else:
                standard_costs[ingredient] = costs[ingredient]
    
    return costs, local_units, standard_costs, standard_units_dict

def format_currency(amount, country):
    """Format amount according to country's currency"""
    currency_info = currency_conversion.get(country, currency_conversion['DEFAULT'])
    symbol = currency_info['symbol']
    
    # Amount is already in local currency
    return f"{symbol}{amount:.2f}"

def has_states(country):
    """Check if country has states/provinces that affect pricing"""
    return country in ['United States', 'Canada', 'Australia', 'India', 'Brazil']

def main():
    st.set_page_config(layout="wide")
    st.title("Ingredient Cost Calculator")
    st.write("Find realistic costs for ingredients in your location")
    
    # Use columns for better layout
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Your Location")
        # Location selection with dropdown appearing below
        country_options = ["United States", "India", "United Kingdom", "Canada", "Australia", 
                          "France", "Germany", "Japan", "Brazil", "Mexico", "Other"]
        country = st.selectbox("Select your country", country_options, key="country_select")
        
        # Handle special case for countries with states - use dropdown below
        state = None
        if has_states(country):
            if country == "United States":
                state_options = ["Alabama", "Alaska", "Arizona", "Arkansas", "California", 
                               "Colorado", "Connecticut", "Delaware", "Florida", "Georgia", 
                               "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", "Kansas", 
                               "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", 
                               "Michigan", "Minnesota", "Mississippi", "Missouri", "Montana", 
                               "Nebraska", "Nevada", "New Hampshire", "New Jersey", "New Mexico", 
                               "New York", "North Carolina", "North Dakota", "Ohio", "Oklahoma", 
                               "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", 
                               "South Dakota", "Tennessee", "Texas", "Utah", "Vermont", 
                               "Virginia", "Washington", "West Virginia", "Wisconsin", "Wyoming"]
                state = st.selectbox("Select your state", state_options, key="state_select")
            elif country == "India":
                state_options = ["Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", 
                               "Chhattisgarh", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", 
                               "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", 
                               "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", 
                               "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", 
                               "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi"]
                state = st.selectbox("Select your state", state_options, key="state_select_india")
        
        city = st.text_input("Enter your city")
        
    with col2:
        st.subheader("Select Ingredients")
        
        # Use tabs for different selection methods
        tab1, tab2 = st.tabs(["Select by Category", "Select All Ingredients"])
        
        with tab1:
            # Create a dropdown for each category
            selected_ingredients_by_category = []
            for category, items in default_ingredients.items():
                with st.expander(f"{category}", expanded=False):
                    for ingredient in items:
                        if st.checkbox(ingredient, key=f"cat_{ingredient}"):
                            selected_ingredients_by_category.append(ingredient)
        
        with tab2:
            all_ingredients = get_all_default_ingredients()
            selected_ingredients_multiselect = st.multiselect("Choose ingredients", all_ingredients)
        
        # Combine selections from both tabs
        selected_ingredients = list(set(selected_ingredients_by_category + selected_ingredients_multiselect))
        
        if selected_ingredients:
            st.write(f"You selected {len(selected_ingredients)} ingredients")
    
    # Button to calculate costs
    calculate_button = st.button("Calculate Costs", type="primary")
    
    if calculate_button:
        if not selected_ingredients:
            st.warning("Please select at least one ingredient")
        else:
            st.subheader("Estimated Costs in Your Area")
            
            # Calculate costs with appropriate units
            costs, local_units, standard_costs, standard_units = calculate_ingredient_costs(selected_ingredients, country, state)
            
            # Display costs in a table
            cost_data = {
                "Ingredient": [], 
                f"Cost Per Unit (Local)": [], 
                "Local Unit": [],
                f"Cost Per Unit (Universal)": [],
                "Universal Unit": []
            }
            
            for ingredient in selected_ingredients:
                cost_data["Ingredient"].append(ingredient)
                
                # Local cost and unit
                formatted_local_cost = format_currency(costs[ingredient], country)
                cost_data[f"Cost Per Unit (Local)"].append(formatted_local_cost)
                cost_data["Local Unit"].append(local_units[ingredient])
                
                # Universal cost and unit (standard unit cost already converted to local currency)
                formatted_std_cost = format_currency(standard_costs[ingredient], country)
                cost_data[f"Cost Per Unit (Universal)"].append(formatted_std_cost)
                cost_data["Universal Unit"].append(standard_units[ingredient])
            
            cost_df = pd.DataFrame(cost_data)
            st.dataframe(cost_df, use_container_width=True)
            
            # Marketplace message
            location_str = f"{city}, {state + ', ' if state else ''}{country}" if city else f"{state + ', ' if state else ''}{country}"
            st.success(f"You can find these ingredients at marketplaces in {location_str}!")
            
            # Show unit information
            st.info(f"Note: 'Local Unit' shows prices in units commonly used in {country}, while 'Universal Unit' shows standardized pricing for comparison across regions.")

if __name__ == "__main__":
    main()