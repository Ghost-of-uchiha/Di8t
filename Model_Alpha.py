import pandas as pd
import numpy as np
import streamlit as st
import pyrebase
import time
import firebase_admin
from firebase_admin import credentials, firestore
import uuid
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import json
import requests
import runpy
import importlib
import streamlit as st
import pandas as pd
import time
import threading
import traceback


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
db = initialize_firebase()
def get_collection_names():
    """Fetch and return all collection names from Firestore."""
    collections = db.collections()  # This returns a generator
    collection_names = [col.id for col in collections]  # Extract collection names
    return collection_names

# Fetch and print collection names
collections = get_collection_names()
print("Firestore Collections:", collections)

def fetch_data_as_2d_array(selected_columns):
    """Fetch Firestore collection and return data as a 2D array with only specified field names."""
    data_array = []
    
    # Get all documents in the collection
    docs = db.collection(collections[2]).stream()
    
    field_names = []  # Store column names
    
    for doc in docs:
        doc_data = doc.to_dict()

        # Extract field names (only for the first document)
        if not field_names:
            field_names = list(doc_data.keys())

        # Extract values for only selected columns
        row_values = [doc_data.get(col, None) for col in selected_columns]  
        
        # Append row to 2D array
        data_array.append(row_values)
    
    return selected_columns, data_array  # Return selected column names and filtered data

# Example usage
selected_cols = ['email','bmi','diet_preference','fitness_goal']  # Define columns you need
fields, data = fetch_data_as_2d_array(selected_cols)

#print("Selected Fields:", fields)
#print("Filtered Data:", data)



file_path = "nutrients.csv"
dataset = pd.read_csv(file_path)
users = pd.read_csv('data/all_survey_responses.csv')

# Replace alphabets in specific columns (by index)
columns_to_replace = [3, 4, 5, 6, 7, 8]
dataset.iloc[:, columns_to_replace] = dataset.iloc[:, columns_to_replace].replace(r'[A-Za-z]', 0, regex=True)

# Extract values
X = dataset.iloc[:, 3:].values
y = dataset.iloc[:,0].values

#Users data
coef = users.iloc[:,[1,7,9,12]]

mapping = {
    'dairy products': 'A',
    'fats, oils, shortenings': 'B',
    'meat, poultry': 'C',
    'fish, seafood': 'D',
    'vegetables a-e': 'E',
    'vegetables f-p': 'F',
    'vegetables r-z': 'G',
    'fruits a-f': 'H',
    'fruits g-p': 'I',
    'fruits r-z': 'J',
    'breads, cereals, fastfood,grains': 'K',
    'soups': 'L',
    'desserts, sweets': 'M',
    'jams, jellies': 'N',
    'seeds and nuts': 'O',
    'drinks,alcohol, beverages': 'P'
}

# Clean and apply the mapping
X[:, -1] = np.vectorize(lambda x: mapping.get(x.strip().lower(), 'Z'))(X[:, -1])

'''
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
ct = ColumnTransformer(transformers=[('encoder',OneHotEncoder(),[-1])],remainder='passthrough')
X = np.array(ct.fit_transform(X))
'''

# Convert all values except the last column to integers
X[:, :-1] = np.array([[int(float(value.replace(',', ''))) if isinstance(value, str) and value.replace(',', '').replace('.', '').isdigit()
               else int(float(value)) if isinstance(value, str) and value.replace('.', '').isdigit()
               else int(value) if isinstance(value, (float, int)) and not np.isnan(value)
               else 0 
               for value in row[:-1]] for row in X])

# Keep last column unchanged
last_column = X[:, -1]

# Combine back into a single array (ensuring last column stays unchanged)
X = np.column_stack((X[:, :-1], last_column))

# Replace NaNs with 0 (if any)
X[:, :-1] = np.nan_to_num(X[:, :-1]).astype(int)

from sklearn.preprocessing import StandardScaler
sc = StandardScaler()
X[:, :-1] = sc.fit_transform(X[:, :-1])

def recommend(email):
    #Processing According to user
    numberRows = len(data)
    matched = []
    idx = -1
    for i in range(0,numberRows):
        idx = i
        if(data[i][0]==email):
            break

    #print(matched[0])
    a = data[idx][1]
    b = str(data[idx][2])
    c = str(data[idx][3])
    _c = 1
    if c=='Muscle gain':
        _c = 80
    # Example coefficients for each numeric column (6 columns)
    coefficients = [a,_c,1,1,1,1]  # Adjust these based on importance

    # List to store row index and calculated rating
    ratings = []

    # Loop through rows to calculate ratings
    for i, row in enumerate(X):
        # Apply coefficients to each column value (excluding last column)
        rating = sum(int(row[j]) * coefficients[j] for j in range(len(coefficients)))
    
        # Append row index and rating
        ratings.append((i, rating))

    # Sort ratings based on the rating value in descending order
    sorted_ratings = sorted(ratings, key=lambda x: x[1], reverse=True)
    final_list = []
    # Display sorted ratings

    for idx, rating in sorted_ratings:
        final_list.append([y[idx],(X[idx])])
        #print(y[idx],end=": ")
        #print(f"Row {idx} -> Rating: {rating:.2f}")
    #print(len(final_list))
    #Filter
    #print(final_list[0][1][6])
    #print(X.shape[0])
    #print(final_list)
    if b == 'Vegetarian':
        for i in range(len(final_list) - 1, -1, -1):  # Loop from last to first
            if final_list[i][1][6] == 'C':  # Check 7th element in the array
                final_list.pop(i)
    #print(len(final_list))
    return final_list

#print(recommend('kakshixguy099@gmail.com'))