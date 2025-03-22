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
import random
from collections import defaultdict
import traceback

def get_column_values(csv_file, column_name, num_rows):
    # Read CSV file
    df = pd.read_csv(csv_file)

    # Select the specified number of rows for the given column
    values_list = df[column_name].head(num_rows).tolist()
    return values_list

def remove_duplicates_from_last(lst):
    seen = set()
    result = []
    
    # Traverse from left to right (normal order)
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    
    return result

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

collections = get_collection_names()
print("Firestore Collections:", collections)

def fetch_data_as_2d_array(selected_columns,colind):
    """Fetch Firestore collection and return data as a 2D array with only specified field names."""
    data_array = []
    
    # Get all documents in the collection
    docs = db.collection(collections[colind]).stream()
    
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

selected_cols = ['email','age','height','weight','bmi','sleep_hours','meals_per_day','diet_preference']  # Define columns you need
fields, data = fetch_data_as_2d_array(selected_cols,4)

print(data[0])
X = []
for i in data:
    temp_list = []
    for j in [1,2,3,4,5,6]:
        temp_list.append(i[j])
    X.append(temp_list)
print(X[0])
X = np.array(X)
#print(X)

from sklearn.preprocessing import StandardScaler
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
print(X_scaled)

from sklearn.neighbors import NearestNeighbors
# Train KNN model
negi = 3
knn = NearestNeighbors(n_neighbors=negi, metric='euclidean')
knn.fit(X_scaled)


def recommend(email):
    idx = -1
    for i, row in enumerate(data):  # Track index using enumerate
        if email == row[0]:  # Assuming email is the first element in each row
            idx = i
            break

    if idx == -1:
        print("Email not found!")
        return
    user_data = X_scaled[idx].reshape(1, -1)  # Use idx directly
    distances, indices = knn.kneighbors(user_data)
    indices_list = list(indices[0])
    indices_list.pop(0)
    #Recipie
    #print("Indices of similar users:", indices[0])
    #print('users: ',data[indices[0][1]][0])
    selected_colsr = ['user_id','recipe_name','rating']
    fields2, recipe_ = fetch_data_as_2d_array(selected_colsr,2)
    #print(recipe_)
    def create_recipe_dict(indices, data, recipe_):
        user_dict = {}  # Dictionary to store results

        # Get users from the given indices
        matched_users = [data[i][0] for i in indices_list]  # Extract emails

        # Match emails with recipe_
        for email in matched_users:
            for recipe in recipe_:
                if recipe[0] == email:  # Match email
                    user_dict[recipe[1]] = recipe[2]  # Store recipe name & rating

        return user_dict

    # Create dictionary
    recipe_dict = create_recipe_dict(indices, data, recipe_)
    #sorted
    recipe__desc = dict(sorted(recipe_dict.items(), key=lambda item: item[1], reverse=True))
    #print(recipe_dict)
    #print(recipe__desc)
    recipe__desc_list = list(recipe__desc.keys())
    #print(recipe__desc_list)

    #Incridents
    file_path = "nutrients.csv"
    dataset = pd.read_csv(file_path)
    column_name = 'Food'
    final_incridient = []
    

    selected_colsi = ['username','ratings']
    file,incrident = fetch_data_as_2d_array(selected_colsi,0)
    #Create
    #print(incrident)
    '''LOGIC'''
    # Step 1: Extract selected emails from data based on index
    selected_emails = {data[i][0] for i in indices_list}

    # Step 2: Extract ingredient data for selected emails
    ingredient_count = defaultdict(int)

    for entry in incrident:
        if entry[0] in selected_emails:  # Check if email is in selected emails
            for item, count in entry[1].items():
                ingredient_count[item] += count  # Sum up ingredient values

    # Step 3: Sort the final dictionary by values in descending order
    sorted_ingredients = dict(sorted(ingredient_count.items(), key=lambda x: x[1], reverse=True))

    # Output the result
    #print(sorted_ingredients)

    # Step 1: Initialize a dictionary to store total ingredient values
    final_ingredients = {}

    final_incridient = list(sorted_ingredients.keys())
    # Step 4: Print the sorted dictionary
    #print(sorted_ingredients)
    #print(final_incridient)
    #if(len(incrident)<3):
    '''
    random_numbers = [random.randint(0, dataset.shape[0]-1) for _ in range(30)]
    final_incridient = dataset.loc[random_numbers, column_name].tolist()
    print(final_incridient)
    '''
    #Removing Duplicate items
    final_incridient = remove_duplicates_from_last(final_incridient)
    recipe__desc_list = remove_duplicates_from_last(recipe__desc_list)
    packup = []
    
    if len(final_incridient)<3:
        final_incridient = get_column_values(file_path,'Food',30)
        final_incridient = remove_duplicates_from_last(final_incridient)

    packup.append(final_incridient)
    packup.append(recipe__desc_list)
    #print(packup)
    return packup


#print(data)
#recommend('bbb@gmail.com')
