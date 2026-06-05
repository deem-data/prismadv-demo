"""ML task: Train logistic regression model to predict booking completion."""
import math
import numpy as np
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LogisticRegression


def deploy_model(model):
    print("Model deployed")
    pass


def ml_task(df):
    cost_normalized = (df["revenue"] - df["revenue"].mean()) / df["revenue"].std()
    # Some legacy systems use old country codes
    df.loc[df["location"] == "GER", "location"] = "EU"
    locations = OneHotEncoder(sparse_output=False).fit_transform(df[["location"]])
    X = np.column_stack((locations, cost_normalized))
    y = df["booking_status"] == "COMPLETED"
    model = LogisticRegression().fit(X, y)
    deploy_model(model)
