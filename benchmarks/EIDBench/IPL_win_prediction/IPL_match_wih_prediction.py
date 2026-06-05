# kaggle datasets download patrickb1912/ipl-complete-dataset-20082020 --unzip

# Importing required libraries
import numpy as np  # Library for numerical operations
import pandas as pd  # Library for data manipulation and analysis
from sklearn.preprocessing import OrdinalEncoder
from sklearn.model_selection import train_test_split  # Function to split data into training and testing sets
from sklearn.metrics import confusion_matrix    # Import the confusion_matrix function for evaluating classification results
from sklearn.metrics import classification_report   # Import the classification_report function for detailed classification metrics
from sklearn.ensemble import RandomForestClassifier  # Random Forest classifier model
from sklearn.linear_model import LogisticRegression  # Importing Logistic regression classifier
from sklearn.svm import SVC     # Import the SVC class for support vector machine classification
from sklearn.metrics import accuracy_score  # Function to calculate accuracy score
# Importing LightGBM library
import lightgbm as lgb  # Light Gradient Boosting Machine library

# Load matches data
data = pd.read_csv('matches.csv')
print(data.head())

# Replace old IPL team names with new ones to avoid inconsistencies
data.replace({'Rising Pune Supergiants': 'Rising Pune Supergiant'}, inplace=True)
data.replace({'Deccan Chargers': 'Sunrisers Hyderabad'}, inplace=True)
data.replace({'Delhi Daredevils': 'Delhi Capitals'}, inplace=True)
data.replace({'Pune Warriors': 'Rising Pune Supergiant'}, inplace=True)
data.replace({'Kings XI Punjab': 'Punjab Kings'}, inplace=True)
data.replace({'Gujarat Lions': 'Gujarat Titans'}, inplace=True)
data.replace({'Royal Challengers Bengaluru': 'Royal Challengers Bangalore'}, inplace=True)

# Clean missing values and drop unwanted rows, cols
data['city'] = data['city'].fillna('Unknown')
cols_to_fill = ['player_of_match', 'result']
data[cols_to_fill] = data[cols_to_fill].fillna('Not Available')
data['result_margin'] = data['result_margin'].fillna(data['result_margin'].mean())
data.drop(['id', 'method', 'date', 'result', 'season', 'match_type', 
        'target_runs', 'target_overs', 'super_over'], axis=1, inplace=True)
data.dropna(subset=['winner'], inplace=True)
print(data.info())

# Feature transformations
team_mapping = {
    'Royal Challengers Bangalore' : 1, 
    'Punjab Kings' : 2,
    'Delhi Capitals' : 3,
    'Mumbai Indians' : 4,
    'Kolkata Knight Riders' : 5, 
    'Rajasthan Royals' : 6,
    'Sunrisers Hyderabad' : 7,
    'Chennai Super Kings' : 8,
    'Kochi Tuskers Kerala' : 9,
    'Rising Pune Supergiant' : 10,
    'Gujarat Titans' : 11,
    'Lucknow Super Giants' : 12
}
data['team1'] = data['team1'].map(team_mapping)
data['team2'] = data['team2'].map(team_mapping)
data['winner'] = data['winner'].map(team_mapping)
data['toss_winner'] = data['toss_winner'].map(team_mapping)
cols_to_encode = ['city', 'player_of_match', 'venue', 'toss_decision', 'umpire1', 'umpire2']
encoder = OrdinalEncoder()
data[cols_to_encode] = encoder.fit_transform(data[cols_to_encode])

# Separate data into feature matrix and target column
X = data.drop(['winner'], axis=1)
y = data['winner']

# Slipt into training and testing set (80:20)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train LGBMClassifier model and evaluate
model = lgb.LGBMClassifier(
    boosting_type='gbdt',       # The type of boosting algorithm to use ('gbdt': Gradient Boosting Decision Tree)
    num_leaves=31,              # Number of leaves in one tree (default: 31)
    max_depth=-1,               # Maximum tree depth for base learners (-1 means no limit, default: -1)
    learning_rate=0.1,          # Learning rate or shrinkage rate to prevent overfitting (default: 0.1)
    n_estimators=100,           # Number of boosting iterations (default: 100)
    verbose=-1                  # Suppress warnings
)

model.fit(X_train, y_train)
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print("Accuracy:", accuracy)

